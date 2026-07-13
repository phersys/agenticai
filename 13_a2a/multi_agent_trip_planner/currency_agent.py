"""Specialist A2A agent exposing one skill: mock currency conversion."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from a2a_lib import A2AServer, SkillError, data_parts, make_artifact  # noqa: E402

HOST = "127.0.0.1"
PORT = 9102

# Mock, fixed exchange rates expressed as "1 unit of this currency = N USD".
MOCK_RATES_TO_USD = {
    "usd": 1.0,
    "inr": 1 / 83.0,
    "eur": 1.08,
    "gbp": 1.27,
    "jpy": 1 / 155.0,
}


def agent_card() -> dict:
    return {
        "name": "Currency Agent",
        "description": "Converts an amount between currencies using mock, fixed exchange rates.",
        "version": "0.1.0",
        "supportedInterfaces": [
            {"protocolBinding": "JSONRPC", "url": f"http://{HOST}:{PORT}/rpc", "protocolVersion": "1.0"}
        ],
        "capabilities": {"streaming": False, "pushNotifications": False, "extendedAgentCard": False},
        "defaultInputModes": ["application/json"],
        "defaultOutputModes": ["text/plain"],
        "skills": [
            {
                "id": "convert_currency",
                "name": "Convert Currency",
                "description": (
                    "Converts an amount from one currency to another using mock exchange rates. "
                    "Expects a data part shaped like {\"amount\": 100, \"from\": \"USD\", \"to\": \"INR\"}. "
                    f"Known currencies: {', '.join(c.upper() for c in sorted(MOCK_RATES_TO_USD))}."
                ),
                "tags": ["currency", "finance"],
                "examples": ["Convert 100 USD to INR."],
                "inputModes": ["application/json"],
                "outputModes": ["text/plain"],
            }
        ],
    }


def handle_convert_currency(message: dict) -> tuple[str, list[dict]]:
    payload = data_parts(message)

    try:
        amount = float(payload.get("amount"))
    except (TypeError, ValueError):
        raise SkillError("data part must include a numeric 'amount' field")

    from_ccy = str(payload.get("from", "")).strip().lower()
    to_ccy = str(payload.get("to", "")).strip().lower()
    if from_ccy not in MOCK_RATES_TO_USD or to_ccy not in MOCK_RATES_TO_USD:
        known = ", ".join(c.upper() for c in sorted(MOCK_RATES_TO_USD))
        raise SkillError(f"unsupported currency pair '{from_ccy.upper()}->{to_ccy.upper()}'. Known currencies: {known}")

    usd_amount = amount * MOCK_RATES_TO_USD[from_ccy]
    converted = usd_amount / MOCK_RATES_TO_USD[to_ccy]
    reply = f"{amount:.2f} {from_ccy.upper()} = {converted:.2f} {to_ccy.upper()} (mock rate)."
    artifact = make_artifact(
        "currency-result",
        text=reply,
        data={"amount": amount, "from": from_ccy, "to": to_ccy, "converted": round(converted, 2)},
    )
    return reply, [artifact]


def main() -> None:
    server = A2AServer((HOST, PORT), agent_card, {"convert_currency": handle_convert_currency})
    print(f"Currency Agent listening on http://{HOST}:{PORT}")
    print(f"Agent Card: http://{HOST}:{PORT}/.well-known/agent-card.json")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main()
