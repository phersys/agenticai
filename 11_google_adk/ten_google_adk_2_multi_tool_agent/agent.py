import os
import requests
import ipinfo
from google.adk.agents import Agent
from dotenv import load_dotenv

load_dotenv()

IPINFO_TOKEN = os.getenv("IPINFO_TOKEN")

# -----------------------------
# Tool 1: Get public IP address
# -----------------------------
def get_public_ip() -> dict:
    try:
        ip = requests.get("https://api.ipify.org").text
        return {"status": "success", "ip": ip}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


# ----------------------------------------------
# Tool 2: Get FULL details from IPInfo (NOT lite)
# ----------------------------------------------
def get_location_from_ip(ip: str) -> dict:
    try:
        handler = ipinfo.getHandler(IPINFO_TOKEN)  # Full API
        details = handler.getDetails(ip)

        info = {
            "ip": ip,
            "asn": details.all.get("asn", None),
            "as_name": details.all.get("asn_name", None),
            "as_domain": details.all.get("asn_domain", None),
            "country_code": details.all.get("country", None),
            "country": details.all.get("country_name", None),
            "continent_code": details.all.get("continent", None),
            "continent": details.all.get("continent_name", None)
        }

        return {"status": "success", "location": info}

    except Exception as e:
        return {"status": "error", "error_message": str(e)}


# -----------------------------
# ADK Agent
# -----------------------------
root_agent = Agent(
    name="ip_location_agent",
    model="gemini-2.5-flash",
    description="Detects user's public IP and returns expanded IP information",
    instruction=(
        "If user types 'ip', first call get_public_ip, then call "
        "get_location_from_ip using the returned IP. "
        "For anything else, reply: 'This agent only supports ip lookup.'"
    ),
    tools=[get_public_ip, get_location_from_ip],
)
