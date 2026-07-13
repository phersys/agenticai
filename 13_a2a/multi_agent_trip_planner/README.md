# Multi-Agent Trip Planner (a more realistic A2A example)

The example in `13_a2a/server.py` / `client.py` is a single client talking to
a single agent that always replies with a fixed echo. This example is closer
to how A2A gets used in practice: three separate agent processes, real
agent-to-agent delegation, and an LLM making the routing decisions.

## Agents

- **Weather Agent** (`weather_agent.py`, port 9101) — one skill, `get_weather`,
  returns mock temperature/conditions for a small set of cities.
- **Currency Agent** (`currency_agent.py`, port 9102) — one skill,
  `convert_currency`, converts an amount between currencies using mock fixed
  rates.
- **Trip Planner Orchestrator** (`orchestrator_agent.py`, port 9100) — the
  agent the end user actually talks to. On startup it fetches the other two
  agents' Agent Cards (real discovery, not hardcoded skill knowledge). On each
  request it calls OpenAI (`responses.parse` with a Pydantic `RoutingPlan`,
  same structured-output pattern as
  [1_openai_chat_requests/1_7_openai_responses_pydantic.py](../../1_openai_chat_requests/1_7_openai_responses_pydantic.py))
  to decide which specialist skills the request needs and to extract their
  parameters, then sends real `SendMessage` JSON-RPC calls to whichever
  specialists are needed, propagating `contextId` across the fan-out, and
  composes their replies into its own completed task.

`a2a_lib.py` is a small shared module (agent card serving, task/artifact
shapes, JSON-RPC dispatch, HTTP client helpers) so the three agent processes
don't each reimplement the same plumbing.

## What makes this more realistic than the top-level example

- **Actual agent-to-agent calls**, not just client-to-agent: the orchestrator
  is both an A2A server (to the end user) and an A2A client (to the
  specialists).
- **Skill discovery drives the LLM prompt** — the orchestrator's routing
  prompt is built from the specialists' live Agent Card skill descriptions,
  not hardcoded.
- **Structured data parts**, not just text: sub-task messages carry a
  `{"data": {...}}` part (e.g. `{"city": "Tokyo"}`), closer to how a real
  skill would want typed input instead of parsing free text again downstream.
- **`contextId` propagation** ties the orchestrator's task and both delegated
  sub-tasks to one shared conversation context.
- **`tasks/get` polling** — completed tasks are kept in an in-memory
  `TaskStore` so a client can look one up by id after the fact, not just read
  the synchronous response.
- **Graceful degradation** — if a specialist agent is unreachable or rejects
  the request (e.g. an unsupported city or currency), the orchestrator embeds
  a clear message about that instead of the whole request failing.

## Run it

Needs `OPENAI_API_KEY` set in the repo root `.env` (same as every other
OpenAI-backed script here). Start each process in its own terminal, in order:

```powershell
python .\13_a2a\multi_agent_trip_planner\weather_agent.py
python .\13_a2a\multi_agent_trip_planner\currency_agent.py
python .\13_a2a\multi_agent_trip_planner\orchestrator_agent.py
python .\13_a2a\multi_agent_trip_planner\client.py
```

You can also inspect any agent's card directly in a browser, e.g.
`http://127.0.0.1:9100/.well-known/agent-card.json`.

Try editing the request text in `client.py` — e.g. asking only about weather,
only about currency, an unsupported city, or something unrelated — to see the
orchestrator's routing plan and its graceful-degradation paths change.
