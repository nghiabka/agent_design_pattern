"""HTTP client used by the Streamlit frontend."""

from __future__ import annotations

from typing import Any

import requests


class BackendClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def get(self, path: str, timeout: int = 10) -> dict[str, Any] | None:
        try:
            response = requests.get(f"{self.base_url}{path}", timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return None

    def chat(self, question: str, session_id: str, timeout: int = 300) -> dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/chat",
            json={"question": question, "session_id": session_id},
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()
