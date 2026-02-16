#!/usr/bin/env python3
"""探测 GitHub Models API 实际可用的模型"""
import httpx
import os
import sys

token = os.environ.get("GITHUB_TOKEN")
if not token:
    print("ERROR: No GITHUB_TOKEN found")
    sys.exit(1)

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
url = "https://models.inference.ai.azure.com/chat/completions"

# 推理模型 (用 max_completion_tokens)
reasoning = ["o1", "o1-mini", "o1-preview", "o3", "o3-mini", "o4-mini"]

# 标准模型 (用 max_tokens)
standard = [
    "Claude-3.5-Sonnet", "claude-3-5-sonnet",
    "Claude-3.5-Haiku", "claude-3-5-haiku",
    "Claude-3-Opus", "claude-3-opus",
    "Claude-4-Sonnet", "Claude-Sonnet-4",
    "Claude-4-Opus", "Claude-Opus-4",
    "claude-opus-4-20250514",
    "Mistral-Large-2411", "Mistral-large",
    "Mistral-Small-2503",
    "Llama-4-Maverick-17B-128E-Instruct-FP8",
    "Phi-4-multimodal-instruct",
    "Phi-4-mini-instruct",
    "AI21-Jamba-1.5-Large",
    "AI21-Jamba-1.5-Mini",
]

print("=== Reasoning models (max_completion_tokens) ===")
for model in reasoning:
    try:
        resp = httpx.post(url, headers=headers, json={
            "model": model,
            "messages": [{"role": "user", "content": "say ok"}],
            "max_completion_tokens": 5,
        }, timeout=20)
        if resp.status_code == 200:
            print(f"  {model:50s} OK")
        else:
            err = ""
            try:
                err = resp.json().get("error", {}).get("message", "")[:60]
            except:
                err = resp.text[:60]
            print(f"  {model:50s} FAIL {resp.status_code} {err}")
    except Exception as e:
        print(f"  {model:50s} ERR {str(e)[:40]}")

print("\n=== Standard models (max_tokens) ===")
for model in standard:
    try:
        resp = httpx.post(url, headers=headers, json={
            "model": model,
            "messages": [{"role": "user", "content": "say ok"}],
            "max_tokens": 5,
        }, timeout=20)
        if resp.status_code == 200:
            print(f"  {model:50s} OK")
        else:
            err = ""
            try:
                err = resp.json().get("error", {}).get("message", "")[:60]
            except:
                err = resp.text[:60]
            print(f"  {model:50s} FAIL {resp.status_code} {err}")
    except Exception as e:
        print(f"  {model:50s} ERR {str(e)[:40]}")
