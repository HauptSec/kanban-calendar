"""Run: python3 api/test_server.py  (starts the API on a temp dir and exercises it)"""
import json
import os
import sys
import tempfile
import threading
import urllib.request
from http.server import ThreadingHTTPServer

os.environ["DATA_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.dirname(__file__))
import server  # noqa: E402

httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{httpd.server_port}/api/events"


def call(method, path="", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as res:
            return res.status, json.loads(res.read())
    except urllib.error.HTTPError as err:
        return err.code, None


ev = {"id": "abc-1", "title": "Gym", "date": "2026-10-19"}
assert call("GET") == (200, [])
assert call("PUT", "/abc-1", ev)[0] == 200
assert call("PUT", "/abc-1", {**ev, "title": "Gym!"})[0] == 200
assert call("GET") == (200, [{**ev, "title": "Gym!"}]), "upsert replaces"
assert call("PUT", "/other", ev)[0] == 400, "id must match path"
assert call("PUT", "/abc-1", [1, 2])[0] == 400, "body must be an object"
assert call("PUT", "/../etc", ev)[0] == 404, "unsafe ids rejected"
assert call("PUT", "/big", {"id": "big", "x": "a" * 70000})[0] == 413, "size limit"
with open(server.DATA_FILE) as f:
    assert json.load(f)["abc-1"]["title"] == "Gym!", "written to disk"
assert call("DELETE", "/abc-1")[0] == 200
assert call("GET") == (200, [])
assert not os.path.exists(server.DATA_FILE + ".tmp"), "no temp file left behind"

# Live updates: a write pushes a message to open streams
stream = urllib.request.urlopen(base + "/stream", timeout=5)
assert stream.headers["Content-Type"] == "text/event-stream"
assert stream.readline() == b"retry: 3000\n" and stream.readline() == b"\n"
call("PUT", "/live", {"id": "live"})
assert stream.readline().startswith(b"data: "), "change pushed to stream"
call("DELETE", "/missing")  # deleting nothing is not a change
call("DELETE", "/live")
assert stream.readline() == b"\n" and stream.readline().startswith(b"data: "), "delete pushed, no-op delete skipped"
stream.close()
print("api tests passed")
