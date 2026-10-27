#!/usr/bin/env python3
"""Check this API key's accessible text models without publishing articles."""
import json
import os
import socket
import sys
import urllib.error
import urllib.request

BASE = "https://generativelanguage.googleapis.com/v1beta"
CANDIDATES = ("gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.8-flash")


def request_json(url, key, payload=None, timeout=18):
    headers = {"x-goog-api-key": key, "Accept": "application/json"}
    method = "GET" if payload is None else "POST"
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp), "OK"
    except urllib.error.HTTPError as exc:
        return None, f"HTTP {exc.code}"
    except (TimeoutError, socket.timeout, urllib.error.URLError) as exc:
        return None, "TIMEOUT_OR_NETWORK_ERROR"


def diagnose(key):
    # A model appearing in the list does not prove usable free-tier quota.
    listed, status = request_json(f"{BASE}/models?pageSize=1000", key)
    if listed is None:
        print(f"MODEL_LIST: {status}")
    else:
        available = {model.get("name", "").removeprefix("models/") for model in listed.get("models", [])
                     if "generateContent" in model.get("supportedGenerationMethods", [])}
        for model in CANDIDATES:
            print(f"LIST {model}: {'YES' if model in available else 'NO'}")

    successes = []
    for model in CANDIDATES:
        result, status = request_json(f"{BASE}/models/{model}:generateContent", key,
            {"contents": [{"parts": [{"text": "한 단어로만 답하세요: 확인"}]}],
             "generationConfig": {"maxOutputTokens": 64, "temperature": 0}}, timeout=18)
        if result and result.get("candidates"):
            successes.append(model)
            print(f"PROBE {model}: OK")
        else:
            print(f"PROBE {model}: {status if result is None else 'NO_CANDIDATE'}")
    if successes:
        print("USABLE_MODEL:", successes[0])
        return True
    print("USABLE_MODEL: NONE (no article published; check account tier/status)")
    return False


if __name__ == "__main__":
    secret = os.getenv("GEMINI_API_KEY", "").strip()
    if not secret:
        print("GEMINI_API_KEY is missing", file=sys.stderr)
        sys.exit(1)
    sys.exit(0 if diagnose(secret) else 1)
