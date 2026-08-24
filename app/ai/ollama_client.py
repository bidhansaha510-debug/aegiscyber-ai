from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator

import aiohttp

from app.config import get_config
from app.logging_config import get_logger

logger = get_logger("ai.ollama_client")


class OllamaClient:
    def __init__(self, host: str | None = None, model: str | None = None) -> None:
        config = get_config()
        self._host = host or config.ollama.host
        self._model = model or config.ollama.model
        self._timeout = aiohttp.ClientTimeout(total=config.ollama.timeout)
        self._session: aiohttp.ClientSession | None = None

    @property
    def model(self) -> str:
        return self._model

    @model.setter
    def model(self, value: str) -> None:
        self._model = value

    @property
    def host(self) -> str:
        return self._host

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        else:
            try:
                loop = asyncio.get_running_loop()
                if self._session._loop is not None and (self._session._loop != loop or self._session._loop.is_closed()):
                    try:
                        await self._session.close()
                    except Exception:
                        pass
                    self._session = aiohttp.ClientSession(timeout=self._timeout)
            except Exception:
                pass
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def health_check(self) -> bool:
        try:
            session = await self._get_session()
            async with session.get(f"{self._host}/api/tags") as resp:
                return resp.status == 200
        except Exception as e:
            logger.warning("Ollama health check failed: %s", e)
            return False

    async def list_models(self) -> list[str]:
        try:
            session = await self._get_session()
            async with session.get(f"{self._host}/api/tags") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [m["name"] for m in data.get("models", [])]
                return []
        except Exception as e:
            logger.error("Failed to list Ollama models: %s", e)
            return []

    async def generate(
        self,
        prompt: str,
        system: str = "",
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        config = get_config()
        payload = {
            "model": model or self._model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature if temperature is not None else config.ollama.temperature,
                "num_predict": max_tokens or config.ollama.max_tokens,
            },
        }
        if system:
            payload["system"] = system

        try:
            session = await self._get_session()
            async with session.post(f"{self._host}/api/generate", json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("response", "")
                error_text = await resp.text()
                logger.error("Ollama generate error (%d): %s", resp.status, error_text)
                return ""
        except Exception as e:
            logger.error("Ollama generate failed: %s", e)
            return ""

    async def generate_stream(
        self,
        prompt: str,
        system: str = "",
        model: str | None = None,
        temperature: float | None = None,
    ) -> AsyncGenerator[str, None]:
        config = get_config()
        payload = {
            "model": model or self._model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature if temperature is not None else config.ollama.temperature,
                "num_predict": config.ollama.max_tokens,
            },
        }
        if system:
            payload["system"] = system

        try:
            session = await self._get_session()
            async with session.post(f"{self._host}/api/generate", json=payload) as resp:
                if resp.status == 200:
                    async for line in resp.content:
                        if line:
                            import orjson
                            try:
                                data = orjson.loads(line)
                                token = data.get("response", "")
                                if token:
                                    yield token
                                if data.get("done", False):
                                    return
                            except Exception:
                                continue
        except Exception as e:
            logger.error("Ollama stream failed: %s", e)

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
    ) -> str:
        config = get_config()
        payload = {
            "model": model or self._model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature if temperature is not None else config.ollama.temperature,
                "num_predict": config.ollama.max_tokens,
            },
        }

        try:
            session = await self._get_session()
            async with session.post(f"{self._host}/api/chat", json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("message", {}).get("content", "")
                error_text = await resp.text()
                logger.error("Ollama chat error (%d): %s", resp.status, error_text)
                return ""
        except Exception as e:
            logger.error("Ollama chat failed: %s", e)
            return ""

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
    ) -> AsyncGenerator[str, None]:
        config = get_config()
        payload = {
            "model": model or self._model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature if temperature is not None else config.ollama.temperature,
                "num_predict": config.ollama.max_tokens,
            },
        }

        try:
            session = await self._get_session()
            async with session.post(f"{self._host}/api/chat", json=payload) as resp:
                if resp.status == 200:
                    async for line in resp.content:
                        if line:
                            import orjson
                            try:
                                data = orjson.loads(line)
                                token = data.get("message", {}).get("content", "")
                                if token:
                                    yield token
                                if data.get("done", False):
                                    return
                            except Exception:
                                continue
        except Exception as e:
            logger.error("Ollama chat stream failed: %s", e)

    async def embeddings(self, text: str, model: str | None = None) -> list[float]:
        config = get_config()
        payload = {
            "model": model or config.ollama.embedding_model,
            "prompt": text,
        }

        try:
            session = await self._get_session()
            async with session.post(f"{self._host}/api/embeddings", json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("embedding", [])
                return []
        except Exception as e:
            logger.error("Ollama embeddings failed: %s", e)
            return []

    async def pull_model(self, model_name: str) -> bool:
        try:
            session = await self._get_session()
            payload = {"name": model_name, "stream": False}
            long_timeout = aiohttp.ClientTimeout(total=3600)
            async with session.post(
                f"{self._host}/api/pull",
                json=payload,
                timeout=long_timeout,
            ) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error("Failed to pull model %s: %s", model_name, e)
            return False

    async def get_model_info(self, model_name: str | None = None) -> dict[str, Any]:
        try:
            session = await self._get_session()
            payload = {"name": model_name or self._model}
            async with session.post(f"{self._host}/api/show", json=payload) as resp:
                if resp.status == 200:
                    return await resp.json()
                return {}
        except Exception as e:
            logger.error("Failed to get model info: %s", e)
            return {}
