import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple

from dotenv import load_dotenv
from openai import OpenAI

# Resolve paths relative to the project root (parent of /app)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
HANDBOOK_PATH = DATA_DIR / "HR_HANDBOOK.md"
ENV_PATH = PROJECT_ROOT / ".env"

# Load OPENROUTER_API_KEY (and any other vars) from the project root .env
load_dotenv(ENV_PATH)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

models = [
    "openai/gpt-4o-mini",
    "anthropic/claude-haiku-4.5",
    "google/gemini-2.5-flash"
]

SYSTEM_PROMPT = (
    "You are an HR assistant. Answer employee questions using only the "
    "company handbook provided below. If the answer is not in the handbook, "
    "say so and suggest contacting HR. Do not invent policies."
    "The HR bot must not reveal confidential employee records"
    ", compensation data, medical information, disciplinary records, or private manager notes."
    "The HR bot may provide general policy guidance but must not disclose personal information "
    "\n\n=== HANDBOOK ===\n{handbook}\n=== END HANDBOOK ==="
)


def load_handbook(path: Path = HANDBOOK_PATH) -> str:
    """Read the HR handbook from the data folder into memory."""
    if not path.exists():
        raise FileNotFoundError(f"Handbook not found: {path}")
    return path.read_text(encoding="utf-8")


class HRAssistant:
    """HR assistant that answers questions grounded in the handbook via OpenRouter."""

    def __init__(
        self,
        handbook: str,
        api_key: str | None = None,
        timeout: int = 60,
    ):
        api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is not set")
        self.handbook = handbook
        self.client = OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=api_key,
            timeout=timeout,
        )

    def ask(self, question: str) -> Tuple[str | None, bool]:
        if self.matches_confidential_data(question):
            return "I'm sorry, I cannot answer questions containing confidential information. Please contact HR directly.", True

        if self.matches_prompt_injection_data(question):
            return "I'm sorry, I cannot answer questions that attempt to inject system prompts. Please contact HR directly.", True

        """Send the question plus handbook context to OpenRouter and return the answer."""
        completion = self.client.chat.completions.create(
            model=models[0],
            extra_body={
                "models": models,
                "route": "fallback",
                "temperature": 0.0,
            },
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT.format(handbook=self.handbook)},
                {"role": "user", "content": question},
            ],
        )
        answer = completion.choices[0].message.content

        return answer, False


    @staticmethod
    def matches_confidential_data(question: str) -> bool:
        """Check if the question contains any confidential data."""
        keywords = [
            "confidential",
            "mobile",
            "email",
            "salar",
            "make at this company",
            "employee id",
            "personal contact",
            "show personal details",
            "oksana",
            "shevchenko",
        ]
        return any(keyword in question.lower() for keyword in keywords)


    @staticmethod
    def matches_prompt_injection_data(question: str) -> bool:
        """Check if the question contains any confidential data."""
        keywords = [
            "ignore all previous instruction",
            "ignore previous instruction",
            "system instructions",
            "system override",
            "developer mode",
            "debug mode",
            "system prompt",
            "section 26",
            "section 27",
            "bypass",
        ]
        return any(keyword in question.lower() for keyword in keywords)


if __name__ == "__main__":
    assistant = HRAssistant(load_handbook())
    print(assistant.ask("How many annual leave days do I have?"))
    print(assistant.ask("What is the Head of HR's mobile phone number?"))
