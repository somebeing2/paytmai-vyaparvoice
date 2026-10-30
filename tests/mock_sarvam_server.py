import base64
import contextlib
import json
import struct
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Iterator, List, Tuple


def make_silent_wav_bytes(duration_ms: int = 80, sample_rate: int = 16000) -> bytes:
    """Create a valid minimal 16-bit mono PCM WAV payload for deterministic mock TTS tests."""
    num_samples = int(sample_rate * (duration_ms / 1000.0))
    data_size = num_samples * 2
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        sample_rate,
        sample_rate * 2,
        2,
        16,
        b"data",
        data_size,
    )
    return header + (b"\x00\x00" * num_samples)


class MockSarvamState:
    def __init__(self, expected_token: str = "mock-test-token-do-not-use-in-prod") -> None:
        self.expected_token = expected_token
        self.force_status: int = 200
        self.requests_log: List[Dict[str, object]] = []


@contextlib.contextmanager
def run_mock_sarvam_server(
    expected_token: str = "mock-test-token-do-not-use-in-prod",
) -> Iterator[Tuple[str, MockSarvamState]]:
    state = MockSarvamState(expected_token=expected_token)
    wav_b64 = base64.b64encode(make_silent_wav_bytes()).decode("ascii")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:
            return

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
            try:
                body = json.loads(raw_body)
            except Exception:
                body = {}

            sub_key = self.headers.get("api-subscription-key", "")
            state.requests_log.append(
                {
                    "path": self.path,
                    "has_auth": bool(sub_key),
                    "body": body,
                }
            )

            if state.force_status != 200:
                self._respond(state.force_status, {"error": f"Simulated HTTP {state.force_status}"})
                return

            if sub_key != state.expected_token:
                self._respond(401, {"error": "Invalid subscription key"})
                return

            if self.path == "/text-to-speech":
                inputs = body.get("inputs") or []
                if not inputs or not body.get("target_language_code"):
                    self._respond(400, {"error": "Missing inputs or target_language_code"})
                    return
                self._respond(200, {"audios": [wav_b64], "request_id": "mock-tts-001"})
            elif self.path == "/speech-to-text":
                lang = body.get("language_code", "en-IN")
                transcript = "Haudu approve win-back campaign" if lang == "kn-IN" else "Yes approve win-back campaign"
                self._respond(200, {"transcript": transcript, "language_code": lang})
            elif self.path == "/translate":
                self._respond(200, {"translated_text": f"[MOCK-TR] {body.get('input', '')}"})
            else:
                self._respond(404, {"error": "Unknown mock endpoint"})

        def _respond(self, code: int, payload: Dict[str, object]) -> None:
            encoded = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://{host}:{port}", state
    finally:
        server.shutdown()
        server.server_close()
