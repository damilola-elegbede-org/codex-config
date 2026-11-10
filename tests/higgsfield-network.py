#!/usr/bin/env python3
"""Test actual HTTP framing over mocked sockets; never contact any network."""

from contextlib import ExitStack
from io import BytesIO
import os
from pathlib import Path
import socket
import ssl
import sys
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "system-configs/.agents/skills/higgsfield-brandkit/scripts"))
import brandkit
import build_brandbook
import public_https as transport


def response(status=200, body=b"ok", headers=None, declared=True):
    fields = {"Content-Type": "image/svg+xml", "Connection": "close"}
    if declared:
        fields["Content-Length"] = str(len(body))
    fields.update(headers or {})
    return (
        f"HTTP/1.1 {status} Fixture\r\n".encode()
        + "".join(f"{key}: {value}\r\n" for key, value in fields.items()).encode()
        + b"\r\n" + body
    )


class FakeSocket:
    def __init__(self, network, family, kind, protocol):
        self.network = network
        self.family = family
        self.closed = False
        self.sent = b""
        self.file = None
        self.timeout = None
        assert kind == socket.SOCK_STREAM and protocol == socket.IPPROTO_TCP

    def settimeout(self, timeout):
        self.timeout = timeout

    def connect(self, address):
        self.network.connections.append((self.family, address))
        if address[0] in self.network.failed_addresses:
            raise OSError("fixture connect failure")

    def sendall(self, data):
        self.sent += data

    def makefile(self, mode):
        assert mode == "rb"
        self.file = BytesIO(self.network.responses.pop(0))
        return self.file

    def close(self):
        self.closed = True


class Network:
    """Replace only DNS, socket/TLS boundaries and proxy discovery, not HTTP logic."""
    def __init__(self, *, answers=None, responses=None, failed_addresses=(), failed_families=(), tls_error=None):
        self.answers = list(answers if answers is not None else [["8.8.8.8"]])
        self.responses = list(responses if responses is not None else [response()])
        self.failed_addresses = failed_addresses
        self.failed_families = failed_families
        self.tls_error = tls_error
        self.resolutions = []
        self.connections = []
        self.server_names = []
        self.sockets = []
        self.check_hostname = True
        self.verify_mode = ssl.CERT_REQUIRED

    def resolve(self, hostname, port, *, type, proto):
        assert type == socket.SOCK_STREAM and proto == socket.IPPROTO_TCP
        self.resolutions.append((hostname, port))
        if not self.answers:
            raise AssertionError("Unexpected second DNS resolution during connection")
        result = []
        for ip in self.answers.pop(0):
            family = socket.AF_INET6 if ":" in ip else socket.AF_INET
            address = (ip, port, 0, 0) if family == socket.AF_INET6 else (ip, port)
            result.append((family, type, proto, "", address))
        return result

    def socket(self, family, kind, protocol):
        if family in self.failed_families:
            raise OSError("fixture address family unavailable")
        raw = FakeSocket(self, family, kind, protocol)
        self.sockets.append(raw)
        return raw

    def wrap_socket(self, raw, *, server_hostname):
        self.server_names.append(server_hostname)
        if self.tls_error:
            raise self.tls_error
        return raw

    def __enter__(self):
        self.stack = ExitStack()
        self.stack.enter_context(patch.dict(os.environ, {}, clear=True))
        self.proxies = self.stack.enter_context(patch.object(transport, "getproxies", return_value={}))
        self.stack.enter_context(patch.object(transport, "tls_context", return_value=self))
        self.stack.enter_context(patch.object(socket, "getaddrinfo", side_effect=self.resolve))
        self.stack.enter_context(patch.object(socket, "socket", side_effect=self.socket))
        return self

    def __exit__(self, *args):
        return self.stack.__exit__(*args)

    def assert_closed(self, testcase):
        for raw in self.sockets:
            testcase.assertTrue(raw.closed, "raw connection leaked")
            if raw.file is not None:
                testcase.assertTrue(raw.file.closed, "HTTP response leaked")


WRAPPERS = (
    ("SVG", brandkit.safe_fetch_svg),
    ("Brandbook", lambda url: build_brandbook.fetch_bytes(url, 1024)),
)


class PublicHTTPSTests(unittest.TestCase):
    def test_rebinding_cannot_change_connected_address_and_host_tls_stay_original(self):
        for name, download in WRAPPERS:
            with self.subTest(wrapper=name), Network(answers=[["8.8.8.8"], ["127.0.0.1"]]) as net:
                self.assertIn(download("https://assets.example:8443/logo.svg?revision=2"), (b"ok", "ok"))
                self.assertEqual(net.resolutions, [("assets.example", 8443)])
                self.assertEqual(net.connections, [(socket.AF_INET, ("8.8.8.8", 8443))])
                self.assertEqual(net.server_names, ["assets.example"])
                self.assertIn(b"GET /logo.svg?revision=2 HTTP/1.1\r\n", net.sockets[0].sent)
                self.assertIn(b"Host: assets.example:8443\r\n", net.sockets[0].sent)
                self.assertNotIn(b"8.8.8.8", net.sockets[0].sent)
                self.assertEqual(net.sockets[0].timeout, 20 if name == "SVG" else 30)
                net.assert_closed(self)

    def test_redirects_validate_and_pin_each_hop_including_same_host(self):
        replies = [response(302, headers={"Location": "/next"}), response(307, headers={"Location": "https://cdn.example/final"}), response()]
        for name, download in WRAPPERS:
            with self.subTest(wrapper=name), Network(answers=[["8.8.8.8"], ["1.1.1.1"], ["9.9.9.9"]], responses=replies) as net:
                download("https://assets.example/start")
                self.assertEqual(net.resolutions, [("assets.example", 443), ("assets.example", 443), ("cdn.example", 443)])
                self.assertEqual(net.server_names, ["assets.example", "assets.example", "cdn.example"])
                self.assertEqual([entry[1][0] for entry in net.connections], ["8.8.8.8", "1.1.1.1", "9.9.9.9"])
                self.assertIn(b"GET /next HTTP/1.1", net.sockets[1].sent)
                self.assertIn(b"Host: cdn.example\r\n", net.sockets[2].sent)
                net.assert_closed(self)

    def test_redirect_rebinding_to_private_fails_before_second_connection(self):
        for name, download in WRAPPERS:
            with self.subTest(wrapper=name), Network(answers=[["8.8.8.8"], ["127.0.0.1"]], responses=[response(302, headers={"Location": "/next"})]) as net:
                with self.assertRaisesRegex(RuntimeError, "non-public"):
                    download("https://assets.example/start")
                self.assertEqual(len(net.resolutions), 2)
                self.assertEqual(len(net.connections), 1)
                net.assert_closed(self)

    def test_proxy_configuration_fails_before_dns_or_socket(self):
        for name, download in WRAPPERS:
            for setting in ("HTTPS_PROXY", "https_proxy", "ALL_PROXY", "http_proxy", "platform"):
                with self.subTest(wrapper=name, setting=setting), Network() as net:
                    if setting == "platform":
                        net.proxies.return_value = {"https": "http://127.0.0.1:8080"}
                    else:
                        os.environ[setting] = "http://127.0.0.1:8080"
                    with self.assertRaisesRegex(RuntimeError, "proxies"):
                        download("https://assets.example/logo")
                    self.assertEqual(net.resolutions, [])
                    self.assertEqual(net.sockets, [])

    def test_no_proxy_alone_does_not_block_a_direct_public_request(self):
        with Network() as net:
            os.environ["NO_PROXY"] = "localhost"
            net.proxies.return_value = {"no": "localhost"}
            self.assertEqual(build_brandbook.fetch_bytes("https://assets.example/file", 10), b"ok")

    def test_private_multicast_scoped_and_mixed_answers_fail_before_connect(self):
        rejected = [
            ["127.0.0.1"], ["10.0.0.1"], ["169.254.169.254"], ["0.0.0.0"],
            ["::1"], ["fc00::1"], ["fec0::1"], ["fe80::1%en0"], ["::ffff:127.0.0.1"],
            ["224.0.0.1"], ["ff02::1"], ["8.8.8.8", "192.168.1.1"], [],
        ]
        for name, download in WRAPPERS:
            for addresses in rejected:
                with self.subTest(wrapper=name, addresses=addresses), Network(answers=[addresses]) as net:
                    with self.assertRaises(RuntimeError):
                        download("https://assets.example/logo")
                    self.assertEqual(net.connections, [])

    def test_public_ipv6_is_pinned_with_original_host_header_and_tls_name(self):
        with Network(answers=[["2606:4700:4700::1111"]]) as net:
            build_brandbook.fetch_bytes("https://[2606:4700:4700::1111]:443/file", 10)
            self.assertEqual(net.connections, [(socket.AF_INET6, ("2606:4700:4700::1111", 443, 0, 0))])
            self.assertEqual(net.server_names, ["2606:4700:4700::1111"])
            self.assertIn(b"Host: [2606:4700:4700::1111]:443\r\n", net.sockets[0].sent)
            net.assert_closed(self)

    def test_connect_retry_uses_only_original_validated_address_list(self):
        with Network(answers=[["8.8.8.8", "1.1.1.1"]], failed_addresses={"8.8.8.8"}) as net:
            build_brandbook.fetch_bytes("https://assets.example/file", 10)
            self.assertEqual(len(net.resolutions), 1)
            self.assertEqual([entry[1][0] for entry in net.connections], ["8.8.8.8", "1.1.1.1"])
            net.assert_closed(self)

    def test_unavailable_ipv6_socket_falls_back_to_validated_ipv4(self):
        with Network(answers=[["2606:4700:4700::1111", "8.8.8.8"]], failed_families={socket.AF_INET6}) as net:
            build_brandbook.fetch_bytes("https://assets.example/file", 10)
            self.assertEqual(len(net.resolutions), 1)
            self.assertEqual(net.connections, [(socket.AF_INET, ("8.8.8.8", 443))])
            net.assert_closed(self)

    def test_tls_verification_and_cleanup(self):
        with Network() as net:
            net.check_hostname = False
            with self.assertRaisesRegex(RuntimeError, "verified TLS"):
                brandkit.safe_fetch_svg("https://assets.example/logo")
            self.assertEqual(net.sockets, [])
        with Network() as net:
            net.verify_mode = ssl.CERT_NONE
            with self.assertRaisesRegex(RuntimeError, "verified TLS"):
                brandkit.safe_fetch_svg("https://assets.example/logo")
            self.assertEqual(net.sockets, [])
        for error in (ssl.SSLCertVerificationError("untrusted certificate"), OSError("TLS wrap failed")):
            with self.subTest(error=error), Network(tls_error=error) as net:
                with self.assertRaisesRegex(RuntimeError, "HTTPS download failed"):
                    brandkit.safe_fetch_svg("https://assets.example/logo")
                self.assertEqual(net.sockets[0].sent, b"")
                net.assert_closed(self)

    def test_invalid_url_and_redirect_downgrade_are_blocked(self):
        for url in ("http://assets.example/x", "https://user:password@assets.example/x", "https://@assets.example/x", "https://assets.example:0/x", "https://assets.example/x\r\nHost:evil", "https://[fe80::1%25en0]/x"):
            with self.subTest(url=url), Network() as net:
                with self.assertRaises(RuntimeError):
                    brandkit.safe_fetch_svg(url)
                self.assertEqual(net.resolutions, [])
        with Network(responses=[response(302, headers={"Location": "http://127.0.0.1/private"})]) as net:
            with self.assertRaises(RuntimeError):
                brandkit.safe_fetch_svg("https://assets.example/logo")
            self.assertEqual(len(net.connections), 1)
            net.assert_closed(self)

    def test_status_size_redirect_bounds_and_svg_content_type_are_preserved(self):
        invalid_responses = [
            response(403), response(302), response(headers={"Content-Length": "9000"}),
            response(headers={"Content-Length": "-1"}), response(headers={"Content-Length": "invalid"}),
            response(body=b"x" * 1025, declared=False),
        ]
        for reply in invalid_responses:
            with self.subTest(response=reply[:100]), Network(responses=[reply]) as net:
                with self.assertRaises(RuntimeError):
                    build_brandbook.fetch_bytes("https://assets.example/file", 1024)
                net.assert_closed(self)
        with Network(answers=[["8.8.8.8"]] * 3, responses=[response(302, headers={"Location": "/loop"})] * 3) as net:
            with self.assertRaisesRegex(RuntimeError, "too many"):
                build_brandbook.fetch_bytes("https://assets.example/file", 1024)
            self.assertEqual(len(net.connections), 3)
            net.assert_closed(self)
        with Network(responses=[response(headers={"Content-Type": "text/html"})]) as net:
            with self.assertRaisesRegex(RuntimeError, "unsupported content type"):
                brandkit.safe_fetch_svg("https://assets.example/logo")
            net.assert_closed(self)
        with Network(responses=[response(body=b"1234", declared=False)]) as net, patch.object(brandkit, "MAX_SVG_BYTES", 3):
            with self.assertRaisesRegex(RuntimeError, "exceeds 3"):
                brandkit.safe_fetch_svg("https://assets.example/logo")
            net.assert_closed(self)


if __name__ == "__main__":
    unittest.main()
