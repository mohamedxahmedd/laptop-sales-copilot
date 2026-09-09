# V4.4.5 — Live Sheet Price Unit Fix

Fixes prices like `37` being shown as `37 جنيه` when the live Google Sheet
stores laptop prices in thousands.

Examples:
- `37` -> `37,000 EGP`
- `37.5` -> `37,500 EGP`
- `49,5` -> `49,500 EGP`
- `37,500` -> stays `37,500 EGP`
- `37500` -> stays `37,500 EGP`

The original raw price is also kept internally as `price_raw` for diagnostics.

This also fixes budget filtering: a 37,500 EGP laptop can no longer pass a
`Budget <= 25,000` filter just because the sheet stored the cell as `37.5`.
