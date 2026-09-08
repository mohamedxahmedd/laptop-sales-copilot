# Deploy Laptop Sales Copilot

## Option 1 — Streamlit Community Cloud (easiest)

1. Create a private GitHub repository.
2. Upload the project files **without `.env`**.
3. In Streamlit Community Cloud, create a new app from the repository.
4. Main file path: `app.py`.
5. In the app's **Secrets** section add:

```toml
SBG_API_KEY = "YOUR_NEW_KEY"
ITI_BASE_URL = "http://apiaccess.iti.net.eg/api/v1"
ITI_MODEL = "deepseek.v3.2"

# Strongly recommended because this tool is private:
APP_PASSWORD = "choose-a-strong-password"
```

Optional live public Google Sheet:

```toml
DEFAULT_INVENTORY_SOURCE = "Google Sheet"
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/..."
GOOGLE_SHEET_WORKSHEET = "Sheet1"
```

The app automatically reads Streamlit Secrets into environment variables.

## Option 2 — Render / Docker

This project includes:

- `Dockerfile`
- `render.yaml`

Push the project to GitHub and create a Render Blueprint or Docker web service.

Set these environment variables on the hosting dashboard:

```text
SBG_API_KEY=YOUR_NEW_KEY
ITI_BASE_URL=http://apiaccess.iti.net.eg/api/v1
ITI_MODEL=deepseek.v3.2
APP_PASSWORD=choose-a-strong-password
```

Do not upload `.env` to GitHub.

## Before deploying

The API key previously pasted into a chat should be rotated before a public or cloud deployment.

Use `.env` only for local development. `.gitignore` already excludes it.
