import os
import sys
import time
import json
import requests

CLIENT_ID = "Iv1.b507a08c87ecfe98"
DEVICE_CODE_URL = "https://github.com/login/device/code"
ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
COPILOT_TOKEN_URL = "https://api.github.com/copilot_internal/v2/token"

UA = "GitHubCopilotChat/0.26.7"
EDITOR_VERSION = "vscode/1.99.3"
EDITOR_PLUGIN_VERSION = "copilot-chat/0.26.7"

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
    print("Please complete authentication:")
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
        # If GitHub returns non-200 here, treat as retryable unless truly bad
        if resp.status_code != 200:
            time.sleep(interval)
            continue

        data = resp.json()
        if "access_token" in data and data["access_token"]:
            return data["access_token"]

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
    # Expected keys: token, expires_at, refresh_in, endpoints: { api }
    return data["token"], data["endpoints"]["api"]

def try_chat(api_base: str, copilot_token: str, prompt: str, model: str | None):
    # Try preferred OpenAI-like path first, then a fallback
    for path in ("/v1/chat/completions", "/chat/completions"):
        url = api_base.rstrip("/") + path
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {copilot_token}",
            "User-Agent": UA,
            "Editor-Version": EDITOR_VERSION,
            "Editor-Plugin-Version": EDITOR_PLUGIN_VERSION,
        }
        body = {
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        if model:
            body["model"] = model

        try:
            resp = requests.post(url, headers=headers, json=body, timeout=60)
        except requests.RequestException as e:
            print(f"Request error calling {url}: {e}")
            continue

        if resp.status_code == 404:
            # Try the next path
            continue

        if resp.status_code != 200:
            print(f"Non-200 from {url}: {resp.status_code} {resp.text}")
            # Some servers respond 400 if model is required; hint to set MODEL
            if resp.status_code == 400 and "model" in resp.text.lower() and not model:
                print("Hint: The endpoint may require a model. Set env var MODEL (e.g., MODEL=gpt-4o).")
            return None

        data = resp.json()
        # Try to extract content in OpenAI-like structure
        try:
            return data["choices"][0]["message"]["content"]
        except Exception:
            print("Unexpected response; full JSON follows:")
            print(json.dumps(data, indent=2))
            return None

    print("Could not find a working chat/completions path at the Copilot API base.")
    return None

def main():
    prompt = "Say hello from GitHub Copilot." if len(sys.argv) < 2 else " ".join(sys.argv[1:])
    model = os.environ.get("MODEL")  # Optional, e.g. "gpt-4o" depending on access

    # 1) Device flow
    device_code, interval, expires_in = start_device_flow()

    # 2) Poll for GitHub OAuth token
    print("Waiting for authorization...")
    github_oauth_token = poll_for_github_access_token(device_code, interval, expires_in)
    print("GitHub OAuth token acquired.")

    # 3) Exchange for Copilot API token
    copilot_token, api_base = exchange_for_copilot_token(github_oauth_token)
    print(f"Copilot token acquired. API base: {api_base}")

    # 4) Send a chat prompt
    print("Sending prompt to Copilot...")
    reply = try_chat(api_base, copilot_token, prompt, model)

    if reply is not None:
        print("\n=== Copilot reply ===")
        print(reply)
    else:
        print("No reply extracted; see logs above.")

if __name__ == "__main__":
    main()