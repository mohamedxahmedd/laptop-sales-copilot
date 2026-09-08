from __future__ import annotations

import os
import re
from typing import Optional

import pandas as pd


def google_user_oauth_configured() -> bool:
    """True when the three user-OAuth secrets needed for a private Google Sheet exist."""
    return all(
        os.getenv(key, "").strip()
        for key in (
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
            "GOOGLE_REFRESH_TOKEN",
        )
    )


def _gid_from_url(url: str) -> Optional[int]:
    match = re.search(r"(?:[#?&]gid=)(\d+)", url or "")
    return int(match.group(1)) if match else None


def _sheet_id_from_url(url: str) -> Optional[str]:
    match = re.search(r"/spreadsheets/d/([^/]+)", url or "")
    return match.group(1) if match else None


def _public_csv_url(url: str) -> str:
    sheet_id = _sheet_id_from_url(url)
    if not sheet_id:
        return url
    gid = _gid_from_url(url)
    gid_part = f"&gid={gid}" if gid is not None else ""
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv{gid_part}"


def _safe_dataframe(values: list[list[str]]) -> pd.DataFrame:
    if not values:
        return pd.DataFrame()

    headers = [str(x).strip() for x in values[0]]
    seen = {}
    safe_headers = []
    for i, header in enumerate(headers):
        base = header or f"column_{i+1}"
        count = seen.get(base, 0)
        seen[base] = count + 1
        safe_headers.append(base if count == 0 else f"{base}_{count+1}")

    width = len(safe_headers)
    rows = []
    for row in values[1:]:
        row = list(row)
        row = row[:width] + [""] * max(0, width - len(row))
        rows.append(row[:width])

    return pd.DataFrame(rows, columns=safe_headers)


def _oauth_client():
    import gspread
    from google.oauth2.credentials import Credentials

    creds = Credentials(
        token=None,
        refresh_token=os.getenv("GOOGLE_REFRESH_TOKEN", "").strip(),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID", "").strip(),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET", "").strip(),
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    return gspread.authorize(creds)


def load_google_sheet(url: str, worksheet_name: str = "") -> pd.DataFrame:
    """
    Reads a private Google Sheet using the Gmail user's OAuth refresh token.
    If OAuth secrets are absent, falls back to public CSV export.
    """
    url = (url or "").strip()
    worksheet_name = (worksheet_name or "").strip()

    if not url:
        raise ValueError("Google Sheet URL is empty.")

    if google_user_oauth_configured():
        gc = _oauth_client()
        spreadsheet = gc.open_by_url(url)

        if worksheet_name:
            worksheet = spreadsheet.worksheet(worksheet_name)
        else:
            gid = _gid_from_url(url)
            if gid is not None:
                try:
                    worksheet = spreadsheet.get_worksheet_by_id(gid)
                except Exception:
                    # Compatibility fallback for gspread versions where direct ID lookup differs.
                    worksheet = next(
                        (ws for ws in spreadsheet.worksheets() if int(ws.id) == int(gid)),
                        None,
                    )
                    if worksheet is None:
                        raise ValueError(f"Couldn't find worksheet with gid={gid}.")
            else:
                worksheet = spreadsheet.sheet1

        return _safe_dataframe(worksheet.get_all_values())

    # Public fallback remains available for non-private sheets.
    return pd.read_csv(_public_csv_url(url))
