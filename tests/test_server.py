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


def test_api_live_stream(local_server):
    with urllib.request.urlopen(f"{local_server}/api/live/stream") as r:
        assert r.status == 200
        data = json.loads(r.read().decode("utf-8"))
        assert "uniqueness_pct" in data
        assert "prefix_similarity_pct" in data
        assert "active_method" in data
        assert "recent_codes" in data


def test_api_live_config(local_server):
    req = urllib.request.Request(
        f"{local_server}/api/live/config",
        data=json.dumps({"method": "standard_second", "speed": 20.0, "is_paused": False}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        assert r.status == 200
        data = json.loads(r.read().decode("utf-8"))
        assert data["success"] is True
        assert data["snapshot"]["active_method"] == "standard_second"
        assert data["snapshot"]["speed_eps"] == 20.0

