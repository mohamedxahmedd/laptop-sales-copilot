# V4.4.2 — Private Google Sheet Connection Fix

- Replaced gspread sheet loading with direct Google Sheets API v4 calls.
- OAuth refresh no longer forces scopes during token refresh.
- Clear errors for:
  - mismatched/revoked refresh token
  - Sheets API not enabled
  - wrong Gmail access
  - bad sheet URL
  - wrong gid / worksheet name
- Google Sheet URL is prefilled from Streamlit Secrets.
- Added "تحديث المخزون من Google Sheet" button.
- Cache reduced to 30 seconds.
- Startup/read errors now show exception type and a useful message instead of a blank banner.
