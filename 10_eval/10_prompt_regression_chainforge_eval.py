"""
Prompt regression testing using ChainForge as the eval runner.

Idea: before shipping a change to a prompt, run the OLD and NEW prompt
variants over the same set of test cases, then send each NEW response
(with the OLD response attached as metadata) to ChainForge's
/app/executepy endpoint to score whether the new variant still meets a
basic quality bar (here: non-empty, under a word-count budget).

ChainForge is expected to already be running locally (chainforge serve,
default port 8000) -- this script only calls its REST API, it never
starts or stops the ChainForge process itself.
"""

from openai import OpenAI
from dotenv import load_dotenv
import requests

load_dotenv(override=True)

client = OpenAI()
CHAINFORGE_URL = "http://localhost:8000"

OLD_PROMPT = "Summarize this in one sentence: {text}"
NEW_PROMPT = "Summarize this in exactly one sentence, no more than 20 words: {text}"

TEST_CASES = [
    "The bank's mobile app now supports biometric login and instant card freezing.",
    "Customers can dispute a transaction directly from the transaction history screen.",
]

# Evaluator code sent to ChainForge to check the new prompt variant's
# response is non-empty and within the word-count budget.
REGRESSION_EVAL_CODE = """
def evaluate(response):
    new_text = response.text
    word_count = len(new_text.split())
    length_ok = word_count <= 25
    not_empty = len(new_text.strip()) > 0
    return bool(length_ok and not_empty)
"""

def ask(prompt_template: str, text: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt_template.format(text=text)}],
    )
    return resp.choices[0].message.content.strip()

def chainforge_regression_check(new_text: str, old_text: str, text: str):
    payload = {
        "id": "prompt_regression",
        "code": REGRESSION_EVAL_CODE,
        "responses": [{
            "responses": [new_text],
            "prompt": NEW_PROMPT,
            "vars": {"text": text},
            "metavars": {"old_response": old_text},
            "llm": "gpt-4o-mini",
        }],
        "scope": "response",
        "process_type": "evaluator",
    }

    try:
        resp = requests.post(f"{CHAINFORGE_URL}/app/executepy", json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[ChainForge] eval unreachable, skipping: {e}")
        return None

    if data.get("error"):
        print(f"[ChainForge] eval failed: {data['error']}")
        return None

    return data["responses"][0]["eval_res"]["items"][0]

if __name__ == "__main__":
    print(f"Running prompt regression test via ChainForge at {CHAINFORGE_URL}\n")

    for text in TEST_CASES:
        old_out = ask(OLD_PROMPT, text)
        new_out = ask(NEW_PROMPT, text)
        passed = chainforge_regression_check(new_out, old_out, text)

        print(f"Input: {text}")
        print(f"  OLD: {old_out}")
        print(f"  NEW: {new_out}")
        print(f"  Regression check passed: {passed}\n")
