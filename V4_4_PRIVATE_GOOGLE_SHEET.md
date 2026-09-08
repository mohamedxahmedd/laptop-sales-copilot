# V4.4 — Private Google Sheet via User OAuth

- Reads a private Google Sheet using the Gmail account that already has access.
- No service-account file is required.
- Credentials are read only from environment variables / Streamlit Secrets.
- Supports selecting the exact tab from the `gid` embedded in a Google Sheet URL.
- Falls back to public CSV export only when user OAuth is not configured.
- Google scope is read-only: `spreadsheets.readonly`.

Required Streamlit Secrets:

```toml
GOOGLE_CLIENT_ID = "..."
GOOGLE_CLIENT_SECRET = "..."
GOOGLE_REFRESH_TOKEN = "..."
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/.../edit?gid=...#gid=..."
DEFAULT_INVENTORY_SOURCE = "Google Sheet"
```
