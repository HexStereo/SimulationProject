"""
tests/test_server.py - Tests for Desktop REST Server Endpoints
"""

import http.server
import json
import threading
import time
import urllib.request
import pytest

from desktop_server import DesktopRequestHandler


@pytest.fixture(scope="module")
def local_server():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 5088), DesktopRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.3)
    yield "http://127.0.0.1:5088"
    server.shutdown()


def test_index_page(local_server):
    with urllib.request.urlopen(f"{local_server}/") as r:
        assert r.status == 200
        html = r.read().decode("utf-8")
        assert "6-Haneli Kod Anomali" in html


def test_api_status(local_server):
    with urllib.request.urlopen(f"{local_server}/api/status") as r:
        assert r.status == 200
        data = json.loads(r.read().decode("utf-8"))
        assert "is_running" in data


def test_api_birthday(local_server):
    req = urllib.request.Request(
        f"{local_server}/api/birthday",
        data=json.dumps({"n": 38, "m": 1000}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        assert r.status == 200
        data = json.loads(r.read().decode("utf-8"))
        assert abs(data["probability_pct"] - 50.93) < 0.1
