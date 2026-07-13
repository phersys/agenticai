from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


HOST = "127.0.0.1"
PORT = 9999
PROTOCOL_VERSION = "1.0"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def text_from_message(message: dict[str, Any]) -> str:
    parts = message.get("parts", [])
    texts = [part.get("text", "") for part in parts if isinstance(part, dict)]
    return " ".join(text for text in texts if text).strip()


def agent_card() -> dict[str, Any]:
    return {
        "name": "Tiny A2A Echo Agent",
        "description": "A minimal Agent2Agent v1.0 JSON-RPC example.",
        "version": "0.1.0",
        "supportedInterfaces": [
            {
                "protocolBinding": "JSONRPC",
                "url": f"http://{HOST}:{PORT}/rpc",
                "protocolVersion": PROTOCOL_VERSION,
            }
        ],
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "extendedAgentCard": False,
        },
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": [
            {
                "id": "echo",
                "name": "Echo",
                "description": "Acknowledges text messages and returns an artifact.",
                "tags": ["example", "echo"],
                "examples": ["hello", "Can you hear me?"],
                "inputModes": ["text/plain"],
                "outputModes": ["text/plain"],
            }
        ],
    }


def completed_task(message: dict[str, Any]) -> dict[str, Any]:
    task_id = str(uuid.uuid4())
    context_id = message.get("contextId") or str(uuid.uuid4())
    user_text = text_from_message(message) or "(no text supplied)"
    message_id = message.get("messageId") or str(uuid.uuid4())
    agent_message_id = str(uuid.uuid4())

    user_message = {
        "messageId": message_id,
        "contextId": context_id,
        "taskId": task_id,
        "role": message.get("role", "ROLE_USER"),
        "parts": message.get("parts", []),
    }

    status_message = {
        "messageId": agent_message_id,
        "contextId": context_id,
        "taskId": task_id,
        "role": "ROLE_AGENT",
        "parts": [{"text": "Request completed.", "mediaType": "text/plain"}],
    }

    return {
        "id": task_id,
        "contextId": context_id,
        "status": {
            "state": "TASK_STATE_COMPLETED",
            "message": status_message,
            "timestamp": now(),
        },
        "artifacts": [
            {
                "artifactId": str(uuid.uuid4()),
                "name": "echo-result",
                "parts": [
                    {
                        "text": f"Tiny A2A agent received: {user_text}",
                        "mediaType": "text/plain",
                    }
                ],
            }
        ],
        "history": [user_message, status_message],
    }


def json_rpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


class A2AHandler(BaseHTTPRequestHandler):
    server_version = "TinyA2A/0.1"

    def do_GET(self) -> None:
        if self.path == "/.well-known/agent-card.json":
            self.send_json(agent_card())
            return
        self.send_json({"error": "not found"}, status=404)

    def do_POST(self) -> None:
        if self.path != "/rpc":
            self.send_json({"error": "not found"}, status=404)
            return

        request = self.read_json()
        request_id = request.get("id")
        if request.get("jsonrpc") != "2.0":
            self.send_json(json_rpc_error(request_id, -32600, "Invalid JSON-RPC request"))
            return
        if request.get("method") != "SendMessage":
            self.send_json(json_rpc_error(request_id, -32601, "Method not found"))
            return

        message = request.get("params", {}).get("message")
        if not isinstance(message, dict) or not message.get("parts"):
            self.send_json(json_rpc_error(request_id, -32602, "params.message.parts is required"))
            return

        result = {"task": completed_task(message)}
        self.send_json({"jsonrpc": "2.0", "id": request_id, "result": result})

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length)
        try:
            return json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/a2a+json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("A2A-Version", PROTOCOL_VERSION)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), A2AHandler)
    print(f"Tiny A2A server listening on http://{HOST}:{PORT}")
    print(f"Agent Card: http://{HOST}:{PORT}/.well-known/agent-card.json")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main()
