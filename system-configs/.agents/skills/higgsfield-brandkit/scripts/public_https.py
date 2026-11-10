"""Bounded public HTTPS downloads with DNS-pinned connections and verified TLS."""

from __future__ import annotations

from http.client import HTTPException, HTTPSConnection
import ipaddress
import os
from pathlib import Path
import socket
import ssl
from urllib.parse import urljoin, urlsplit
from urllib.request import getproxies


def tls_context() -> ssl.SSLContext:
    """Keep certificate/hostname verification and the existing OS CA fallback."""
    context = ssl.create_default_context()
    if ssl.get_default_verify_paths().cafile:
        return context
    for candidate in (
        Path("/etc/ssl/cert.pem"),
        Path("/etc/ssl/certs/ca-certificates.crt"),
        Path("/etc/pki/tls/certs/ca-bundle.crt"),
    ):
        if candidate.is_file():
            context.load_verify_locations(cafile=str(candidate))
            break
    return context


def reject_proxies() -> None:
    """Fail closed: this transport cannot enforce a proxy's ultimate destination."""
    environment_proxy = any(
        value and name.lower().endswith("_proxy") and name.lower() != "no_proxy"
        for name, value in os.environ.items()
    )
    configured_proxy = any(
        value for name, value in getproxies().items() if name.lower() != "no"
    )
    if environment_proxy or configured_proxy:
        raise RuntimeError("public HTTPS downloads do not support configured proxies")


def public_addresses(hostname: str, port: int) -> tuple[tuple[int, tuple], ...]:
    """Resolve once, validate every answer, and return only numeric socket targets."""
    try:
        answers = socket.getaddrinfo(
            hostname, port, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP
        )
    except socket.gaierror as error:
        raise RuntimeError(f"cannot resolve HTTPS host '{hostname}'") from error
    targets: list[tuple[int, tuple]] = []
    for family, _, _, _, address in answers:
        numeric = address[0]
        if "%" in numeric or (family == socket.AF_INET6 and address[3]):
            raise RuntimeError("HTTPS host resolves to a scoped address")
        try:
            ip = ipaddress.ip_address(numeric)
        except ValueError as error:
            raise RuntimeError("HTTPS resolver returned a non-numeric address") from error
        mapped = getattr(ip, "ipv4_mapped", None)
        if any(
            not candidate.is_global
            or candidate.is_multicast
            or candidate.is_reserved
            or candidate.is_unspecified
            or getattr(candidate, "is_site_local", False)
            for candidate in (ip, mapped) if candidate is not None
        ):
            raise RuntimeError("HTTPS host resolves to a non-public address")
        if family == socket.AF_INET and ip.version == 4:
            target = (family, (str(ip), port))
        elif family == socket.AF_INET6 and ip.version == 6:
            target = (family, (str(ip), port, 0, 0))
        else:
            raise RuntimeError("HTTPS resolver returned an unsupported address family")
        if target not in targets:
            targets.append(target)
    if not targets:
        raise RuntimeError(f"cannot resolve HTTPS host '{hostname}'")
    return tuple(targets)


class PinnedHTTPSConnection(HTTPSConnection):
    """Connect only to previously validated IPs; authenticate the original host."""

    def __init__(self, host, port, *, addresses, context, timeout):
        """Keep the authenticated hostname separate from the validated IP targets."""
        if not context.check_hostname or context.verify_mode != ssl.CERT_REQUIRED:
            raise RuntimeError("public HTTPS downloads require verified TLS")
        super().__init__(host, port, context=context, timeout=timeout)
        self._public_addresses = tuple(addresses)

    def connect(self) -> None:
        """Bypass create_connection's second DNS lookup and all proxy tunneling."""
        if self._tunnel_host:
            raise RuntimeError("public HTTPS downloads do not support proxy tunnels")
        last_error = None
        for family, address in self._public_addresses:
            raw = None
            try:
                raw = socket.socket(family, socket.SOCK_STREAM, socket.IPPROTO_TCP)
                raw.settimeout(self.timeout)
                raw.connect(address)
                self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
                return
            except ssl.SSLCertVerificationError:
                if raw is not None:
                    raw.close()
                raise
            except OSError as error:
                if raw is not None:
                    raw.close()
                last_error = error
            except BaseException:
                if raw is not None:
                    raw.close()
                raise
        if last_error is not None:
            raise last_error
        raise RuntimeError("no validated public HTTPS addresses")


def parse_https_url(url: str) -> tuple[str, int, str, str]:
    """Return canonical TLS hostname, port, HTTP Host, and origin-form target."""
    if any(ord(character) <= 32 or ord(character) == 127 for character in url):
        raise RuntimeError("HTTPS URLs must not contain whitespace or control characters")
    try:
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or "%" in parsed.hostname
            or "\\" in parsed.netloc
        ):
            raise ValueError("not a public HTTPS URL")
        hostname = parsed.hostname.encode("idna").decode("ascii")
        port = parsed.port if parsed.port is not None else 443
        if not 1 <= port <= 65535:
            raise ValueError("invalid port")
    except (ValueError, UnicodeError) as error:
        raise RuntimeError("resources must use HTTPS with a public host and no credentials") from error
    host_header = f"[{hostname}]" if ":" in hostname else hostname
    if parsed.port is not None:
        host_header += f":{port}"
    target = parsed.path or "/"
    if parsed.query:
        target += f"?{parsed.query}"
    return hostname, port, host_header, target


def fetch_public_https(
    url: str, *, limit: int, redirects: int, timeout: int, accept: str | None = None
) -> tuple[bytes, str]:
    """Fetch bounded bytes, validating and pinning every redirect independently."""
    if limit < 0 or redirects < 0 or timeout <= 0:
        raise ValueError("download bounds must be nonnegative with a positive timeout")
    reject_proxies()
    context = tls_context()
    current = url
    for hop in range(redirects + 1):
        reject_proxies()
        hostname, port, host_header, target = parse_https_url(current)
        addresses = public_addresses(hostname, port)
        connection = PinnedHTTPSConnection(
            hostname, port, addresses=addresses, context=context, timeout=timeout
        )
        response = None
        try:
            headers = {
                "Host": host_header,
                "User-Agent": "higgsfield-brandkit/1",
                "Accept-Encoding": "identity",
                "Connection": "close",
            }
            if accept:
                headers["Accept"] = accept
            connection.request("GET", target, headers=headers)
            response = connection.getresponse()
            if response.status in {301, 302, 303, 307, 308}:
                location = response.headers.get("Location")
                if not location:
                    raise RuntimeError("HTTPS redirect is missing Location")
                if hop == redirects:
                    raise RuntimeError("HTTPS URL redirected too many times")
                current = urljoin(current, location)
                continue
            if not 200 <= response.status < 300:
                raise RuntimeError(f"HTTPS download failed with HTTP {response.status}")
            try:
                declared = int(response.headers.get("Content-Length", "0") or "0")
            except ValueError as error:
                raise RuntimeError("HTTPS response has an invalid Content-Length") from error
            if declared < 0 or declared > limit:
                raise RuntimeError(f"HTTPS resource exceeds {limit} bytes or has invalid length")
            data = response.read(limit + 1)
            if len(data) > limit:
                raise RuntimeError(f"HTTPS resource exceeds {limit} bytes")
            return data, response.headers.get_content_type()
        except (OSError, HTTPException) as error:
            raise RuntimeError(f"HTTPS download failed: {error}") from error
        finally:
            try:
                if response is not None:
                    response.close()
            finally:
                connection.close()
    raise RuntimeError("HTTPS URL redirected too many times")
