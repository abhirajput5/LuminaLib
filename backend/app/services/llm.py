from __future__ import annotations

import json
import requests
import logging
from abc import ABC, abstractmethod
from typing import Dict, Type, List
from app.settings import settings

logger = logging.getLogger(__name__)


# ============================================================
# 🔹 BASE INTERFACE
# ============================================================


class LLMProvider(ABC):
    @abstractmethod
    def summarize(self, text: str) -> str:
        pass

    @abstractmethod
    def combine(self, summaries: List[str]) -> str:
        pass

    @abstractmethod
    def analyze_reviews(self, reviews: List[str]) -> tuple[str, float]:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if provider is reachable and usable.
        Should be lightweight.
        """
        pass


# ============================================================
# 🔹 OLLAMA PROVIDER
# ============================================================


class OllamaProvider(LLMProvider):
    def __init__(self) -> None:
        self.base_url: str = settings.ollama_api_base
        self.model: str = settings.ollama_model_name

    def _generate(self, prompt: str) -> str:
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            },
            timeout=1800,
        )
        response.raise_for_status()
        return response.json()["response"]

    def summarize(self, text: str) -> str:
        prompt = f"""
        You are a precise summarization engine.

        Summarize the following text into concise bullet points.
        Do not add extra information.

        TEXT:
        {text}
        """
        return self._generate(prompt)

    def combine(self, summaries: List[str]) -> str:
        summaries_str = "".join(summaries)
        prompt = f"""
        Combine the following summaries into a single coherent summary.
        Keep it concise and structured.

        SUMMARIES:
        {summaries_str}
        """
        return self._generate(prompt)

    def analyze_reviews(self, reviews: List[str]) -> tuple[str, float]:
        reviews_text = "".join(reviews)

        prompt = (
            prompt
        ) = f"""
        Summarize reviews and give score (0 to 1).

        Reviews:
        {reviews_text}

        Return JSON:
        {{"summary": "...", "score": 0.5}}
        """

        response = self._generate(prompt)

        logger.info(f"Analysis : {response}")

        try:
            data = json.loads(response)
            summary = data.get("summary", "")
            score = float(data.get("score", 0.0))
        except Exception:
            logger.warning(f"Failed to parse LLM response: {response}")
            summary = response
            score = 0.0

        return summary, score

    def is_available(self) -> bool:
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=3,
            )
            return response.status_code == 200
        except Exception:
            return False


# ============================================================
# 🔹 OPENAI PROVIDER
# ============================================================


class OpenAIProvider(LLMProvider):
    def __init__(self) -> None:
        self.api_key: str = settings.openai_api_key
        self.model: str = settings.openai_model_name
        self.base_url: str = settings.openai_api_base

    def _generate(self, prompt: str) -> str:
        response = requests.post(
            f"{self.base_url}/responses",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "input": prompt,
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["output"][0]["content"][0]["text"]

    def summarize(self, text: str) -> str:
        prompt = f"""
        You are a precise summarization engine.

        Summarize the following text into concise bullet points.
        Do not add extra information.

        TEXT:
        {text}
        """
        return self._generate(prompt)

    def combine(self, summaries: List[str]) -> str:
        joined_summaries = "".join(summaries)
        prompt = f"""
        Combine the following summaries into a single coherent summary.
        Keep it concise and structured.

        SUMMARIES:
        {joined_summaries}
        """
        return self._generate(prompt)

    def analyze_reviews(self, reviews: List[str]) -> tuple[str, float]:
        reviews_text = "\n".join(reviews)

        prompt = f"""
        You are a sentiment analysis engine.

        Analyze the following user reviews and:
        1. Provide a concise summary
        2. Provide a sentiment score between 0 and 1

        REVIEWS:
        {reviews_text}

        OUTPUT FORMAT:
        Summary: <text>
        Score: <float>
        """

        response = self._generate(prompt)

        logger.info(f"Analysis : {response}")

        summary = ""
        score = 0.0

        for line in response.splitlines():
            if line.lower().startswith("summary"):
                summary = line.split(":", 1)[-1].strip()
            elif line.lower().startswith("score"):
                try:
                    score = float(line.split(":", 1)[-1].strip())
                except Exception:
                    score = 0.0

        return summary, score

    def is_available(self) -> bool:
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                },
                timeout=3,
            )
            return response.status_code == 200
        except Exception:
            return False


# ============================================================
# 🔹 PROVIDER REGISTRY
# ============================================================

PROVIDER_REGISTRY: Dict[str, Type[LLMProvider]] = {
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
}


# ============================================================
# 🔹 FACTORY
# ============================================================


def get_llm_provider() -> LLMProvider:
    provider_name: str = settings.llm_provider

    provider_cls = PROVIDER_REGISTRY.get(provider_name)

    if not provider_cls:
        raise ValueError(f"Unsupported LLM provider: {provider_name}")

    provider: LLMProvider = provider_cls()

    # Health check (fail fast)
    if not provider.is_available():
        raise RuntimeError(
            f"LLM provider '{provider_name}' is not available or misconfigured"
        )

    return provider
