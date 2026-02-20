import json
import os
import uuid
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PREFS_FILE = DATA_DIR / "notification_prefs.json"

MOCK_USERS = {
    "shipper": {"label": "Shipper", "permissions": ["track", "notifications"]},
    "freight_forwarder": {
        "label": "Freight Forwarder",
        "permissions": ["track", "notifications"],
    },
    "viewer": {"label": "Viewer", "permissions": ["track"]},
    "admin": {"label": "Admin", "permissions": ["track", "notifications", "admin"]},
}

SHIPMENTS = [
    {
        "bookingNumber": "BK-2026-1001",
        "blNumber": "BL-775533",
        "containerNumber": "MSCU1234567",
        "vesselName": "MSC Aurora",
        "voyage": "VOY-AX12",
        "currentPort": "Antwerp",
        "eta": "2026-02-24T09:30:00Z",
        "status": "In Transit",
        "events": [
            {"name": "Booking Confirmation", "timestamp": "2026-02-10 08:22", "location": "Ghent"},
            {"name": "Gate In Full", "timestamp": "2026-02-12 14:40", "location": "Antwerp"},
            {"name": "Vessel Departure", "timestamp": "2026-02-14 21:15", "location": "Antwerp"},
            {"name": "Transshipment", "timestamp": "2026-02-18 06:00", "location": "Algeciras"},
        ],
    },
    {
        "bookingNumber": "BK-2026-2044",
        "blNumber": "BL-991200",
        "containerNumber": "MSCU7654321",
        "vesselName": "MSC Horizon",
        "voyage": "VOY-HZ77",
        "currentPort": "Valencia",
        "eta": "2026-02-26T13:00:00Z",
        "status": "Delayed",
        "events": [
            {"name": "Booking Confirmation", "timestamp": "2026-02-11 10:10", "location": "Rotterdam"},
            {"name": "Gate In Full", "timestamp": "2026-02-13 17:45", "location": "Rotterdam"},
            {"name": "Vessel Departure", "timestamp": "2026-02-15 23:30", "location": "Rotterdam"},
            {"name": "Delay Notice", "timestamp": "2026-02-19 12:30", "location": "At Sea"},
        ],
    },
]

SESSIONS = {}


def ensure_storage():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not PREFS_FILE.exists():
        PREFS_FILE.write_text("{}", encoding="utf-8")


def load_prefs():
    ensure_storage()
    try:
        return json.loads(PREFS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_prefs(data):
    ensure_storage()
    PREFS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def user_pref_key(email, role):
    return f"{email.lower()}::{role}"


class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/me":
            return self.handle_me()
        if parsed.path == "/api/shipments/search":
            return self.handle_search(parsed)
        if parsed.path == "/api/notifications":
            return self.handle_get_notifications()
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/login":
            return self.handle_login()
        if parsed.path == "/api/logout":
            return self.handle_logout()
        return self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_PUT(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/notifications":
            return self.handle_put_notifications()
        return self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def parse_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return None

    def get_session(self):
        raw_cookie = self.headers.get("Cookie", "")
        cookie = SimpleCookie()
        cookie.load(raw_cookie)
        session_cookie = cookie.get("session_id")
        if not session_cookie:
            return None, None
        session_id = session_cookie.value
        return session_id, SESSIONS.get(session_id)

    def require_session(self):
        session_id, session = self.get_session()
        if not session:
            self.send_json({"error": "Unauthorized"}, HTTPStatus.UNAUTHORIZED)
            return None, None
        return session_id, session

    def send_json(self, payload, status=HTTPStatus.OK, extra_headers=None):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if extra_headers:
            for name, value in extra_headers.items():
                self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def handle_login(self):
        body = self.parse_body()
        if body is None:
            return self.send_json({"error": "Invalid JSON"}, HTTPStatus.BAD_REQUEST)

        email = str(body.get("email", "")).strip()
        password = str(body.get("password", ""))
        role = str(body.get("role", ""))

        if not email or role not in MOCK_USERS:
            return self.send_json({"error": "Invalid login payload"}, HTTPStatus.BAD_REQUEST)
        if password != "demo":
            return self.send_json({"error": "Invalid password"}, HTTPStatus.UNAUTHORIZED)

        session_id = str(uuid.uuid4())
        user = {
            "email": email,
            "role": role,
            "roleLabel": MOCK_USERS[role]["label"],
            "permissions": MOCK_USERS[role]["permissions"],
        }
        SESSIONS[session_id] = user

        headers = {"Set-Cookie": f"session_id={session_id}; Path=/; HttpOnly; SameSite=Lax"}
        return self.send_json({"user": user}, HTTPStatus.OK, headers)

    def handle_logout(self):
        session_id, _ = self.get_session()
        if session_id:
            SESSIONS.pop(session_id, None)
        headers = {"Set-Cookie": "session_id=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"}
        return self.send_json({"ok": True}, HTTPStatus.OK, headers)

    def handle_me(self):
        _, session = self.get_session()
        if not session:
            return self.send_json({"authenticated": False}, HTTPStatus.OK)
        return self.send_json({"authenticated": True, "user": session}, HTTPStatus.OK)

    def handle_search(self, parsed):
        _, session = self.require_session()
        if not session:
            return

        if "track" not in session["permissions"]:
            return self.send_json({"error": "Forbidden"}, HTTPStatus.FORBIDDEN)

        query = parse_qs(parsed.query)
        search_type = query.get("type", [""])[0]
        value = query.get("value", [""])[0].strip().upper()

        if search_type not in {"container", "bl", "booking"} or not value:
            return self.send_json({"error": "Invalid search parameters"}, HTTPStatus.BAD_REQUEST)

        def matches(shipment):
            if search_type == "container":
                return shipment["containerNumber"].upper() == value
            if search_type == "bl":
                return shipment["blNumber"].upper() == value
            return shipment["bookingNumber"].upper() == value

        shipment = next((item for item in SHIPMENTS if matches(item)), None)
        if not shipment:
            return self.send_json({"found": False}, HTTPStatus.OK)
        return self.send_json({"found": True, "shipment": shipment}, HTTPStatus.OK)

    def handle_get_notifications(self):
        _, session = self.require_session()
        if not session:
            return

        prefs = load_prefs()
        key = user_pref_key(session["email"], session["role"])
        user_prefs = prefs.get(key, {"email": False, "push": False})

        return self.send_json({"preferences": user_prefs}, HTTPStatus.OK)

    def handle_put_notifications(self):
        _, session = self.require_session()
        if not session:
            return

        if "notifications" not in session["permissions"]:
            return self.send_json({"error": "Forbidden"}, HTTPStatus.FORBIDDEN)

        body = self.parse_body()
        if body is None:
            return self.send_json({"error": "Invalid JSON"}, HTTPStatus.BAD_REQUEST)

        email_pref = bool(body.get("email", False))
        push_pref = bool(body.get("push", False))

        prefs = load_prefs()
        key = user_pref_key(session["email"], session["role"])
        prefs[key] = {"email": email_pref, "push": push_pref}
        save_prefs(prefs)

        return self.send_json({"ok": True, "preferences": prefs[key]}, HTTPStatus.OK)


def main():
    ensure_storage()
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), AppHandler)
    print(f"Server running on http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
