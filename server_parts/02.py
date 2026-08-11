        if not morsel:
            return None
        return conn.execute("""SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id
                              WHERE s.token=? AND s.expires_at>?""", (morsel.value, now_iso())).fetchone()

    def require_user(self, conn):
        user = self.session_user(conn)
        if not user:
            self.send_json({"error": "Authentication required"}, 401)
        return user

    def require_admin(self, conn):
        user = self.require_user(conn)
        if user and user["role"] != "admin":
            self.send_json({"error": "Admin access required"}, 403)
            return None
        return user

    def create_session(self, conn, user_id):
        token = secrets.token_urlsafe(32)
        expires = (datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)).isoformat()
        conn.execute("INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)", (token, user_id, expires))
        conn.commit()
        secure = "; Secure" if SECURE_COOKIES else ""
        return f"access_session={token}; Path=/; HttpOnly; SameSite=Lax{secure}; Max-Age={SESSION_DAYS * 86400}"

    def parts(self):
        return [x for x in urlparse(self.path).path.split("/") if x]

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.api_get(parsed)
        else:
            self.serve_static(parsed.path)

    def do_POST(self):
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            return self.send_error(404)
        if not self.same_origin():
            return self.send_json({"error": "Cross-origin request blocked"}, 403)
        self.api_post(parsed)

    def do_PUT(self):
        parsed = urlparse(self.path)
        if not self.same_origin():
            return self.send_json({"error": "Cross-origin request blocked"}, 403)
        self.api_put(parsed)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        if not self.same_origin():
            return self.send_json({"error": "Cross-origin request blocked"}, 403)
        self.api_delete(parsed)

    def api_get(self, parsed):
        conn = db()
        try:
            path = parsed.path
            if path == "/api/health":
                return self.send_json({"ok": True, "version": "2.1"})
            if path == "/api/me":
                return self.send_json({"user": user_public(self.session_user(conn))})
            row = self.require_user(conn)
            if not row:
                return
            user = user_public(row)
            if path == "/api/dashboard":
                uid = user["id"]
                stats = {
                    "saved": conn.execute("SELECT COUNT(*) FROM saved WHERE user_id=?", (uid,)).fetchone()[0],
                    "applications": conn.execute("SELECT COUNT(*) FROM applications WHERE user_id=?", (uid,)).fetchone()[0],
                    "submitted": conn.execute("SELECT COUNT(*) FROM applications WHERE user_id=? AND status='submitted'", (uid,)).fetchone()[0],
                    "won": conn.execute("SELECT COUNT(*) FROM applications WHERE user_id=? AND status='won'", (uid,)).fetchone()[0],
                    "due_soon": conn.execute("SELECT COUNT(*) FROM opportunities WHERE date(deadline) BETWEEN date('now') AND date('now','+30 day')").fetchone()[0],
                    "available": conn.execute("SELECT COUNT(*) FROM opportunities WHERE date(deadline)>=date('now')").fetchone()[0],
                }
                return self.send_json({"stats": stats})
            if path == "/api/opportunities":
                qs = parse_qs(parsed.query)
                q = (qs.get("q", [""])[0] or "").strip().lower()
                type_filter = (qs.get("type", [""])[0] or "").strip()
                sort = qs.get("sort", ["match"])[0]
                saved_only = qs.get("saved", ["0"])[0] == "1"
                app_only = qs.get("applications", ["0"])[0] == "1"
                verified_only = qs.get("verified", ["0"])[0] == "1"
                rows = conn.execute("SELECT * FROM opportunities WHERE date(deadline)>=date('now')").fetchall()
                saved_ids = {r[0] for r in conn.execute("SELECT opportunity_id FROM saved WHERE user_id=?", (user["id"],))}
                apps = {r["opportunity_id"]: {"status": r["status"], "notes": r["notes"], "updated_at": r["updated_at"]}
                        for r in conn.execute("SELECT * FROM applications WHERE user_id=?", (user["id"],))}
                items = []
                for r in rows:
                    item = opportunity_public(r, user, r["id"] in saved_ids, apps.get(r["id"]))
                    hay = " ".join([item["title"], item["org"], item["type"], item["description"], " ".join(item["interests"])]).lower()
                    if q and q not in hay: continue
                    if type_filter and type_filter != "All" and item["type"] != type_filter: continue
                    if saved_only and not item["saved"]: continue
                    if app_only and not item["application"]: continue
                    if verified_only and not item["verified"]: continue
                    items.append(item)
                if sort == "deadline": items.sort(key=lambda x: x["deadline"])
                elif sort == "value": items.sort(key=lambda x: x["value"], reverse=True)
                else: items.sort(key=lambda x: (x["match_score"], x["verified"], x["deadline"]), reverse=True)
                return self.send_json({"items": items, "total": len(items)})
            if path == "/api/admin/stats":
                if row["role"] != "admin": return self.send_json({"error": "Admin access required"}, 403)
                stats = {
                    "students": conn.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0],
                    "opportunities": conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0],
                    "verified": conn.execute("SELECT COUNT(*) FROM opportunities WHERE verified=1").fetchone()[0],
                    "saves": conn.execute("SELECT COUNT(*) FROM saved").fetchone()[0],
                    "applications": conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0],
                }
                recent = [dict(r) for r in conn.execute("SELECT id,title,org,type,deadline,verified,is_demo FROM opportunities ORDER BY id DESC LIMIT 40")]
                return self.send_json({"stats": stats, "recent": recent})
            parts = self.parts()
            if len(parts) == 3 and parts[:2] == ["api", "opportunities"]:
                try: oid = int(parts[2])
                except ValueError: return self.send_json({"error": "Invalid opportunity id"}, 400)
                r = conn.execute("SELECT * FROM opportunities WHERE id=?", (oid,)).fetchone()
                if not r: return self.send_json({"error": "Opportunity not found"}, 404)
                saved = bool(conn.execute("SELECT 1 FROM saved WHERE user_id=? AND opportunity_id=?", (user["id"], oid)).fetchone())
                app = conn.execute("SELECT status,notes,updated_at FROM applications WHERE user_id=? AND opportunity_id=?", (user["id"], oid)).fetchone()
                return self.send_json({"item": opportunity_public(r, user, saved, dict(app) if app else None)})
            return self.send_json({"error": "Not found"}, 404)
        finally:
            conn.close()

    def api_post(self, parsed):
        conn = db()
        try:
            try: body = self.read_json()
            except ValueError as e: return self.send_json({"error": str(e)}, 400)
            path = parsed.path
            if path == "/api/register":
                name = str(body.get("name", "")).strip()[:80]
                email = str(body.get("email", "")).strip().lower()[:200]
                password = str(body.get("password", ""))
                grade = str(body.get("grade", "")).strip()[:30]
                location = str(body.get("location", "")).strip()[:120]
                interests = parse_list(body.get("interests", []))[:20]
                if len(name) < 2 or "@" not in email or len(password) < 8:
                    return self.send_json({"error": "Enter a name, valid email, and password of at least 8 characters."}, 400)
                if conn.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
                    return self.send_json({"error": "An account with that email already exists."}, 409)
                salt, digest = hash_password(password)
                cur = conn.execute("INSERT INTO users(name,email,password_hash,salt,role,grade,location,interests,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                                   (name, email, digest, salt, "student", grade, location, json.dumps(interests), now_iso()))
                conn.commit()
                cookie = self.create_session(conn, cur.lastrowid)
                r = conn.execute("SELECT * FROM users WHERE id=?", (cur.lastrowid,)).fetchone()
                return self.send_json({"user": user_public(r)}, 201, {"Set-Cookie": cookie})
            if path == "/api/login":
                email = str(body.get("email", "")).strip().lower()
                password = str(body.get("password", ""))
                r = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
                if not r or not verify_password(password, r["salt"], r["password_hash"]):
                    return self.send_json({"error": "Invalid email or password."}, 401)
                return self.send_json({"user": user_public(r)}, 200, {"Set-Cookie": self.create_session(conn, r["id"])})
            if path == "/api/logout":
                cookie = SimpleCookie(self.headers.get("Cookie", ""))
                if cookie.get("access_session"):
                    conn.execute("DELETE FROM sessions WHERE token=?", (cookie["access_session"].value,)); conn.commit()
                secure = "; Secure" if SECURE_COOKIES else ""
                return self.send_json({"ok": True}, 200, {"Set-Cookie": f"access_session=; Path=/; HttpOnly; SameSite=Lax{secure}; Max-Age=0"})
            row = self.require_user(conn)
            if not row: return
            user = user_public(row)
            parts = self.parts()
            if len(parts) == 4 and parts[:2] == ["api", "opportunities"] and parts[3] == "save":
                try: oid = int(parts[2])
                except ValueError: return self.send_json({"error": "Invalid opportunity id"}, 400)
                if not conn.execute("SELECT 1 FROM opportunities WHERE id=?", (oid,)).fetchone(): return self.send_json({"error": "Opportunity not found"}, 404)
                exists = conn.execute("SELECT 1 FROM saved WHERE user_id=? AND opportunity_id=?", (user["id"], oid)).fetchone()
                if exists:
                    conn.execute("DELETE FROM saved WHERE user_id=? AND opportunity_id=?", (user["id"], oid)); saved = False
                else:
                    conn.execute("INSERT INTO saved(user_id,opportunity_id,created_at) VALUES(?,?,?)", (user["id"], oid, now_iso())); saved = True
                conn.commit(); return self.send_json({"saved": saved})
            if len(parts) == 4 and parts[:2] == ["api", "opportunities"] and parts[3] == "application":
                try: oid = int(parts[2])
                except ValueError: return self.send_json({"error": "Invalid opportunity id"}, 400)
                status = str(body.get("status", "planning"))
                notes = str(body.get("notes", ""))[:4000]
                if status not in ALLOWED_STATUSES: return self.send_json({"error": "Invalid application status"}, 400)
                conn.execute("""INSERT INTO applications(user_id,opportunity_id,status,notes,updated_at) VALUES(?,?,?,?,?)
                                ON CONFLICT(user_id,opportunity_id) DO UPDATE SET status=excluded.status,notes=excluded.notes,updated_at=excluded.updated_at""",
                             (user["id"], oid, status, notes, now_iso()))
                conn.commit(); return self.send_json({"ok": True, "application": {"status": status, "notes": notes}})
            if len(parts) == 4 and parts[:2] == ["api", "opportunities"] and parts[3] == "click":
                try: oid = int(parts[2])
                except ValueError: return self.send_json({"error": "Invalid opportunity id"}, 400)
                conn.execute("INSERT INTO events(user_id,opportunity_id,event_type,created_at) VALUES(?,?,?,?)", (user["id"], oid, "outbound_click", now_iso())); conn.commit()
                return self.send_json({"ok": True})
            if path == "/api/admin/opportunities":
                if row["role"] != "admin": return self.send_json({"error": "Admin access required"}, 403)
                item, err = validate_opportunity(body)
                if err: return self.send_json({"error": err}, 400)
                cur = conn.execute("""INSERT INTO opportunities(title,org,type,interests,grades,location,deadline,value,description,url,verified,is_demo,created_at)
                                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                   (item["title"], item["org"], item["type"], json.dumps(item["interests"]), json.dumps(item["grades"]), item["location"], item["deadline"], item["value"], item["description"], item["url"], int(item["verified"]), 0, now_iso()))
                conn.commit(); r = conn.execute("SELECT * FROM opportunities WHERE id=?", (cur.lastrowid,)).fetchone()
                return self.send_json({"item": opportunity_public(r)}, 201)
            if path == "/api/admin/import-csv":
                if row["role"] != "admin": return self.send_json({"error": "Admin access required"}, 403)
                text = str(body.get("csv", ""))
                if not text.strip(): return self.send_json({"error": "CSV content is empty"}, 400)
                imported, errors = 0, []
                for line_no, csv_row in enumerate(csv.DictReader(io.StringIO(text)), 2):
                    item, err = validate_opportunity(csv_row)
                    if err:
                        errors.append(f"Row {line_no}: {err}"); continue
                    conn.execute("""INSERT INTO opportunities(title,org,type,interests,grades,location,deadline,value,description,url,verified,is_demo,created_at)
                                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                 (item["title"], item["org"], item["type"], json.dumps(item["interests"]), json.dumps(item["grades"]), item["location"], item["deadline"], item["value"], item["description"], item["url"], int(item["verified"]), 0, now_iso()))
                    imported += 1
                conn.commit(); return self.send_json({"imported": imported, "errors": errors[:25]})
            return self.send_json({"error": "Not found"}, 404)
        finally:
            conn.close()

    def api_put(self, parsed):
        conn = db()
        try:
            try: body = self.read_json()
            except ValueError as e: return self.send_json({"error": str(e)}, 400)
            row = self.require_user(conn)
            if not row: return
            if parsed.path == "/api/me/profile":
                name = str(body.get("name", row["name"])).strip()[:80]
                grade = str(body.get("grade", row["grade"])).strip()[:30]
                location = str(body.get("location", row["location"])).strip()[:120]
                interests = parse_list(body.get("interests", parse_list(row["interests"])))[:20]
                if len(name) < 2: return self.send_json({"error": "Name is too short"}, 400)
                conn.execute("UPDATE users SET name=?,grade=?,location=?,interests=? WHERE id=?", (name, grade, location, json.dumps(interests), row["id"])); conn.commit()
                return self.send_json({"user": user_public(conn.execute("SELECT * FROM users WHERE id=?", (row["id"],)).fetchone())})
            parts = self.parts()
            if len(parts) == 4 and parts[:3] == ["api", "admin", "opportunities"]:
                if row["role"] != "admin": return self.send_json({"error": "Admin access required"}, 403)
                try: oid = int(parts[3])
                except ValueError: return self.send_json({"error": "Invalid opportunity id"}, 400)
                item, err = validate_opportunity(body)
                if err: return self.send_json({"error": err}, 400)
                cur = conn.execute("""UPDATE opportunities SET title=?,org=?,type=?,interests=?,grades=?,location=?,deadline=?,value=?,description=?,url=?,verified=?,is_demo=0 WHERE id=?""",
                                   (item["title"], item["org"], item["type"], json.dumps(item["interests"]), json.dumps(item["grades"]), item["location"], item["deadline"], item["value"], item["description"], item["url"], int(item["verified"]), oid))
                conn.commit(); return self.send_json({"ok": bool(cur.rowcount)})
            return self.send_json({"error": "Not found"}, 404)
        finally:
            conn.close()
