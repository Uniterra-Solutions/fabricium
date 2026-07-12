"""Reasoning-model SSE proxy for Hermes eval containers.

DeepSeek V4 outputs chain-of-thought in ``reasoning_content`` before the
final answer in ``content``.  Hermes sees ``content: null`` during the
reasoning phase and fails with "empty stream".

This proxy:
- Forwards chunks with non-null ``content`` as-is
- Silently drops ``reasoning_content`` during streaming (so Hermes only
  sees the final answer)
- For non-streaming: falls back to ``reasoning_content`` if ``content``
  is empty
"""

from __future__ import annotations

import gzip
import http.server
import json
import os
import re
import sys
import urllib.request
from typing import Any

# ── SSE chunk transformation ────────────────────────────────────────

# Pattern: "content":null  →  "content":""
_RE_CONTENT_NULL = re.compile(r'"content"\s*:\s*null')


def _patch_sse_chunk(line: str) -> str:
    """Replace ``content: null`` with ``content: \"\"`` so Hermes doesn't
    see a null content field.  Reasoning text is left in
    ``reasoning_content`` (which Hermes ignores)."""
    if '"content":null' in line:
        return _RE_CONTENT_NULL.sub('"content":""', line)
    return line


def _patch_non_streaming_body(data: dict[str, Any]) -> dict[str, Any]:
    """Non-streaming: fall back to reasoning_content if content is empty."""
    for choice in data.get("choices", []):
        msg = choice.get("message", {})
        if not msg.get("content") and msg.get("reasoning_content"):
            msg["content"] = msg["reasoning_content"]
    return data


# ── HTTP proxy handler ──────────────────────────────────────────────


class _ProxyHandler(http.server.BaseHTTPRequestHandler):
    upstream_base: str = ""
    api_key: str = ""
    _proxy_timeout: int = 300

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b""

        # Ensure /v1 prefix — Hermes may send /chat/completions or /v1/chat/completions
        path = self.path
        if not path.startswith("/v1/"):
            path = "/v1" + path

        req = urllib.request.Request(self.upstream_base + path, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {self.api_key}")
        for key, val in self.headers.items():
            if key.lower() in ("host", "authorization", "content-length"):
                continue
            req.add_header(key, val)

        try:
            with urllib.request.urlopen(req, timeout=self._proxy_timeout) as resp:
                ct = resp.headers.get("Content-Type", "")
                ce = resp.headers.get("Content-Encoding", "")
                is_stream = "text/event-stream" in ct

                print(
                    f"proxy: {self.command} {self.path} → {path} ct={ct!r} stream={is_stream}",
                    file=sys.stderr,
                    flush=True,
                )

                if is_stream:
                    self._proxy_stream(resp, ce)
                else:
                    self._proxy_non_stream(resp, ce)
        except urllib.error.HTTPError as e:
            err_body = e.read() if hasattr(e, "read") else b"{}"
            print(f"proxy: HTTP {e.code}", file=sys.stderr, flush=True)
            self._respond(e.code, "application/json", err_body)
        except Exception as e:
            print(f"proxy: ERROR {e}", file=sys.stderr, flush=True)
            body_err = json.dumps({"error": str(e)}).encode()
            self._respond(502, "application/json", body_err)

    def _proxy_stream(self, resp: "http.client.HTTPResponse", content_encoding: str) -> None:
        """Stream SSE chunks, replacing content:null → content:\"\"."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        buf = b""
        while True:
            try:
                chunk = resp.read1(4096)
            except Exception:
                break
            if not chunk:
                break

            buf += chunk
            if content_encoding == "gzip" and buf[:2] == b"\x1f\x8b":
                try:
                    buf = gzip.decompress(buf)
                except Exception:
                    pass
                content_encoding = ""

            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                line_str = line.decode("utf-8", errors="replace")
                if line_str.startswith("data:"):
                    line_str = _patch_sse_chunk(line_str)
                self.wfile.write(line_str.encode() + b"\n")
                self.wfile.flush()

        if buf:
            line_str = buf.decode("utf-8", errors="replace")
            if line_str.startswith("data:"):
                line_str = _patch_sse_chunk(line_str)
            self.wfile.write(line_str.encode() + b"\n")
            self.wfile.flush()

    def _proxy_non_stream(self, resp: "http.client.HTTPResponse", content_encoding: str) -> None:
        """Read full non-streaming response and patch."""
        raw = resp.read()
        if content_encoding == "gzip" or raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        if not raw.strip():
            self._respond(200, "application/json", b'{"choices":[]}')
            return
        data: dict[str, Any] = json.loads(raw)
        patched = _patch_non_streaming_body(data)
        self._respond(200, "application/json", json.dumps(patched).encode())

    def do_GET(self) -> None:
        if self.path in ("/", "/health"):
            self._respond(200, "text/plain", b"ok")

    def _respond(self, code: int, content_type: str, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: ARG002
        pass


# ── Entry point ──────────────────────────────────────────────────────


def _run(upstream: str, api_key: str, port: int) -> None:
    _ProxyHandler.upstream_base = upstream.rstrip("/")
    _ProxyHandler.api_key = api_key
    server = http.server.HTTPServer(("127.0.0.1", port), _ProxyHandler)
    print(f"proxy: listening on 127.0.0.1:{port} -> {upstream}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            f"Usage: python3 {sys.argv[0]} <API_KEY> <UPSTREAM_BASE_URL> [PORT]",
            file=sys.stderr,
        )
        sys.exit(1)

    api_key = sys.argv[1]
    upstream = sys.argv[2]
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 9090

    pidfile = os.environ.get("PROXY_PIDFILE", "")
    if pidfile:
        with open(pidfile, "w") as f:
            f.write(str(os.getpid()))

    _run(upstream, api_key, port)
