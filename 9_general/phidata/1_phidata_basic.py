from phi.agent import Agent
from phi.model.openai import OpenAIChat
from dotenv import load_dotenv

load_dotenv(override=True)


agent = Agent(
    model=OpenAIChat(model="gpt-4o-mini"),
    instructions="Explain Kubernetes to a beginner"
)

agent.print_response("What is Kubernetes?")
