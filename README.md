# GitHub Copilot API Tools

Python tools for interacting with GitHub Copilot's API using OAuth device flow authentication.

## Overview

This repository provides two command-line tools that demonstrate how to authenticate with GitHub Copilot and interact with its API:

- **`copilot_chat.py`** - Interactive chat client for sending prompts to GitHub Copilot
- **`copilot_models.py`** - Model discovery tool to list and verify available Copilot models

## Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- A GitHub account with Copilot access

## Installation

1. Clone the repository:
```bash
git clone https://github.com/ipdelete/copilot.git
cd copilot
```

2. Install dependencies with uv (automatically handled when running scripts):
```bash
uv sync
```

## Usage

### Copilot Chat

Send prompts to GitHub Copilot and receive AI-generated responses:

```bash
# Basic usage with default prompt
uv run copilot_chat.py

# Custom prompt
uv run copilot_chat.py "Explain how OAuth device flow works"

# With specific model
MODEL=gpt-4o uv run copilot_chat.py "Write a Python function to sort a list"
```

### Model Discovery

List and verify available GitHub Copilot models:

```bash
# List stable models
uv run copilot_models.py

# Include experimental models
uv run copilot_models.py --include-experimental

# Verify access to models (requires authentication)
uv run copilot_models.py --verify

# Limit verification checks
uv run copilot_models.py --verify --verify-limit 5

# Output as JSON
uv run copilot_models.py --json
```

## Authentication Flow

Both tools use GitHub's OAuth device flow:

1. **Device Code Request** - Generate a user code and verification URL
2. **User Authorization** - User visits URL and enters the code
3. **Token Polling** - Tool polls GitHub for authorization completion
4. **Token Exchange** - Exchange GitHub token for Copilot API token
5. **API Access** - Use Copilot API token to make requests

## Features

- ✅ OAuth device flow authentication
- ✅ Automatic token exchange for Copilot API access
- ✅ Support for multiple Copilot models
- ✅ Model discovery and verification
- ✅ JSON output support for automation
- ✅ Comprehensive error handling

## Project Structure

```
.
├── copilot_chat.py      # Chat client implementation
├── copilot_models.py    # Model discovery tool
├── pyproject.toml       # Project configuration
├── uv.lock              # Dependency lock file
├── README.md            # This file
└── AGENTS.md            # Detailed agent documentation
```

## Documentation

- **[AGENTS.md](AGENTS.md)** - Detailed documentation of agent capabilities, authentication flow, and API endpoints

## Dependencies

- `requests>=2.32.5` - HTTP client library

## Environment Variables

- `MODEL` - (Optional) Specify the Copilot model to use (e.g., `gpt-4o`, `gpt-4`, `gpt-3.5-turbo`)

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is provided as-is for educational and demonstration purposes.

## Related Resources

- [GitHub Copilot Documentation](https://docs.github.com/en/copilot)
- [OAuth Device Flow](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps#device-flow)
- [Models.dev API](https://models.dev/)
