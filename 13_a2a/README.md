# A2A v1.0 Examples

This folder has two examples, in increasing order of realism:

1. **This example (below)** — a tiny, dependency-free single client / single
   agent echo, for learning the protocol shape before using the official SDK.
2. **[multi_agent_trip_planner/](multi_agent_trip_planner/)** — three agent
   processes with real agent-to-agent delegation: an orchestrator discovers
   two specialist agents' Agent Cards, uses an LLM to route a free-text
   request between them, and composes their answers. See that folder's
   README for details.

## Tiny A2A v1.0 Example

This is a small, dependency-free Agent2Agent example for learning the protocol shape before using the official SDK.

It implements:

- `GET /.well-known/agent-card.json`
- `POST /rpc` with JSON-RPC `SendMessage`
- A completed `Task` response with one text artifact
- `A2A-Version: 1.0` headers

It does not implement streaming, push notifications, authentication, task persistence, or the full SDK surface.

## Run

Terminal 1:

```powershell
python .\13_a2a\server.py
```

Terminal 2:

```powershell
python .\13_a2a\client.py
```

You can also inspect the Agent Card in a browser:

```text
http://127.0.0.1:9999/.well-known/agent-card.json
```

## Why This Shape

A2A v1.0 separates discovery from interaction:

- Discovery uses an Agent Card.
- Interaction happens through a protocol binding, here JSON-RPC over HTTP.
- Client messages initiate tasks.
- Agent outputs are returned as task artifacts.

When you are ready for a production-ish version, switch to the official `a2a-sdk` and add streaming/auth as needed.
