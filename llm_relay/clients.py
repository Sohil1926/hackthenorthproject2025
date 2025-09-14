import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


_DEFAULT_TIMEOUT = float(os.getenv("SIGMA_MULCHER_TIMEOUT", "60"))


def _make_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    return ctx


def _post_json(url: str, headers: Dict[str, str], payload: Dict[str, Any], timeout: float = _DEFAULT_TIMEOUT) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url=url, data=data, method="POST")
    for k, v in headers.items():
        req.add_header(k, v)
    req.add_header("Content-Type", "application/json")
    ctx = _make_ssl_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            err_body = str(e)
        raise RuntimeError(f"HTTP {e.code} calling {url}: {err_body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error calling {url}: {e}") from e


# -------------------------
# Groq (OpenAI-compatible)
# -------------------------

def call_groq(prompt: str, system: Optional[str] = None, model: Optional[str] = None, temperature: float = 0.2, timeout: float = _DEFAULT_TIMEOUT) -> Dict[str, Any]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("Missing GROQ_API_KEY environment variable")
    base = os.getenv("GROQ_API_BASE", "https://api.groq.com/openai/v1")
    url = f"{base.rstrip('/')}/chat/completions"
    mdl = model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": mdl,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    raw = _post_json(url, headers, payload, timeout=timeout)

    text = None
    if isinstance(raw, dict):
        try:
            text = raw.get("choices", [{}])[0].get("message", {}).get("content")
        except Exception:
            text = None
    return {
        "provider": "groq",
        "model": mdl,
        "output_text": text,
        "raw": raw,
    }


# -------------------------
# Cohere
# -------------------------

def call_cohere(prompt: str, system: Optional[str] = None, model: Optional[str] = None, temperature: float = 0.2, timeout: float = _DEFAULT_TIMEOUT) -> Dict[str, Any]:
    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        raise ValueError("Missing COHERE_API_KEY environment variable")
    url = os.getenv("COHERE_API_BASE", "https://api.cohere.com/v1/chat")
    mdl = model or os.getenv("COHERE_MODEL", "command-r")

    # Cohere chat API accepts a single string message; system can be prepended
    message = prompt if not system else f"[system]: {system}\n\n{prompt}"

    payload = {
        "model": mdl,
        "message": message,
        "temperature": temperature,
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    raw = _post_json(url, headers, payload, timeout=timeout)

    text = None
    if isinstance(raw, dict):
        # Cohere may return 'text' or 'output_text'
        text = raw.get("text") or raw.get("output_text")
        if text is None:
            # Try to synthesize from tool results if present
            generations = raw.get("generations") or []
            if generations and isinstance(generations, list):
                cand = generations[0]
                if isinstance(cand, dict):
                    text = cand.get("text")
    return {
        "provider": "cohere",
        "model": mdl,
        "output_text": text,
        "raw": raw,
    }


# -------------------------
# Cerebras (OpenAI-compatible)
# -------------------------

def call_cerebras(prompt: str, system: Optional[str] = None, model: Optional[str] = None, temperature: float = 0.2, timeout: float = _DEFAULT_TIMEOUT) -> Dict[str, Any]:
    api_key = os.getenv("CEREBRAS_API_KEY")
    if not api_key:
        raise ValueError("Missing CEREBRAS_API_KEY environment variable")
    base = os.getenv("CEREBRAS_API_BASE", "https://api.cerebras.ai/v1")
    url = f"{base.rstrip('/')}/chat/completions"
    mdl = model or os.getenv("CEREBRAS_MODEL", "llama3.1-8b")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": mdl,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    raw = _post_json(url, headers, payload, timeout=timeout)

    text = None
    if isinstance(raw, dict):
        try:
            text = raw.get("choices", [{}])[0].get("message", {}).get("content")
        except Exception:
            text = None
    return {
        "provider": "cerebras",
        "model": mdl,
        "output_text": text,
        "raw": raw,
    }


# -------------------------
# Databricks (AI Gateway - OpenAI-compatible chat)
# -------------------------

def call_databricks(prompt: str, system: Optional[str] = None, model: Optional[str] = None, temperature: float = 0.2, timeout: float = _DEFAULT_TIMEOUT) -> Dict[str, Any]:
    token = os.getenv("DATABRICKS_TOKEN")
    host = os.getenv("DATABRICKS_HOST")
    if not token or not host:
        raise ValueError("Missing DATABRICKS_HOST or DATABRICKS_TOKEN environment variables")
    # Databricks AI Chat Completions API
    base = os.getenv("DATABRICKS_API_BASE", f"https://{host}/api/2.0/ai")
    url = f"{base.rstrip('/')}/chat/completions"
    mdl = model or os.getenv("DATABRICKS_MODEL", "meta-llama/Meta-Llama-3.1-8B-Instruct")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": mdl,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }
    headers = {"Authorization": f"Bearer {token}"}
    raw = _post_json(url, headers, payload, timeout=timeout)

    text = None
    if isinstance(raw, dict):
        try:
            text = raw.get("choices", [{}])[0].get("message", {}).get("content")
        except Exception:
            text = None
    return {
        "provider": "databricks",
        "model": mdl,
        "output_text": text,
        "raw": raw,
    }


# -------------------------
# Vapi (generic HTTP)
# -------------------------

def call_vapi(prompt: str, system: Optional[str] = None, model: Optional[str] = None, temperature: float = 0.2, timeout: float = _DEFAULT_TIMEOUT) -> Dict[str, Any]:
    api_key = os.getenv("VAPI_API_KEY")
    if not api_key:
        raise ValueError("Missing VAPI_API_KEY environment variable")
    base = os.getenv("VAPI_BASE_URL", "https://api.vapi.ai/v1")
    url = f"{base.rstrip('/')}/messages"

    payload = {
        "input": prompt if not system else f"[system]: {system}\n\n{prompt}",
        "model": model or os.getenv("VAPI_MODEL", "default"),
        "temperature": temperature,
    }
    headers = {
        "x-api-key": api_key,
    }
    raw = _post_json(url, headers, payload, timeout=timeout)

    text = None
    if isinstance(raw, dict):
        text = raw.get("text") or raw.get("output") or raw.get("message")
    return {
        "provider": "vapi",
        "model": payload.get("model"),
        "output_text": text,
        "raw": raw,
    }
