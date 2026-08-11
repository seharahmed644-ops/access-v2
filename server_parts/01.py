import csv
import hashlib
import hmac
import io
import json
import mimetypes
import os
import secrets
import sqlite3
from datetime import date, datetime, timedelta, timezone
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
DB_PATH = DATA / "access.db"
HOST = os.environ.get("ACCESS_HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", os.environ.get("ACCESS_PORT", "8000")))
ADMIN_EMAIL = os.environ.get("ACCESS_ADMIN_EMAIL", "").strip().lower()
ADMIN_PASSWORD = os.environ.get("ACCESS_ADMIN_PASSWORD", "")
SECURE_COOKIES = bool(os.environ.get("RENDER")) or os.environ.get("ACCESS_SECURE_COOKIES", "").lower() in {"1", "true", "yes"}
SESSION_DAYS = 14
PBKDF2_ROUNDS = 210_000
ALLOWED_TYPES = {"Scholarship", "Internship", "Program", "Competition", "Volunteer", "Research", "Fellowship"}
ALLOWED_STATUSES = {"planning", "in_progress", "submitted", "interview", "won", "rejected"}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def hash_password(password, salt=None):
    salt_bytes = bytes.fromhex(salt) if salt else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt_bytes, PBKDF2_ROUNDS)
    return salt_bytes.hex(), digest.hex()


def verify_password(password, salt, expected):
    _, got = hash_password(password, salt)
    return hmac.compare_digest(got, expected)


def parse_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    text = str(value).strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            val = json.loads(text)
            if isinstance(val, list):
                return [str(x).strip() for x in val if str(x).strip()]
        except json.JSONDecodeError:
            pass
    return [x.strip() for x in text.split(",") if x.strip()]


def user_public(row):
    if not row:
        return None
    return {"id": row["id"], "name": row["name"], "email": row["email"], "role": row["role"],
            "grade": row["grade"], "location": row["location"], "interests": parse_list(row["interests"])}


def match_score(row, user):
    if not user or user.get("role") == "admin":
        return 100
    score = 48
    interests = {x.lower() for x in parse_list(row["interests"])}
    mine = {x.lower() for x in user.get("interests", [])}
    score += min(32, len(interests & mine) * 12)
    grades = {x.lower() for x in parse_list(row["grades"])}
    grade = str(user.get("grade", "")).lower()
    if grade and (not grades or grade in grades or "all" in grades):
        score += 10
    location = (row["location"] or "").lower()
    mine_loc = (user.get("location") or "").lower()
    if "online" in location or "remote" in location or (mine_loc and any(p in location for p in mine_loc.split(",") if len(p.strip()) > 2)):
        score += 7
    if row["verified"]:
        score += 3
    return min(99, max(35, score))


def opportunity_public(row, user=None, saved=False, application=None):
    return {
        "id": row["id"], "title": row["title"], "org": row["org"], "type": row["type"],
        "interests": parse_list(row["interests"]), "grades": parse_list(row["grades"]),
        "location": row["location"], "deadline": row["deadline"], "value": row["value"],
        "description": row["description"], "url": row["url"], "verified": bool(row["verified"]),
        "is_demo": bool(row["is_demo"]), "match_score": match_score(row, user), "saved": bool(saved),
        "application": application,
    }


def init_db():
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL, salt TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'student',
      grade TEXT DEFAULT '', location TEXT DEFAULT '', interests TEXT DEFAULT '[]', created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS sessions(
      token TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, expires_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS opportunities(
      id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, org TEXT NOT NULL, type TEXT NOT NULL,
      interests TEXT DEFAULT '[]', grades TEXT DEFAULT '[]', location TEXT DEFAULT 'Online', deadline TEXT NOT NULL,
      value INTEGER DEFAULT 0, description TEXT DEFAULT '', url TEXT DEFAULT '', verified INTEGER DEFAULT 0,
      is_demo INTEGER DEFAULT 0, created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS saved(
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      opportunity_id INTEGER NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
      created_at TEXT NOT NULL, PRIMARY KEY(user_id, opportunity_id)
    );
    CREATE TABLE IF NOT EXISTS applications(
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      opportunity_id INTEGER NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
      status TEXT NOT NULL DEFAULT 'planning', notes TEXT DEFAULT '', updated_at TEXT NOT NULL,
      PRIMARY KEY(user_id, opportunity_id)
    );
    CREATE TABLE IF NOT EXISTS events(
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, opportunity_id INTEGER,
      event_type TEXT NOT NULL, created_at TEXT NOT NULL
    );
    """)
    if conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0] == 0:
        seed_demo(conn)
    if ADMIN_EMAIL and ADMIN_PASSWORD:
        if len(ADMIN_PASSWORD) < 12:
            raise RuntimeError("ACCESS_ADMIN_PASSWORD must be at least 12 characters")
        row = conn.execute("SELECT id FROM users WHERE email=?", (ADMIN_EMAIL,)).fetchone()
        if not row:
            salt, digest = hash_password(ADMIN_PASSWORD)
            conn.execute("INSERT INTO users(name,email,password_hash,salt,role,grade,location,interests,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                         ("Access Admin", ADMIN_EMAIL, digest, salt, "admin", "", "", "[]", now_iso()))
    conn.commit()
    conn.close()


def seed_demo(conn):
    types = ["Scholarship", "Internship", "Program", "Research", "Competition", "Fellowship", "Volunteer"]
    interests = ["STEM", "Research", "Technology", "Business", "Entrepreneurship", "Leadership", "Community", "Writing", "Arts", "Design", "Health", "Environment", "Public Policy"]
    orgs = ["Northstar Foundation", "Future Builders Network", "Civic Spark Lab", "BrightPath Institute", "Youth Impact Collective", "Open Horizons Center"]
    today = date.today()
    for i in range(240):
        kind = types[i % len(types)]
        a = interests[i % len(interests)]
        b = interests[(i * 3 + 4) % len(interests)]
        deadline = today + timedelta(days=18 + (i * 7) % 330)
        value = 0 if kind in {"Volunteer", "Program", "Research"} else 500 + (i % 12) * 750
        title = f"{a} {kind} Opportunity {i + 1}"
        org = orgs[i % len(orgs)]
        desc = f"Fictional demo {kind.lower()} for students interested in {a} and {b}. This listing is included only to demonstrate Access product features."
        conn.execute("""INSERT INTO opportunities(title,org,type,interests,grades,location,deadline,value,description,url,verified,is_demo,created_at)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                     (title, org, kind, json.dumps([a, b]), json.dumps(["9", "10", "11", "12", "College"]),
                      "Online", deadline.isoformat(), value, desc, "", 0, 1, now_iso()))


def validate_opportunity(body):
    title = str(body.get("title", "")).strip()
    org = str(body.get("org", "")).strip()
    kind = str(body.get("type", "Program")).strip().title()
    location = str(body.get("location", "Online")).strip() or "Online"
    deadline = str(body.get("deadline", "")).strip()
    description = str(body.get("description", "")).strip()[:5000]
    url = str(body.get("url", "")).strip()
    interests = parse_list(body.get("interests", []))
    grades = parse_list(body.get("grades", []))
    try:
        value = max(0, int(float(body.get("value", 0) or 0)))
    except (ValueError, TypeError):
        return None, "Value must be a number"
    raw_verified = body.get("verified", False)
    verified = raw_verified if isinstance(raw_verified, bool) else str(raw_verified).lower() in {"1", "true", "yes", "y"}
    if len(title) < 3 or len(org) < 2:
        return None, "Title and organization are required"
    if kind not in ALLOWED_TYPES:
        return None, "Invalid opportunity type"
    try:
        date.fromisoformat(deadline)
    except ValueError:
        return None, "Deadline must use YYYY-MM-DD"
    if url and not url.startswith(("https://", "http://")):
        return None, "URL must start with http:// or https://"
    return {"title": title, "org": org, "type": kind, "location": location, "deadline": deadline,
            "description": description, "url": url, "interests": interests, "grades": grades,
            "value": value, "verified": verified}, None


class Handler(BaseHTTPRequestHandler):
    server_version = "Access/2.1"

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}")

    def send_json(self, data, status=200, extra=None):
        payload = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.security_headers()
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(payload)

    def security_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'")

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length > 2_000_000:
            raise ValueError("Request body too large")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode())
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("Invalid JSON")

    def same_origin(self):
        origin = self.headers.get("Origin")
        if not origin:
            return True
        return urlparse(origin).netloc.lower() == self.headers.get("Host", "").lower()

    def session_user(self, conn):
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        morsel = cookie.get("access_session")
