"""LLM Service Integration Module

Connects to local LLM services (Ollama, vLLM, etc.)
via OpenAI-compatible API endpoints.
"""

import requests
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

from src.config import config
from src.logger import get_logger

logger = get_logger(__name__)


class LLMClient:
    """Client for local LLM services with OpenAI-compatible API"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 120,
    ):
        """Initialize LLM client

        Args:
            base_url: LLM API base URL (e.g., http://localhost:8000/v1)
            api_key: API key for authentication
            model: Model name (e.g., qwen2, llama2)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or config.LLM_BASE_URL
        self.api_key = api_key or config.LLM_API_KEY
        self.model = model or config.LLM_MODEL
        self.timeout = timeout
        self.max_tokens = config.LLM_MAX_TOKENS

        logger.info(
            f"LLMClient initialized: {self.base_url}, model={self.model}"
        )

    def _request(
        self,
        endpoint: str,
        method: str = "POST",
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request to LLM API

        Args:
            endpoint: API endpoint path
            method: HTTP method
            data: Request payload

        Returns:
            Response JSON

        Raises:
            requests.RequestException: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            if method == "POST":
                response = requests.post(
                    url, json=data, headers=headers, timeout=self.timeout
                )
            elif method == "GET":
                response = requests.get(
                    url, headers=headers, timeout=self.timeout
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            logger.error(f"LLM request timeout: {url}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"LLM request failed: {e}")
            raise

    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> str:
        """Generate text using LLM

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-1)
            top_p: Nucleus sampling parameter

        Returns:
            Generated text
        """
        max_tokens = max_tokens or self.max_tokens

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
        }

        try:
            response = self._request("/chat/completions", data=payload)
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            logger.error(f"Unexpected LLM response format: {e}")
            raise

    def generate_stream(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
    ):
        """Generate text with streaming response

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Yields:
            Generated text chunks
        """
        max_tokens = max_tokens or self.max_tokens

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }

        try:
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }

            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
                stream=True,
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            delta = data["choices"][0]["delta"]
                            if "content" in delta:
                                yield delta["content"]
                        except (json.JSONDecodeError, KeyError):
                            continue

        except requests.exceptions.RequestException as e:
            logger.error(f"Stream generation failed: {e}")
            raise

    def list_models(self) -> List[str]:
        """List available models

        Returns:
            List of model names
        """
        try:
            response = self._request("/models", method="GET")
            return [model["id"] for model in response["data"]]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    def health_check(self) -> bool:
        """Check if LLM service is healthy

        Returns:
            True if service is reachable, False otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/models",
                timeout=5,
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"LLM health check failed: {e}")
            return False
