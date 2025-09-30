# AI Agents

This document describes the AI agents and automation capabilities in this repository.

## GitHub Copilot API Tools

This repository contains Python tools for interacting with GitHub Copilot's API using OAuth device flow authentication.

## Tools

### 1. Copilot Chat Agent (`copilot_chat.py`)

An interactive chat client that sends prompts to GitHub Copilot and receives responses.

**Capabilities:**
- Authenticate with GitHub using OAuth device flow
- Exchange GitHub OAuth tokens for Copilot API tokens
- Send chat prompts to GitHub Copilot
- Receive and display AI-generated responses

**Usage:**

```bash
# Basic usage with default prompt
uv run copilot_chat.py

# Custom prompt
uv run copilot_chat.py "Your custom prompt here"

# With specific model (optional)
MODEL=gpt-4o uv run copilot_chat.py "Your prompt"
```

### 2. Copilot Models Discovery (`copilot_models.py`)

A tool to discover and verify available GitHub Copilot models from the Models.dev manifest.

**Capabilities:**
- Fetch GitHub Copilot models from Models.dev API
- Filter experimental vs. stable models
- Optionally verify access to each model with live authentication
- Output results in human-readable or JSON format

**Usage:**

```bash
# List available models
uv run copilot_models.py

# Include experimental models
uv run copilot_models.py --include-experimental

# Verify access to models (requires authentication)
uv run copilot_models.py --verify

# Limit verification to first N models
uv run copilot_models.py --verify --verify-limit 5

# Output as JSON
uv run copilot_models.py --json
```

## Authentication Flow

Both tools share a common authentication flow:

```
1. Start Device Flow
   ├─ Generate device code
   └─ Display verification URL and user code

2. Poll for Authorization
   ├─ Wait for user to complete authentication
   └─ Obtain GitHub OAuth token

3. Exchange for Copilot Token
   ├─ Call Copilot token endpoint
   └─ Receive API token and base URL

4. Execute Tool Operation
   ├─ copilot_chat.py: Send chat request and display response
   └─ copilot_models.py: Verify model access (if --verify flag used)
```

### Configuration

- **CLIENT_ID**: GitHub OAuth app client ID (Iv1.b507a08c87ecfe98)
- **MODEL**: Optional environment variable to specify the model
- **USER_AGENT**: Configured to match VS Code extension

### API Endpoints

**Authentication:**
- Device authorization: `https://github.com/login/device/code`
- Access token: `https://github.com/login/oauth/access_token`
- Copilot token: `https://api.github.com/copilot_internal/v2/token`

**Operations:**
- Chat completions: `{api_base}/v1/chat/completions` or `{api_base}/chat/completions`
- Models manifest: `https://models.dev/api.json`

### Dependencies

- `requests>=2.32.5`: HTTP client library

### Future Enhancements

Potential improvements for these tools:

**General:**
- [ ] Token caching and refresh mechanism
- [ ] Configuration file support (YAML/JSON)
- [ ] Logging and debugging modes
- [ ] Better error handling and retry logic

**Chat Agent:**
- [ ] Streaming responses for real-time output
- [ ] Multi-turn conversations with context persistence
- [ ] Support for system messages and conversation history
- [ ] Interactive REPL mode

**Models Discovery:**
- [ ] Cache model manifest locally with TTL
- [ ] Compare manifest with actual API-supported models
- [ ] Export verified models list for automation
- [ ] Performance metrics for each model (latency, token limits)
