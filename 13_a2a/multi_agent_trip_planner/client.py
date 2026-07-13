"""End-user client: talks only to the orchestrator.

It never sees the Weather or Currency agents directly - all the real
agent-to-agent delegation happens inside orchestrator_agent.py. Run this
last, after weather_agent.py, currency_agent.py, and orchestrator_agent.py
are all up.
"""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from a2a_lib import fetch_agent_card, post_json, text_part  # noqa: E402

BASE_URL = "http://127.0.0.1:9100"


def main() -> None:
    card = fetch_agent_card(BASE_URL)
    rpc_url = card["supportedInterfaces"][0]["url"]
    print(f"Discovered agent: {card['name']} — {card['description']}")

    user_text = "What's the weather in Tokyo, and convert 100 USD to INR?"
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "SendMessage",
        "params": {
            "message": {
                "messageId": str(uuid.uuid4()),
                "role": "ROLE_USER",
                "parts": [text_part(user_text)],
            }
        },
    }

    print(f"\nSending: {user_text!r}")
    response = post_json(rpc_url, payload)
    print(json.dumps(response, indent=2))

    task_id = response["result"]["task"]["id"]
    poll_payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "tasks/get",
        "params": {"id": task_id},
    }
    print(f"\nPolling task {task_id} via tasks/get:")
    print(json.dumps(post_json(rpc_url, poll_payload), indent=2))


if __name__ == "__main__":
    main()
