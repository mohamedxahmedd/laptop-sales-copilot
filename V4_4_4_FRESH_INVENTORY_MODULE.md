# V4.4.4 — Fresh Live Inventory Module

This update removes the app's dependency on the old `src.inventory` import path.

Why:
Streamlit hot reload had served mixed/stale module versions. The UI could still show
`Missing columns: specs` even after a newer inventory.py no longer required specs.

Fix:
- New module: `src/live_inventory.py`
- `app.py` imports Google Sheet loading + normalization only from this new module.
- `specs` is never mandatory.
- If specs is absent, it is synthesized from CPU/RAM/SSD/GPU/VRAM/other columns.
- Google Sheet header row is auto-detected within the first 25 rows.
- Supports English and Arabic inventory column names.
- Visible `Build 4.4.4` marker in the UI confirms the running deploy.
- Uses direct Google Sheets API with the existing Gmail OAuth secrets.
