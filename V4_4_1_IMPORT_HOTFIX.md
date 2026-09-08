# V4.4.1 Import Hotfix

Fixes Streamlit startup crash:
`ImportError: cannot import name google_user_oauth_configured from src.inventory`

The Google user-OAuth implementation now lives in its own
`src/google_sheet_oauth.py` module so the app does not depend on a matching
`src/inventory.py` version during Streamlit deploys.

Private Google Sheets continue to use:
- GOOGLE_CLIENT_ID
- GOOGLE_CLIENT_SECRET
- GOOGLE_REFRESH_TOKEN
- GOOGLE_SHEET_URL
