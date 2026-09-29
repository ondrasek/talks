# app.py: a web page that counts its visits and keeps the count in /data.
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

COUNT = Path("/data/count.txt")

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        COUNT.parent.mkdir(parents=True, exist_ok=True)
        n = int(COUNT.read_text()) + 1 if COUNT.exists() else 1
        COUNT.write_text(str(n))
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(f"visit {n}\n".encode())

HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
