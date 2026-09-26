import json
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types

from app.schemas.models import (
    Goal,
    Action,
    StepGroup,
    Deeplink,
    ValidationDeepLink,
    actionCategory,
    ContextDeeplinkResponse,
)
from app.services.deeplink_search import get_deeplink_search


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY environment variable not set")

client = genai.Client(api_key=GEMINI_API_KEY)

MODEL_NAME = os.getenv("LLM_MODEL", "gemini-3.8-flash")

SAMPLE_OUTPUT = json.dumps(
    {
        "query": "The mobile phone screen is cracked and flashes intermittently.",
        "response": {
            "contexts": [
                {
                    "goal": "Follow these steps to perform this Screen Damage Troubleshooting",
                    "title": "Screen display damage",
                    "score": 0.95,
                    "actions": [
                        {
                            "actionName": "Back Up Phone Data",
                            "description": "It will facilitate secure data transfer between your devices",
                            "stepGroups": [
                                {
                                    "steps": [
                                        "Navigate to and open Settings.",
                                        "Tap on Accounts and backup.",
                                        "Select Back up data to secure your personal files.",
                                    ],
                                    "actionableDeeplink": {
                                        "deeplink": "voiceassist://masked/act/b3ed3ed663",
                                        "description": "Enables data backup to TechCorp Cloud via device Settings on the device.",
                                        "message": "Enable Back up data (TechCorp Cloud)",
                                        "originalType": "onURL",
                                    },
                                    "validationDeeplink": {
                                        "deeplink": "voiceassist://masked/val/266037d0c5",
                                        "key": "Back up data (TechCorp Cloud)",
                                        "resultType": "boolean",
                                        "condition": "equal",
                                        "value": "True",
                                    },
                                }
                            ],
                            "category": "auto",
                        },
                        {
                            "actionName": "Schedule Screen Repair Service",
                            "description": "It will help you locate the nearest TechCorp service center and schedule",
                            "stepGroups": [
                                {
                                    "steps": [
                                        "Contact Customer Support or visit an authorized TechCorp Service Center.",
                                        "Provide device details regarding the peeling film and green display lines to initiate service.",
                                    ],
                                    "actionableDeeplink": None,
                                    "validationDeeplink": None,
                                }
                            ],
                            "category": "manual",
                        },
                    ],
                }
            ]
        },
    },
    indent=2,
)


def build_prompt(complaint: str, siis_response: str) -> str:
    return f"""You are a troubleshooting engine that converts raw user complaints and official SIIS responses into structured Goal objects.

Your task: Extract a structured Goal object from the complaint and SIIS response, following the schema exactly.

SCHEMA RULES:
1. Goal: goal (str), title (str, 2-3 words sentence case), score (float 0-1), actions (List[Action])
2. Action: actionName (Title Case), description (5-7 words, starts with "It will"), stepGroups (List[StepGroup]), category (auto|manual|critical)
3. StepGroup: steps (List[str]), actionableDeeplink (Deeplink|null), validationDeeplink (ValidationDeepLink|null)
4. Deeplink: deeplink (str), description (str), message (str), originalType (str)
5. ValidationDeepLink: deeplink (str), key (str), resultType (boolean|integer|str|float), condition (greater|equal|less), value (str)

FORMATTING REFERENCE (sample_output.json):
{SAMPLE_OUTPUT}

INSTRUCTIONS:
- Derive actions and steps ONLY from the SIIS response text. Do not invent steps.
- Title must be 2-3 words in sentence case (e.g., "Screen damage", "Blank display fix")
- Goal must start with "Follow these steps to perform this"
- actionName must be Title Case
- description must be 5-7 words starting with "It will"
- For each action, create 1 StepGroup with the sequential steps from the SIIS response
- Use deeplink_search to find matching deeplinks for actionableDeeplink and validationDeeplink
- If no matching deeplink found, set to null
- Set category: "auto" for settings/configuration steps, "manual" for physical/repair steps, "critical" for data backup/emergency steps
- Score: confidence 0.8-0.99 based on how well SIIS response addresses complaint

USER COMPLAINT:
{complaint}

SIIS RESPONSE:
{siis_response}

Return ONLY valid JSON matching the ContextDeeplinkResponse schema (with contexts array containing one Goal object). No markdown, no explanation, no code fences, no extra text. Output must start with {{ and end with }}."""


def find_deeplink_for_step(step_text: str, search) -> Optional[Deeplink]:
    results = search.search(step_text, limit=1, score_cutoff=50)
    return results[0] if results else None


def find_validation_deeplink_for_step(step_text: str, search) -> Optional[ValidationDeepLink]:
    results = search.search(step_text, limit=1, score_cutoff=50)
    if results:
        entry = search.get_validation_deeplink(results[0].deeplink.split("/")[-1])
        if entry:
            return entry
    return None


def extract_goal_from_text(complaint: str, siis_response_text: str) -> Goal:
    search = get_deeplink_search()

    prompt = build_prompt(complaint, siis_response_text)

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.1,
            candidate_count=1,
        ),
    )

    content = response.text
    print("=== RAW GEMINI RESPONSE ===")
    print(content)
    print("=== END RAW RESPONSE ===")

    if not content:
        raise ValueError("Empty response from LLM")

    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    parsed = json.loads(content)
    contexts = parsed.get("contexts") or parsed.get("response", {}).get("contexts", [])
    if not contexts:
        raise ValueError("No contexts in LLM response")

    goal_data = contexts[0]
    goal = Goal(**goal_data)

    for action in goal.actions:
        for step_group in action.stepGroups:
            if step_group.actionableDeeplink is None and step_group.steps:
                combined_steps = " ".join(step_group.steps[:3])
                deeplink = find_deeplink_for_step(combined_steps, search)
                if deeplink:
                    step_group.actionableDeeplink = deeplink

            if step_group.validationDeeplink is None and step_group.steps:
                combined_steps = " ".join(step_group.steps[:3])
                val_deeplink = find_validation_deeplink_for_step(combined_steps, search)
                if val_deeplink:
                    step_group.validationDeeplink = val_deeplink

    return goal


def extract_context_response(complaint: str, siis_response_text: str) -> ContextDeeplinkResponse:
    goal = extract_goal_from_text(complaint, siis_response_text)
    return ContextDeeplinkResponse(contexts=[goal])


if __name__ == "__main__":
    complaint = "My TechCorp A15G tablet screen flashes and then goes completely blank whenever I tap to open an email in Gmail, and after it works for a short time it goes blank again."
    siis_response = """Smartphone,Others Mobile,Mobile Accessories,Tablet Email server not responding on smartphone or tablet ( Smartphone,Others Mobile,Mobile Accessories,Tablet): # Troubleshooting Email Connection Issues on Your smartphone
If you're having trouble accessing your email on your smartphone, here are some steps you can take to resolve the issue.
## Step 1: Check Email Access on a PC
First, try accessing your email on a personal computer. This helps determine if the problem is with your phone's connection or your email account itself. If you can sign in and access your email on a PC, your phone might not be connected to Wi-Fi or mobile data.
## Step 2: Verify Your Phone's Internet Connection
Ensure your phone is connected to a stable Wi-Fi or mobile data network.
Swipe down from the top of your phone's screen to open the Quick settings panel.
Touch and hold the Wi-Fi icon to check your connection status.
Alternatively, go to Settings, tap Connections, and then tap Wi-Fi. To confirm your internet connection is working, try loading a webpage or performing a quick search.
## Step 3: Review Your Email Account Settings
Sometimes, changes made by your email provider on their server can cause connection problems. In such cases, you may need to remove and re-add your email account to your phone to apply the new configuration.
Before proceeding, make sure you have your email account's username and password readily available."""

    try:
        result = extract_context_response(complaint, siis_response)
        print(json.dumps(result.model_dump(), indent=2))
    except Exception as e:
        print(f"Error: {e}")