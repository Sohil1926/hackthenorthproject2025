import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

from .clients import (
    call_groq,
    call_cohere,
    call_cerebras,
    call_databricks,
    call_vapi,
)


def run(provider: str, prompt: str, system: str, model: str, temperature: float, timeout: float, raw: bool) -> int:
    try:
        if provider == "groq":
            res = call_groq(prompt, system=system or None, model=model or None, temperature=temperature, timeout=timeout)
        elif provider == "cohere":
            res = call_cohere(prompt, system=system or None, model=model or None, temperature=temperature, timeout=timeout)
        elif provider == "cerebras":
            res = call_cerebras(prompt, system=system or None, model=model or None, temperature=temperature, timeout=timeout)
        elif provider == "databricks":
            res = call_databricks(prompt, system=system or None, model=model or None, temperature=temperature, timeout=timeout)
        elif provider == "vapi":
            res = call_vapi(prompt, system=system or None, model=model or None, temperature=temperature, timeout=timeout)
        else:
            print(f"Unknown provider: {provider}", file=sys.stderr)
            return 2
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if raw:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        text = res.get("output_text") or ""
        print(text)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="sigma_mulcher", description="Simple CLI for multiple LLM providers")
    parser.add_argument("--provider", "-p", choices=["groq", "cohere", "cerebras", "databricks", "vapi"], required=True, help="Provider to call")
    parser.add_argument("--prompt", "-q", required=True, help="User prompt text")
    parser.add_argument("--system", "-s", default="", help="Optional system prompt")
    parser.add_argument("--model", "-m", default="", help="Override model name")
    parser.add_argument("--temperature", "-t", type=float, default=float(os.getenv("SIGMA_MULCHER_TEMPERATURE", "0.2")), help="Sampling temperature")
    parser.add_argument("--timeout", type=float, default=float(os.getenv("SIGMA_MULCHER_TIMEOUT", "60")), help="Request timeout seconds")
    parser.add_argument("--raw", action="store_true", help="Print full JSON response")

    args = parser.parse_args(argv)
    return run(
        provider=args.provider,
        prompt=args.prompt,
        system=args.system,
        model=args.model,
        temperature=args.temperature,
        timeout=args.timeout,
        raw=args.raw,
    )


if __name__ == "__main__":
    raise SystemExit(main())
