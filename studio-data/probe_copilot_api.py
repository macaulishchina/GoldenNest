import asyncio, json, uuid, httpx, time

COPILOT_TOKEN_URL = "https://api.github.com/copilot_internal/v2/token"
COPILOT_API_BASE = "https://api.githubcopilot.com"

oauth_token = json.load(open("/data/copilot_oauth.json")).get("oauth_token", "")
print(f"OAuth: {oauth_token[:10]}...")

async def main():
    async with httpx.AsyncClient(timeout=30) as client:
        # 1. Get session token and inspect ALL response fields
        print("\n=== 1. Session Token Response ===")
        resp = await client.get(COPILOT_TOKEN_URL, headers={
            "Authorization": f"token {oauth_token}",
            "editor-version": "vscode/1.96.0",
            "editor-plugin-version": "copilot-chat/0.24.0",
            "user-agent": "probe/1.0",
        })
        print(f"Status: {resp.status_code}")
        print(f"Headers:")
        for k, v in resp.headers.items():
            print(f"  {k}: {v}")
        if resp.status_code != 200:
            print(f"Body: {resp.text[:500]}")
            return
        token_data = resp.json()
        print(f"Fields: {list(token_data.keys())}")
        for k, v in token_data.items():
            if k == "token":
                print(f"  token: {str(v)[:60]}...")
            elif k == "endpoints":
                print(f"  endpoints:")
                if isinstance(v, dict):
                    for ek, ev in v.items():
                        print(f"    {ek}: {ev}")
                else:
                    print(f"    {v}")
            else:
                print(f"  {k}: {v}")

        session_token = token_data.get("token", "")
        if not session_token:
            print("No token!")
            return

        headers = {
            "Authorization": f"Bearer {session_token}",
            "Content-Type": "application/json",
            "editor-version": "vscode/1.96.0",
            "editor-plugin-version": "copilot-chat/0.24.0",
            "copilot-integration-id": "vscode-chat",
            "openai-intent": "conversation-panel",
            "x-request-id": str(uuid.uuid4()),
            "vscode-sessionid": str(uuid.uuid4()),
            "vscode-machineid": "probe-machine",
        }

        # 2. GET /models - inspect response headers + model fields
        print("\n=== 2. GET /models ===")
        resp = await client.get(f"{COPILOT_API_BASE}/models", headers=headers)
        print(f"Status: {resp.status_code}")
        print("Response Headers:")
        for k, v in resp.headers.items():
            print(f"  {k}: {v}")

        if resp.status_code == 200:
            data = resp.json()
            models_list = data if isinstance(data, list) else data.get("data") or data.get("models") or data.get("value") or []
            print(f"Total models: {len(models_list)}")
            
            # Print first 2 models in full
            for m in models_list[:2]:
                print(f"\n  --- {m.get('id', m.get('name', '?'))} ---")
                print(f"  {json.dumps(m, indent=4)}")
            
            # All keys across all models
            all_keys = set()
            for m in models_list:
                if isinstance(m, dict):
                    all_keys.update(m.keys())
            print(f"\nAll model keys: {sorted(all_keys)}")

        # 3. Probe Copilot API endpoints
        print("\n=== 3. Probing Copilot API endpoints ===")
        probe_paths = [
            "/usage", "/billing", "/user", "/subscription",
            "/v1/usage", "/rate_limiting", "/agents",
            "/embeddings/models", "/telemetry",
            "/chat/models", "/v1/models",
        ]
        for path in probe_paths:
            r = await client.get(f"{COPILOT_API_BASE}{path}", headers=headers)
            status_icon = "+" if r.status_code == 200 else "-" if r.status_code == 404 else "?"
            print(f"  [{status_icon}] {r.status_code} GET {path}")
            if r.status_code not in (404, 403):
                body_preview = r.text[:200]
                print(f"      Body: {body_preview}")

        # 4. Probe GitHub API copilot-internal endpoints
        print("\n=== 4. Probing GitHub API copilot-internal endpoints ===")
        github_headers = {
            "Authorization": f"token {oauth_token}",
            "Accept": "application/json",
            "editor-version": "vscode/1.96.0",
            "editor-plugin-version": "copilot-chat/0.24.0",
            "user-agent": "probe/1.0",
        }
        github_api = "https://api.github.com"
        
        github_paths = [
            "/user",
            "/copilot_internal/v2/token",
            "/copilot_internal/user",
            "/copilot_internal/v2/user",
            "/copilot_internal/notification",
            "/copilot_internal/v2/chat/premium_requests",
            "/copilot_internal/v2/usage",
            "/copilot_internal/usage",
            "/copilot_internal/v2/models",
            "/copilot_internal/models",
            "/user/copilot_billing/seats",
            "/user/copilot_billing/usage",
            "/copilot/usage",
            "/settings/copilot",
        ]
        for path in github_paths:
            r = await client.get(f"{github_api}{path}", headers=github_headers)
            status_icon = "+" if r.status_code == 200 else "-" if r.status_code == 404 else "?"
            print(f"  [{status_icon}] {r.status_code} GET {path}")
            if r.status_code == 200 and path != "/copilot_internal/v2/token":
                body_preview = r.text[:300]
                print(f"      Body: {body_preview}")

        # 5. Make a small chat completion and inspect response headers
        print("\n=== 5. Chat Completion Response Headers ===")
        chat_body = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Say hi in 3 words"}],
            "max_tokens": 20,
            "stream": False,
        }
        r = await client.post(f"{COPILOT_API_BASE}/chat/completions", headers=headers, json=chat_body)
        print(f"Status: {r.status_code}")
        print("Response Headers:")
        for k, v in r.headers.items():
            print(f"  {k}: {v}")
        if r.status_code == 200:
            data = r.json()
            print(f"Response keys: {list(data.keys())}")
            if "usage" in data:
                print(f"Usage: {data['usage']}")
            for k in data:
                if k not in ("id", "object", "created", "model", "choices", "usage", "system_fingerprint"):
                    print(f"Extra field '{k}': {data[k]}")

asyncio.run(main())
