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
