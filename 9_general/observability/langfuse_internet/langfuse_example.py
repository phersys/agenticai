# pip install openai-agents nest_asyncio "pydantic-ai[logfire]" langfuse datasets
import os
import base64
from dotenv import load_dotenv

load_dotenv(override=True)
 
langfuse_public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
langfuse_secret_key = os.getenv("LANGFUSE_SECRET_KEY")
langfuse_base_url = os.getenv("LANGFUSE_BASE_URL")
 
# Build Basic Auth header
LANGFUSE_AUTH = base64.b64encode(
    f"{langfuse_public_key}:{langfuse_secret_key}".encode()
).decode()
 
# Configure OpenTelemetry endpoint & headers
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = langfuse_base_url + "/api/public/otel"
os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {LANGFUSE_AUTH}"
 
# Openai key
openai_api_key = os.environ["OPENAI_API_KEY"]

# Initialize the langfuse client
from langfuse import get_client
 
langfuse = get_client()
 
# Verify connection
if langfuse.auth_check():
    print("Langfuse client is authenticated and ready!")
else:
    print("Authentication failed. Please check your credentials and host.")

import nest_asyncio
nest_asyncio.apply()

# Pydantic Logfire offers an instrumentation for the OpenAi 
# Agent SDK
# We use this to send traces to the Langfuse OpenTelemetry Backend

import logfire
 
# Configure logfire instrumentation.
logfire.configure(
    service_name='my_agent_service',
 
    send_to_logfire=False,
)
# This method automatically patches the OpenAI Agents SDK to send logs via OTLP to Langfuse.
logfire.instrument_openai_agents()

# A simple Q&A agent to test langfuse
import asyncio
from agents import Agent, Runner
 
async def main():
    agent = Agent(
        name="Assistant",
        instructions="You are a senior software engineer",
    )
 
    result = await Runner.run(agent, "Tell me why it is important to evaluate AI agents.")
    print(result.final_output)
 
# replace the last part ONLY

if __name__ == "__main__":
    asyncio.run(main())
    langfuse.flush()


