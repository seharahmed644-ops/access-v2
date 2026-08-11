
    def api_delete(self, parsed):
        conn = db()
        try:
            row = self.require_admin(conn)
            if not row: return
            parts = self.parts()
            if len(parts) == 4 and parts[:3] == ["api", "admin", "opportunities"]:
                try: oid = int(parts[3])
                except ValueError: return self.send_json({"error": "Invalid opportunity id"}, 400)
                cur = conn.execute("DELETE FROM opportunities WHERE id=?", (oid,)); conn.commit()
                return self.send_json({"ok": bool(cur.rowcount)})
            return self.send_json({"error": "Not found"}, 404)
        finally:
            conn.close()

    def serve_static(self, request_path):
        path = request_path or "/"
        if path == "/": path = "/index.html"
        candidate = (PUBLIC / path.lstrip("/")).resolve()
        try: candidate.relative_to(PUBLIC.resolve())
        except ValueError: return self.send_error(403)
        if not candidate.exists() or not candidate.is_file(): candidate = PUBLIC / "index.html"
        content = candidate.read_bytes()
        mime = mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", mime + ("; charset=utf-8" if mime.startswith("text/") or mime in {"application/javascript", "application/json"} else ""))
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache" if candidate.name == "index.html" else "public, max-age=600")
        self.security_headers()
        self.end_headers(); self.wfile.write(content)


if __name__ == "__main__":
    init_db()
    print(f"Access v2 running at http://{HOST}:{PORT}")
    print(f"Admin account configured for: {ADMIN_EMAIL}" if ADMIN_EMAIL and ADMIN_PASSWORD else "Admin account disabled until environment credentials are set.")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
