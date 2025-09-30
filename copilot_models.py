#!/usr/bin/env python3
import argparse
import json
import time
import requests

MODELS_DEV_URL = "https://models.dev/api.json"
GITHUB_COPILOT_PROVIDER_ID = "github-copilot"

# GitHub OAuth Device Flow + Copilot token exchange (mirrors opencode behavior)
CLIENT_ID = "Iv1.b507a08c87ecfe98"
DEVICE_CODE_URL = "https://github.com/login/device/code"
ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
COPILOT_TOKEN_URL = "https://api.github.com/copilot_internal/v2/token"

UA = "GitHubCopilotChat/0.26.7"
EDITOR_VERSION = "vscode/1.99.3"
EDITOR_PLUGIN_VERSION = "copilot-chat/0.26.7"

def fetch_models_manifest():
    resp = requests.get(MODELS_DEV_URL, timeout=30, headers={"User-Agent": "opencode-models-sample/0.0.1"})
    resp.raise_for_status()
    return resp.json()

def list_copilot_models_from_manifest(manifest: dict, include_experimental: bool):
    provider = manifest.get(GITHUB_COPILOT_PROVIDER_ID)
    if not provider:
        return []

    models = provider.get("models", {}) or {}
    out = []
    for model_id, model_info in models.items():
        # Filter out experimental unless explicitly requested (mirrors opencode filtering behavior)
        experimental = bool(model_info.get("experimental"))
        if experimental and not include_experimental:
            continue
        out.append({
            "id": model_id,
            "name": model_info.get("name") or model_id,
            "experimental": experimental,
            "raw": model_info,
        })
    # Sort by display name then id for nicer output
    out.sort(key=lambda m: (m["name"], m["id"]))
    return out

def start_device_flow():
    resp = requests.post(
        DEVICE_CODE_URL,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": UA,
        },
        json={"client_id": CLIENT_ID, "scope": "read:user"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    print("Please complete GitHub authentication for Copilot:")
    print(f"- Visit: {data['verification_uri']}")
    print(f"- Enter code: {data['user_code']}")
    return data["device_code"], int(data.get("interval", 5)), int(data["expires_in"])

def poll_for_github_access_token(device_code: str, interval: int, expires_in: int) -> str:
    deadline = time.time() + expires_in
    while time.time() < deadline:
        resp = requests.post(
            ACCESS_TOKEN_URL,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": UA,
            },
            json={
                "client_id": CLIENT_ID,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
            timeout=30,
        )
        if resp.status_code != 200:
            time.sleep(interval)
            continue

        data = resp.json()
        token = data.get("access_token")
        if token:
            return token

        err = data.get("error")
        if err == "authorization_pending":
            time.sleep(interval)
            continue
        if err == "slow_down":
            interval += 5
            time.sleep(interval)
            continue

        raise RuntimeError(f"Device flow failed: {data!r}")

    raise TimeoutError("Timed out waiting for device authorization.")

def exchange_for_copilot_token(github_oauth_token: str):
    resp = requests.get(
        COPILOT_TOKEN_URL,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {github_oauth_token}",
            "User-Agent": UA,
            "Editor-Version": EDITOR_VERSION,
            "Editor-Plugin-Version": EDITOR_PLUGIN_VERSION,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Copilot token exchange failed: {resp.status_code} {resp.text}")
    data = resp.json()
    return data["token"], data["endpoints"]["api"]

def try_minimal_prompt(api_base: str, copilot_token: str, model_id: str) -> tuple[bool, str]:
    """
    Attempt a minimal chat request to check if this model is usable for the current account.
    Returns (ok, detail).
    """
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {copilot_token}",
        "User-Agent": UA,
        "Editor-Version": EDITOR_VERSION,
        "Editor-Plugin-Version": EDITOR_PLUGIN_VERSION,
    }
    body = {
        "model": model_id,
        "messages": [{"role": "user", "content": "Respond with the single word: ok"}],
        "max_tokens": 5,
        "temperature": 0,
    }

    # Try OpenAI-like first, then fallback
    for path in ("/v1/chat/completions", "/chat/completions"):
        url = api_base.rstrip("/") + path
        try:
            resp = requests.post(url, headers=headers, json=body, timeout=30)
        except requests.RequestException as e:
            return False, f"request-error: {e}"

        if resp.status_code == 404:
            continue

        if resp.status_code == 200:
            try:
                data = resp.json()
            except Exception:
                return True, "200 OK (non-JSON?)"
            # If we can parse choices, consider it usable
            ok = isinstance(data, dict) and "choices" in data
            return ok, f"{resp.status_code} {'ok' if ok else 'unknown-shape'}"

        # 401/403 often means no access to that model
        return False, f"{resp.status_code} {resp.text[:200]}"

    return False, "no-known-chat-path"

def main():
    parser = argparse.ArgumentParser(
        description="List GitHub Copilot models from Models.dev (not from live Copilot APIs). Optionally verify access."
    )
    parser.add_argument("--include-experimental", action="store_true", help="Include experimental models from manifest")
    parser.add_argument("--verify", action="store_true", help="Authenticate and probe each model with a tiny request")
    parser.add_argument("--verify-limit", type=int, default=10, help="Max number of models to probe with --verify")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of human-readable text")
    args = parser.parse_args()

    manifest = fetch_models_manifest()
    models = list_copilot_models_from_manifest(manifest, include_experimental=args.include_experimental)

    disclaimer = (
        "Listing is from Models.dev (filtered/merged), not a live Copilot model listing. "
        "Whether a model actually works depends on your GitHub Copilot subscription and settings."
    )

    if args.verify and models:
        print("Starting verification flow...")
        device_code, interval, expires_in = start_device_flow()
        print("Waiting for authorization...")
        gh_token = poll_for_github_access_token(device_code, interval, expires_in)
        print("GitHub OAuth token acquired.")
        copilot_token, api_base = exchange_for_copilot_token(gh_token)
        print(f"Copilot token acquired. API base: {api_base}")
        to_check = models[: args.verify_limit]
        for m in to_check:
            ok, detail = try_minimal_prompt(api_base, copilot_token, m["id"])
            m["verified"] = ok
            m["verify_detail"] = detail

    if args.json:
        print(json.dumps({
            "provider": GITHUB_COPILOT_PROVIDER_ID,
            "disclaimer": disclaimer,
            "count": len(models),
            "models": [
                {
                    "id": m["id"],
                    "name": m["name"],
                    "experimental": m["experimental"],
                    **({"verified": m.get("verified")} if "verified" in m else {}),
                    **({"verify_detail": m.get("verify_detail")} if "verify_detail" in m else {}),
                }
                for m in models
            ],
        }, indent=2))
        return

    print(disclaimer)
    if not models:
        print("No models found for provider:", GITHUB_COPILOT_PROVIDER_ID)
        return

    print(f"Provider: {GITHUB_COPILOT_PROVIDER_ID}")
    print(f"Models ({len(models)}):")
    for m in models:
        flag = " [experimental]" if m["experimental"] else ""
        vflag = ""
        if "verified" in m:
            vflag = f" [verified={m['verified']}, {m.get('verify_detail','')}]"
        print(f"- {m['name']} ({m['id']}){flag}{vflag}")

if __name__ == "__main__":
    main()