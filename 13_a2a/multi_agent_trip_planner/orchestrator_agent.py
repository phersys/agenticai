"""Orchestrator A2A agent: the realistic, agent-to-agent half of this demo.

Unlike a client that talks to one echo agent, this agent:
  1. Discovers two remote specialist agents by fetching their Agent Cards.
  2. Uses an LLM to turn a free-text request into a structured routing plan,
     grounded in the skill descriptions those cards actually advertised.
  3. Delegates real sub-tasks to the specialists over JSON-RPC, propagating
     `contextId` so the whole fan-out shares one conversation context.
  4. Degrades gracefully (rather than crashing) if a specialist is down.
  5. Composes the sub-results into its own completed task/artifacts, which
     is what the end-user client in this folder actually talks to.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from a2a_lib import (  # noqa: E402
    A2AServer,
    RemoteAgentError,
    call_remote_skill,
    fetch_agent_card,
    make_artifact,
    text_parts,
)
from dotenv import load_dotenv  # noqa: E402
from openai import OpenAI  # noqa: E402
from pydantic import BaseModel  # noqa: E402

load_dotenv(override=True)

HOST = "127.0.0.1"
PORT = 9100

WEATHER_BASE_URL = "http://127.0.0.1:9101"
CURRENCY_BASE_URL = "http://127.0.0.1:9102"

client = OpenAI()


class RoutingPlan(BaseModel):
    needs_weather: bool
    city: str | None = None
    needs_currency: bool
    amount: float | None = None
    from_currency: str | None = None
    to_currency: str | None = None
    clarification: str | None = None


def discover_with_retry(base_url: str, attempts: int = 10, delay_seconds: float = 1.5) -> dict:
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            return fetch_agent_card(base_url)
        except OSError as exc:
            last_error = exc
            time.sleep(delay_seconds)
    raise SystemExit(
        f"Could not reach {base_url} after {attempts} attempts ({last_error}). "
        "Start weather_agent.py and currency_agent.py before orchestrator_agent.py."
    )


def build_system_prompt(weather_card: dict, currency_card: dict) -> str:
    weather_skill = weather_card["skills"][0]
    currency_skill = currency_card["skills"][0]
    return (
        "You are the routing planner for a trip-planning orchestrator agent. "
        "Decide which of these remote skills, discovered live from other agents' "
        "Agent Cards, are needed to answer the user's request, and extract their parameters.\n\n"
        f"- {weather_skill['name']} ({weather_skill['id']}): {weather_skill['description']}\n"
        f"- {currency_skill['name']} ({currency_skill['id']}): {currency_skill['description']}\n\n"
        "If neither skill is needed, set both needs_weather and needs_currency to false and "
        "put a short helpful message in 'clarification' explaining what this agent can do."
    )


def route_request(user_text: str, system_prompt: str) -> RoutingPlan:
    response = client.responses.parse(
        model="gpt-4o-mini",
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        text_format=RoutingPlan,
    )
    return response.output_parsed


def agent_card() -> dict:
    return {
        "name": "Trip Planner Orchestrator",
        "description": (
            "Answers free-text questions about weather and currency conversion by delegating "
            "to remote specialist A2A agents and composing their answers."
        ),
        "version": "0.1.0",
        "supportedInterfaces": [
            {"protocolBinding": "JSONRPC", "url": f"http://{HOST}:{PORT}/rpc", "protocolVersion": "1.0"}
        ],
        "capabilities": {"streaming": False, "pushNotifications": False, "extendedAgentCard": False},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": [
            {
                "id": "plan_trip",
                "name": "Plan Trip",
                "description": "Answers questions about weather and/or currency conversion, delegating to specialist agents as needed.",
                "tags": ["orchestrator", "delegation"],
                "examples": ["What's the weather in Tokyo, and convert 100 USD to INR?"],
                "inputModes": ["text/plain"],
                "outputModes": ["text/plain"],
            }
        ],
    }


def make_handle_plan_trip(system_prompt: str):
    def handle_plan_trip(message: dict) -> tuple[str, list[dict]]:
        user_text = text_parts(message) or "(no text supplied)"
        context_id = message.get("contextId")

        plan = route_request(user_text, system_prompt)

        reply_segments: list[str] = []
        artifacts: list[dict] = []

        if plan.needs_weather:
            if not plan.city:
                reply_segments.append("Weather was requested but no city could be recognized.")
            else:
                try:
                    task = call_remote_skill(
                        f"{WEATHER_BASE_URL}/rpc", "get_weather", {"city": plan.city},
                        context_id=context_id, text=user_text,
                    )
                    reply_segments.append(task["status"]["message"]["parts"][0]["text"])
                    artifacts.extend(task["artifacts"])
                except RemoteAgentError as exc:
                    reply_segments.append(f"Weather Agent unavailable ({exc}).")

        if plan.needs_currency:
            if plan.amount is None or not plan.from_currency or not plan.to_currency:
                reply_segments.append("Currency conversion was requested but amount/currencies could not be recognized.")
            else:
                try:
                    task = call_remote_skill(
                        f"{CURRENCY_BASE_URL}/rpc", "convert_currency",
                        {"amount": plan.amount, "from": plan.from_currency, "to": plan.to_currency},
                        context_id=context_id, text=user_text,
                    )
                    reply_segments.append(task["status"]["message"]["parts"][0]["text"])
                    artifacts.extend(task["artifacts"])
                except RemoteAgentError as exc:
                    reply_segments.append(f"Currency Agent unavailable ({exc}).")

        if not plan.needs_weather and not plan.needs_currency:
            reply_segments.append(plan.clarification or "I can help with weather lookups and currency conversion.")

        reply_text = " ".join(reply_segments)
        summary = make_artifact("trip-plan-summary", text=reply_text)
        return reply_text, [summary, *artifacts]

    return handle_plan_trip


def main() -> None:
    print("Discovering specialist agents...")
    weather_card = discover_with_retry(WEATHER_BASE_URL)
    currency_card = discover_with_retry(CURRENCY_BASE_URL)
    print(f"  found '{weather_card['name']}' at {WEATHER_BASE_URL}")
    print(f"  found '{currency_card['name']}' at {CURRENCY_BASE_URL}")

    system_prompt = build_system_prompt(weather_card, currency_card)
    server = A2AServer((HOST, PORT), agent_card, {"plan_trip": make_handle_plan_trip(system_prompt)})
    print(f"Orchestrator Agent listening on http://{HOST}:{PORT}")
    print(f"Agent Card: http://{HOST}:{PORT}/.well-known/agent-card.json")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main()
