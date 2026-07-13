from __future__ import annotations

import json
import uuid
from urllib.request import Request, urlopen


BASE_URL = "http://127.0.0.1:9999"


def get_json(url: str) -> dict:
    request = Request(url, headers={"Accept": "application/a2a+json", "A2A-Version": "1.0"})
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(url: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/a2a+json",
            "A2A-Version": "1.0",
        },
    )
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    card = get_json(f"{BASE_URL}/.well-known/agent-card.json")
    rpc_url = card["supportedInterfaces"][0]["url"]
    print(f"Discovered agent: {card['name']}")
    print(f"RPC endpoint: {rpc_url}")

    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "SendMessage",
        "params": {
            "message": {
                "messageId": str(uuid.uuid4()),
                "role": "ROLE_USER",
                "parts": [{"text": "Hello from a tiny A2A client.", "mediaType": "text/plain"}],
            }
        },
    }

    response = post_json(rpc_url, payload)
    print(json.dumps(response, indent=2))


if __name__ == "__main__":
    main()
