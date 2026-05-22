from __future__ import annotations

from typing import Iterable, Optional

import httpx
from httpx_socks import SyncProxyTransport
from google import genai
from google.genai import types

from config import (
    GCP_PROJECT,
    GCP_LOCATION,
    SOCKS_PROXY_URL,
    HTTP_TIMEOUT_SECONDS,
)


_transport = SyncProxyTransport.from_url(SOCKS_PROXY_URL)
_httpx_client = httpx.Client(transport=_transport, timeout=HTTP_TIMEOUT_SECONDS)

client = genai.Client(
    vertexai=True,
    project=GCP_PROJECT,
    location=GCP_LOCATION,
    http_options=types.HttpOptions(httpx_client=_httpx_client),
)


def generate(
    model: str,
    user_text: str,
    system_prompt: Optional[str] = None,
    history: Optional[Iterable[dict]] = None,
) -> str:
    contents = []
    if history:
        for m in history:
            role = "user" if m["role"] == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part(text=m["content"])]))
    contents.append(types.Content(role="user", parts=[types.Part(text=user_text)]))

    cfg = types.GenerateContentConfig(system_instruction=system_prompt) if system_prompt else None
    resp = client.models.generate_content(
        model=model,
        contents=contents,
        config=cfg,
    )
    return resp.text or ""


def generate_simple(model: str, prompt: str) -> str:
    resp = client.models.generate_content(model=model, contents=prompt)
    return resp.text or ""
