"""
Provider is selected once, at import time, via CHAT_PROVIDER env var.
Every call site depends on the ChatProvider protocol, never on a concrete
implementation — this is the seam that keeps "swap to a free local model
for individual learners" or "self-host for a privacy-sensitive institution"
a config change instead of a rewrite.
"""
import os
from typing import Protocol
import httpx

SYSTEM_PROMPT = (
    "You are Bloch, the tutor character inside the Quanta Learn app for team IDIOTS' "
    "SIH 2026 build. Your voice rule is Socratic: ALWAYS ask a leading question first, "
    "then hint — NEVER dump the answer. Assume the learner is around class 8. "
    "Scope is strictly the 7-level curriculum: qubits & measurement, superposition, "
    "basic gates (H/X/Z), multi-qubit & CNOT, entanglement (the Bell state), Deutsch's "
    "algorithm, and the Final Boss. Use the course's own explanations passed as RAG context. "
    "If asked something outside the curriculum, redirect back to the course rather than "
    "answering as a general-purpose model. Never scold — a wrong prediction gets 'close, "
    "let's find the gap', never 'incorrect'."
)


class ChatProvider(Protocol):
    async def complete(self, message: str, rag_context: str) -> str: ...


class OpenAIProvider:
    def __init__(self):
        self.api_key = os.environ["OPENAI_API_KEY"]
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    async def complete(self, message: str, rag_context: str) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "system", "content": f"Relevant course material:\n{rag_context}"},
                        {"role": "user", "content": message},
                    ],
                },
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]


class OllamaProvider:
    """Free/local path — points at a self-hosted or Ollama-served open-weight model."""

    def __init__(self):
        self.base_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
        self.model = os.environ.get("OLLAMA_MODEL", "llama3.1")

    async def complete(self, message: str, rag_context: str) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "system", "content": f"Relevant course material:\n{rag_context}"},
                        {"role": "user", "content": message},
                    ],
                    "stream": False,
                },
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"]


def get_chat_provider() -> ChatProvider:
    provider = os.environ.get("CHAT_PROVIDER", "ollama")  # default to the free path
    if provider == "openai":
        return OpenAIProvider()
    if provider == "ollama":
        return OllamaProvider()
    raise ValueError(f"Unknown CHAT_PROVIDER: {provider}")
