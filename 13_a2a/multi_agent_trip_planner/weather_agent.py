"""Specialist A2A agent exposing one skill: mock weather lookup by city."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from a2a_lib import A2AServer, SkillError, data_parts, make_artifact  # noqa: E402

HOST = "127.0.0.1"
PORT = 9101

# Same style of mock lookup table as demo/our_first_agent.py's get_temperature.
MOCK_WEATHER = {
    "new york": ("72°F", "sunny"),
    "london": ("65°F", "cloudy"),
    "tokyo": ("78°F", "humid"),
    "sydney": ("68°F", "clear"),
    "mumbai": ("85°F", "hazy"),
}


def agent_card() -> dict:
    return {
        "name": "Weather Agent",
        "description": "Reports mock current weather for a small set of cities.",
        "version": "0.1.0",
        "supportedInterfaces": [
            {"protocolBinding": "JSONRPC", "url": f"http://{HOST}:{PORT}/rpc", "protocolVersion": "1.0"}
        ],
        "capabilities": {"streaming": False, "pushNotifications": False, "extendedAgentCard": False},
        "defaultInputModes": ["application/json"],
        "defaultOutputModes": ["text/plain"],
        "skills": [
            {
                "id": "get_weather",
                "name": "Get Weather",
                "description": (
                    "Returns mock temperature and conditions for a city. "
                    "Expects a data part shaped like {\"city\": \"<city name>\"}. "
                    f"Known cities: {', '.join(sorted(MOCK_WEATHER))}."
                ),
                "tags": ["weather"],
                "examples": ["What's the weather in Tokyo?"],
                "inputModes": ["application/json"],
                "outputModes": ["text/plain"],
            }
        ],
    }


def handle_get_weather(message: dict) -> tuple[str, list[dict]]:
    payload = data_parts(message)
    city = str(payload.get("city", "")).strip().lower()
    if not city:
        raise SkillError("data part must include a 'city' field")
    if city not in MOCK_WEATHER:
        raise SkillError(f"no weather data for '{city}'. Known cities: {', '.join(sorted(MOCK_WEATHER))}")

    temperature, conditions = MOCK_WEATHER[city]
    reply = f"{city.title()}: {temperature}, {conditions}."
    artifact = make_artifact(
        "weather-result",
        text=reply,
        data={"city": city, "temperature": temperature, "conditions": conditions},
    )
    return reply, [artifact]


def main() -> None:
    server = A2AServer((HOST, PORT), agent_card, {"get_weather": handle_get_weather})
    print(f"Weather Agent listening on http://{HOST}:{PORT}")
    print(f"Agent Card: http://{HOST}:{PORT}/.well-known/agent-card.json")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main()
