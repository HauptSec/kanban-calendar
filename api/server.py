"""Event storage API for the week board (Python stdlib only).

  GET    /api/events        -> list of all events
  PUT    /api/events/<id>   -> create or replace one event
  DELETE /api/events/<id>   -> delete one event

Events live in DATA_DIR/events.json. Every write goes to a temp file, is
fsynced, then atomically renamed over the old file, so a crash or power cut
leaves either the previous or the new data on disk, never a torn file.

Other paths are served as static files from the working directory, so
`python3 api/server.py` from the repo root runs the whole app for local dev.
In Docker, nginx serves the page and proxies /api here.
"""
import json
import os
import re
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

DATA_DIR = os.environ.get("DATA_DIR", ".data")
DATA_FILE = os.path.join(DATA_DIR, "events.json")
PORT = int(os.environ.get("PORT", "8000"))
MAX_BODY = 64 * 1024
EVENT_PATH = re.compile(r"/api/events/([A-Za-z0-9_-]{1,64})")
lock = threading.Lock()  # ponytail: one lock + whole-file rewrite per change; fine for a personal calendar


def load():
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def store(events):
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(events, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, DATA_FILE)
    fd = os.open(DATA_DIR, os.O_RDONLY)  # persist the rename itself
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class Handler(SimpleHTTPRequestHandler):
    def send_json(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def event_id(self):
        m = EVENT_PATH.fullmatch(self.path)
        return m and m[1]

    def do_GET(self):
        if self.path == "/api/events":
            with lock:
                return self.send_json(200, list(load().values()))
        if self.path.startswith("/api/"):
            return self.send_json(404, {"error": "not found"})
        super().do_GET()

    def do_PUT(self):
        event_id = self.event_id()
        if not event_id:
            return self.send_json(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            length = 0
        if not 0 < length <= MAX_BODY:
            return self.send_json(413 if length else 411, {"error": "bad body size"})
        try:
            event = json.loads(self.rfile.read(length))
        except ValueError:
            return self.send_json(400, {"error": "invalid JSON"})
        if not isinstance(event, dict) or event.get("id") != event_id:
            return self.send_json(400, {"error": "body must be an event object with matching id"})
        with lock:
            events = load()
            events[event_id] = event
            store(events)
        self.send_json(200, {"ok": True})

    def do_DELETE(self):
        event_id = self.event_id()
        if not event_id:
            return self.send_json(404, {"error": "not found"})
        with lock:
            events = load()
            if events.pop(event_id, None) is not None:
                store(events)
        self.send_json(200, {"ok": True})


if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"Serving on :{PORT}, data in {DATA_FILE}", flush=True)
    ThreadingHTTPServer(("", PORT), Handler).serve_forever()
