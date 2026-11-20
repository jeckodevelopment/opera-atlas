"""HTTP safety checks without contacting an external host."""
import io
import unittest
from urllib.error import URLError

from opera_atlas.controlled_fetch import (
    AccessDenied, FetchUnavailable, fetch_official_html, record_source_check,
)
from opera_atlas.db import connect, migrate

SOURCE = "https://www.teatroregio.torino.it/"
URL = SOURCE + "opera-e-balletto-2026-2027/la-traviata"


class Response:
    def __init__(self, data: bytes, content_type="text/html", status=200):
        self.content = io.BytesIO(data)
        self.status = status
        self.headers = {"Content-Type": content_type}
    def __enter__(self): return self
    def __exit__(self, *args): self.content.close()
    def read(self, size=-1): return self.content.read(size)


class FakeOpener:
    def __init__(self, robots=b"User-agent: *\nAllow: /\n", html=b"<html>OK</html>"):
        self.robots, self.html, self.calls = robots, html, []
    def open(self, request, timeout=None):
        self.calls.append(request.full_url)
        if request.full_url.endswith("robots.txt"):
            if self.robots is None:
                raise URLError("unreachable")
            return Response(self.robots)
        return Response(self.html)


class FetchTests(unittest.TestCase):
    def setUp(self):
        self.conn = connect()
        migrate(self.conn)
        self.conn.execute(
            "INSERT INTO sources(official_url,access_status) VALUES (?, 'approved')",
            (SOURCE,),
        )

    def tearDown(self):
        self.conn.close()

    def test_network_disabled_by_default(self):
        with self.assertRaises(AccessDenied):
            fetch_official_html(self.conn, source_id=1,url=URL)
    
    def test_robots_disallow_fails_before_page(self):
        opener = FakeOpener(robots=b"User-agent: *\nDisallow: /opera-e-balletto-2026-2027/")
        with self.assertRaises(AccessDenied):
            fetch_official_html(self.conn,source_id=1,url=URL,
                                network_enabled=True,opener=opener)
        self.assertEqual(len(opener.calls),1)

    def test_robots_unavailable_fails_closed(self):
        opener = FakeOpener(robots=None)
        with self.assertRaises(FetchUnavailable):
            fetch_official_html(self.conn,source_id=1,url=URL,
                                network_enabled=True,opener=opener)
        self.assertEqual(len(opener.calls),1)

    def test_robots_html_placeholder_is_not_permission(self):
        opener = FakeOpener(robots=b"<html><body>Temporarily unavailable</body></html>")
        with self.assertRaises(FetchUnavailable):
            fetch_official_html(self.conn,source_id=1,url=URL,
                                network_enabled=True,opener=opener)
        self.assertEqual(opener.calls,[SOURCE+"robots.txt"])

    def test_robot_rules_permit_specific_page_but_not_forbidden_path(self):
        opener = FakeOpener(
            robots=b"User-agent: *\\nDisallow: /private/\\nAllow: /opera-e-balletto-2026-2027/\\n"
        )
        fetch_official_html(self.conn,source_id=1,url=URL,
                            network_enabled=True,opener=opener)
        self.assertEqual(len(opener.calls),2)
        forbidden = FakeOpener(robots=b"User-agent: *\\nDisallow: /\\n")
        with self.assertRaises(AccessDenied):
            fetch_official_html(self.conn,source_id=1,url=URL,
                                network_enabled=True,opener=forbidden)
        self.assertEqual(len(forbidden.calls),1)

    def test_explicit_approved_fetch_after_robots(self):
        opener = FakeOpener()
        result = fetch_official_html(self.conn,source_id=1,url=URL,
                                     network_enabled=True,opener=opener)
        self.assertEqual(result.byte_count,15)
        self.assertEqual(len(opener.calls),2)
        self.assertEqual(len(result.sha256),64)

    def test_blocked_source_not_fetched(self):
        opener = FakeOpener()
        self.conn.execute("UPDATE sources SET access_status='blocked'")
        with self.assertRaises(AccessDenied):
            fetch_official_html(self.conn,source_id=1,url=URL,
                                network_enabled=True,opener=opener)
        self.assertEqual(opener.calls,[])

    def test_no_cross_host(self):
        opener = FakeOpener()
        with self.assertRaises(AccessDenied):
            fetch_official_html(self.conn,source_id=1,url="https://evil.example/page",
                                network_enabled=True,opener=opener)
        self.assertEqual(opener.calls,[])

    def test_check_records_operational_metadata(self):
        record_source_check(self.conn,source_id=1,url=URL,outcome="robots_unavailable",
                            message="policy cannot be verified")
        record = self.conn.execute(
            "SELECT outcome,message FROM source_checks"
        ).fetchone()
        self.assertEqual(record["outcome"],"robots_unavailable")
        self.assertNotIn("html",record["message"])


if __name__ == "__main__":
    unittest.main()
