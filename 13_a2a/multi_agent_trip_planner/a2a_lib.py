"""Small shared JSON-RPC/A2A helpers used by the trip-planner demo.

Not a spec-complete A2A implementation (see the root 13_a2a/README.md) -
just enough plumbing (agent card serving, task/artifact shapes, a JSON-RPC
dispatcher, and an HTTP client) so three separate agent processes can talk
to each other without each file re-implementing it.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.error import URLError
from urllib.request import Request, urlopen

PROTOCOL_VERSION = "1.0"

SkillHandler = Callable[[dict[str, Any]], tuple[str, list[dict[str, Any]]]]


class SkillError(Exception):
    """Raised by a skill handler for an expected, user-facing failure."""


class RemoteAgentError(Exception):
    """Raised when a downstream A2A call fails or the remote agent errors."""


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def text_part(text: str) -> dict[str, Any]:
    return {"text": text, "mediaType": "text/plain"}


def data_part(data: dict[str, Any]) -> dict[str, Any]:
    return {"data": data, "mediaType": "application/json"}


def text_parts(message: dict[str, Any]) -> str:
    texts = [p.get("text", "") for p in message.get("parts", []) if isinstance(p, dict) and "text" in p]
    return " ".join(t for t in texts if t).strip()


def data_parts(message: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for part in message.get("parts", []):
        if isinstance(part, dict) and isinstance(part.get("data"), dict):
            merged.update(part["data"])
    return merged


def make_artifact(name: str, *, text: str | None = None, data: dict[str, Any] | None = None) -> dict[str, Any]:
    parts = []
    if text is not None:
        parts.append(text_part(text))
    if data is not None:
        parts.append(data_part(data))
    return {"artifactId": str(uuid.uuid4()), "name": name, "parts": parts}


class TaskStore:
    """In-memory task store so a client can poll `tasks/get` after the fact."""

    def __init__(self) -> None:
        self._tasks: dict[str, dict[str, Any]] = {}

    def save(self, task: dict[str, Any]) -> None:
        self._tasks[task["id"]] = task

    def get(self, task_id: str) -> dict[str, Any] | None:
        return self._tasks.get(task_id)


def make_task(message: dict[str, Any], artifacts: list[dict[str, Any]], agent_reply_text: str) -> dict[str, Any]:
    task_id = str(uuid.uuid4())
    context_id = message.get("contextId") or str(uuid.uuid4())
    message_id = message.get("messageId") or str(uuid.uuid4())

    user_message = {
        "messageId": message_id,
        "contextId": context_id,
        "taskId": task_id,
        "role": message.get("role", "ROLE_USER"),
        "parts": message.get("parts", []),
    }
    status_message = {
        "messageId": str(uuid.uuid4()),
        "contextId": context_id,
        "taskId": task_id,
        "role": "ROLE_AGENT",
        "parts": [text_part(agent_reply_text)],
    }
    return {
        "id": task_id,
        "contextId": context_id,
        "status": {"state": "TASK_STATE_COMPLETED", "message": status_message, "timestamp": now()},
        "artifacts": artifacts,
        "history": [user_message, status_message],
    }


def json_rpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def json_rpc_result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


class A2ARequestHandler(BaseHTTPRequestHandler):
    server_version = "A2ADemo/0.2"

    def do_GET(self) -> None:
        if self.path == "/.well-known/agent-card.json":
            self.send_json(self.server.agent_card_fn())
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

        method = request.get("method")
        params = request.get("params", {})
        if method == "SendMessage":
            self.handle_send_message(request_id, params)
        elif method == "tasks/get":
            self.handle_get_task(request_id, params)
        else:
            self.send_json(json_rpc_error(request_id, -32601, "Method not found"))

    def handle_send_message(self, request_id: Any, params: dict[str, Any]) -> None:
        message = params.get("message")
        if not isinstance(message, dict) or not message.get("parts"):
            self.send_json(json_rpc_error(request_id, -32602, "params.message.parts is required"))
            return

        skills: dict[str, SkillHandler] = self.server.skill_handlers
        skill_id = message.get("skillId")
        if skill_id:
            handler = skills.get(skill_id)
            if handler is None:
                self.send_json(json_rpc_error(request_id, -32602, f"Unknown skill '{skill_id}'"))
                return
        elif len(skills) == 1:
            handler = next(iter(skills.values()))
        else:
            self.send_json(json_rpc_error(request_id, -32602, "message.skillId is required (agent exposes multiple skills)"))
            return

        try:
            reply_text, artifacts = handler(message)
        except SkillError as exc:
            self.send_json(json_rpc_error(request_id, -32000, str(exc)))
            return
        except Exception as exc:  # keep the connection alive even on unexpected failures (e.g. an LLM call erroring)
            self.send_json(json_rpc_error(request_id, -32001, f"skill handler failed: {exc}"))
            return

        task = make_task(message, artifacts, reply_text)
        self.server.task_store.save(task)
        self.send_json(json_rpc_result(request_id, {"task": task}))

    def handle_get_task(self, request_id: Any, params: dict[str, Any]) -> None:
        task = self.server.task_store.get(params.get("id", ""))
        if task is None:
            self.send_json(json_rpc_error(request_id, -32001, f"Unknown task '{params.get('id')}'"))
            return
        self.send_json(json_rpc_result(request_id, {"task": task}))

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


class A2AServer(ThreadingHTTPServer):
    """A ThreadingHTTPServer pre-wired with an agent card and skill handlers."""

    def __init__(self, address: tuple[str, int], agent_card_fn: Callable[[], dict[str, Any]], skill_handlers: dict[str, SkillHandler]):
        super().__init__(address, A2ARequestHandler)
        self.agent_card_fn = agent_card_fn
        self.skill_handlers = skill_handlers
        self.task_store = TaskStore()


def get_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={"Accept": "application/a2a+json", "A2A-Version": PROTOCOL_VERSION})
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/a2a+json",
            "A2A-Version": PROTOCOL_VERSION,
        },
    )
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_agent_card(base_url: str) -> dict[str, Any]:
    return get_json(f"{base_url}/.well-known/agent-card.json")


def call_remote_skill(
    rpc_url: str,
    skill_id: str,
    data: dict[str, Any],
    *,
    context_id: str | None = None,
    text: str = "",
) -> dict[str, Any]:
    """Send a SendMessage task to a remote agent and return its completed task."""
    message: dict[str, Any] = {
        "messageId": str(uuid.uuid4()),
        "role": "ROLE_USER",
        "skillId": skill_id,
        "parts": ([text_part(text)] if text else []) + [data_part(data)],
    }
    if context_id:
        message["contextId"] = context_id

    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "SendMessage",
        "params": {"message": message},
    }
    try:
        response = post_json(rpc_url, payload)
    except (URLError, OSError) as exc:
        raise RemoteAgentError(f"could not reach {rpc_url} ({exc})") from exc

    if "error" in response:
        raise RemoteAgentError(response["error"].get("message", "remote agent returned an error"))
    return response["result"]["task"]
