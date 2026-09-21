"""Local LLM access (Ollama). Future providers would implement the same two methods."""

from __future__ import annotations

import httpx


class OllamaClient:
    def __init__(self, url: str, model: str, timeout: float = 120.0) -> None:
        self.url = url.rstrip("/")
        self.model = model
        self.timeout = timeout

    @property
    def name(self) -> str:
        return f"ollama:{self.model}"

    def available(self) -> bool:
        try:
            tags = httpx.get(f"{self.url}/api/tags", timeout=1.0).json()
        except (httpx.HTTPError, ValueError):
            return False
        return any(m.get("name") == self.model for m in tags.get("models", []))

    def generate(self, prompt: str) -> str:
        response = httpx.post(
            f"{self.url}/api/chat",
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "think": False,  # qwen3: skip the reasoning trace, we only want the answer
                "options": {"temperature": 0.2, "num_predict": 300},
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()["message"]["content"].strip()
