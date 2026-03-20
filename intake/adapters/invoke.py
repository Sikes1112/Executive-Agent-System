#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def read_text_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def http_post_json(url: str, payload: dict, headers: dict[str, str], timeout: int = 120) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8"))


def invoke_ollama(model: str, system_prompt: str, message: str) -> str:
    base = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    url = f"{base}/api/chat"
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ],
    }
    headers = {"Content-Type": "application/json"}
    out = http_post_json(url, payload, headers)
    message_obj = out.get("message")
    if not isinstance(message_obj, dict):
        raise RuntimeError("ollama response missing message object")
    content = message_obj.get("content")
    if not isinstance(content, str):
        raise RuntimeError("ollama response missing message.content text")
    return content


def invoke_anthropic(model: str, system_prompt: str, message: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is required for anthropic provider")
    url = "https://api.anthropic.com/v1/messages"
    payload = {
        "model": model,
        "max_tokens": 4096,
        "system": system_prompt,
        "messages": [{"role": "user", "content": message}],
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    out = http_post_json(url, payload, headers)
    blocks = out.get("content")
    if not isinstance(blocks, list):
        raise RuntimeError("anthropic response missing content array")
    text_parts: list[str] = []
    for block in blocks:
        if isinstance(block, dict) and block.get("type") == "text":
            t = block.get("text")
            if isinstance(t, str):
                text_parts.append(t)
    if not text_parts:
        raise RuntimeError("anthropic response has no text content")
    return "".join(text_parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", choices=["ollama", "anthropic"], required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--system-prompt", required=True)
    ap.add_argument("--message", required=True)
    args = ap.parse_args()

    system_prompt = read_text_file(args.system_prompt)
    message = read_text_file(args.message)

    try:
        if args.provider == "ollama":
            text = invoke_ollama(args.model, system_prompt, message)
        else:
            text = invoke_anthropic(args.model, system_prompt, message)
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        print(f"invoke_http_error status={e.code} body={body}", file=sys.stderr)
        return 2
    except urllib.error.URLError as e:
        print(f"invoke_network_error reason={e.reason}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"invoke_error {e}", file=sys.stderr)
        return 2

    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
