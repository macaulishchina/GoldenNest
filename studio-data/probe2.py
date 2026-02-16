import asyncio, json, uuid, httpx

COPILOT_TOKEN_URL = "https://api.github.com/copilot_internal/v2/token"

oauth_token = json.load(open("/data/copilot_oauth.json")).get("oauth_token", "")

async def main():
    async with httpx.AsyncClient(timeout=30) as client:
        github_headers = {
            "Authorization": f"token {oauth_token}",
            "Accept": "application/json",
            "editor-version": "vscode/1.96.0",
            "editor-plugin-version": "copilot-chat/0.24.0",
            "user-agent": "probe/1.0",
        }

        # 1. Full /copilot_internal/user response
        print("=== 1. Full /copilot_internal/user ===")
        r = await client.get("https://api.github.com/copilot_internal/user", headers=github_headers)
        print(json.dumps(r.json(), indent=2))

        # 2. Get session token for individual API
        r = await client.get(COPILOT_TOKEN_URL, headers=github_headers)
        token_data = r.json()
        session_token = token_data["token"]
        endpoints = token_data.get("endpoints", {})
        individual_api = endpoints.get("api", "https://api.individual.githubcopilot.com")
        print(f"\n=== 2. Individual API: {individual_api} ===")
        
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

        # 3. Probe individual API endpoints
        print("\n=== 3. Probing individual API ===")
        for path in ["/models", "/usage", "/billing", "/agents", "/user",
                      "/subscription", "/rate_limiting", "/quota",
                      "/premium_requests", "/chat/premium_requests",
                      "/v1/usage", "/v1/models", "/"]:
            r = await client.get(f"{individual_api}{path}", headers=headers)
            icon = "+" if r.status_code == 200 else "-" if r.status_code == 404 else "?"
            detail = ""
            if r.status_code == 200:
                try:
                    data = r.json()
                    if isinstance(data, list):
                        detail = f" [{len(data)} items]"
                    elif isinstance(data, dict):
                        detail = f" keys={list(data.keys())[:10]}"
                except:
                    detail = f" text={r.text[:100]}"
            print(f"  [{icon}] {r.status_code} GET {path}{detail}")

        # 4. Probe the origin-tracker and proxy endpoints
        origin_tracker = endpoints.get("origin-tracker", "")
        proxy = endpoints.get("proxy", "")
        telemetry = endpoints.get("telemetry", "")
        
        for label, base in [("origin-tracker", origin_tracker), ("proxy", proxy), ("telemetry", telemetry)]:
            if not base:
                continue
            print(f"\n=== 4. Probing {label}: {base} ===")
            for path in ["/", "/models", "/usage", "/agents"]:
                try:
                    r = await client.get(f"{base}{path}", headers=headers, timeout=10)
                    icon = "+" if r.status_code == 200 else "-" if r.status_code == 404 else "?"
                    print(f"  [{icon}] {r.status_code} GET {path}  body={r.text[:100]}")
                except Exception as e:
                    print(f"  [!] Error GET {path}: {e}")

        # 5. Check /models on individual API with full detail
        print("\n=== 5. Individual /models detail ===")
        r = await client.get(f"{individual_api}/models", headers=headers)
        if r.status_code == 200:
            data = r.json()
            models_list = data if isinstance(data, list) else data.get("data") or data.get("models") or []
            print(f"Total models: {len(models_list)}")
            all_keys = set()
            for m in models_list:
                if isinstance(m, dict):
                    all_keys.update(m.keys())
                    # Check nested capabilities for any pricing
                    caps = m.get("capabilities", {})
                    if isinstance(caps, dict):
                        all_keys.update(f"capabilities.{k}" for k in caps.keys())
                        limits = caps.get("limits", {})
                        if isinstance(limits, dict):
                            all_keys.update(f"capabilities.limits.{k}" for k in limits.keys())
            print(f"All keys (including nested): {sorted(all_keys)}")
            
            # Show any model with policy data
            for m in models_list:
                policy = m.get("policy", {})
                if isinstance(policy, dict) and len(policy) > 2:
                    print(f"\n  Model {m['id']} policy: {json.dumps(policy, indent=4)}")
                
            # Check if models differ from api.githubcopilot.com
            individual_ids = sorted(m.get("id", "") for m in models_list if isinstance(m, dict))
            print(f"\nModel IDs: {individual_ids}")

        # 6. Check chat completion on individual API
        print("\n=== 6. Chat completion on individual API ===")
        chat_body = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 5,
            "stream": False,
        }
        r = await client.post(f"{individual_api}/chat/completions", headers=headers, json=chat_body)
        print(f"Status: {r.status_code}")
        print("Response Headers:")
        for k, v in r.headers.items():
            print(f"  {k}: {v}")
        if r.status_code == 200:
            data = r.json()
            print(f"Keys: {list(data.keys())}")
            if "usage" in data:
                print(f"Usage: {data['usage']}")

asyncio.run(main())
