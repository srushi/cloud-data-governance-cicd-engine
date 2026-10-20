"""Tiny report server used by the Kubernetes Deployment.

Serves the latest audit summary at ``/summary`` and a liveness probe at
``/health`` using only the Python standard library, so the container image
stays slim. This is what the K8s Service fronts; the audits themselves are
run by the CronJob / CLI.
"""

from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer


def make_handler(report_dir: str):
    class Handler(BaseHTTPRequestHandler):
        def _send_json(self, payload: dict, status: int = 200) -> None:
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
            if self.path == "/health":
                self._send_json({"status": "ok"})
            elif self.path == "/summary":
                path = os.path.join(report_dir, "summary.json")
                if os.path.exists(path):
                    with open(path, encoding="utf-8") as fh:
                        self._send_json(json.load(fh))
                else:
                    self._send_json({"error": "no audit report yet"}, status=404)
            else:
                self._send_json({"error": "not found"}, status=404)

        def log_message(self, *args) -> None:  # keep logs quiet
            pass

    return Handler


def main() -> None:  # pragma: no cover - blocking server entry point
    parser = argparse.ArgumentParser(description="Pipeline engine report server")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--report-dir", default="out")
    args = parser.parse_args()
    server = HTTPServer(("0.0.0.0", args.port), make_handler(args.report_dir))
    print(f"Serving reports from {args.report_dir} on :{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
