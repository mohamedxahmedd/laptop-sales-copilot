from __future__ import annotations

import os
import re
from typing import Optional
from urllib.parse import quote

import pandas as pd
import requests


SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"


def google_user_oauth_configured() -> bool:
    return all(
        os.getenv(key, "").strip()
        for key in (
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
            "GOOGLE_REFRESH_TOKEN",
        )
    )


def _gid_from_url(url: str) -> Optional[int]:
    m = re.search(r"(?:[#?&]gid=)(\d+)", url or "")
    return int(m.group(1)) if m else None


def _sheet_id_from_url(url: str) -> Optional[str]:
    m = re.search(r"/spreadsheets/d/([^/?#]+)", url or "")
    return m.group(1) if m else None


def _safe_dataframe(values: list[list[str]]) -> pd.DataFrame:
    if not values:
        return pd.DataFrame()

    headers = [str(x).strip() for x in values[0]]
    seen: dict[str, int] = {}
    safe_headers: list[str] = []

    for i, header in enumerate(headers):
        base = header or f"column_{i + 1}"
        count = seen.get(base, 0)
        seen[base] = count + 1
        safe_headers.append(base if count == 0 else f"{base}_{count + 1}")

    width = len(safe_headers)
    rows = []
    for row in values[1:]:
        row = list(row)
        row = row[:width] + [""] * max(0, width - len(row))
        rows.append(row[:width])

    return pd.DataFrame(rows, columns=safe_headers)


def _google_error(response: requests.Response) -> str:
    try:
        payload = response.json()
        err = payload.get("error", {})
        message = err.get("message") or str(err)
        status = err.get("status")
        if status:
            return f"{status}: {message}"
        return message
    except Exception:
        text = (response.text or "").strip()
        return text[:600] if text else f"HTTP {response.status_code}"


def _access_token() -> str:
    """
    Refresh the Gmail OAuth token.

    Important: don't force a new scope during refresh. The refresh token already
    carries the scope granted during the one-time local OAuth consent flow.
    """
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN", "").strip()

    if not all((client_id, client_secret, refresh_token)):
        raise RuntimeError(
            "Google OAuth Secrets ناقصة. لازم GOOGLE_CLIENT_ID و "
            "GOOGLE_CLIENT_SECRET و GOOGLE_REFRESH_TOKEN."
        )

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
    )

    try:
        creds.refresh(Request())
    except RefreshError as exc:
        msg = str(exc) or repr(exc)
        raise RuntimeError(
            "فشل تجديد Google OAuth Token. غالبًا الـRefresh Token مش تابع لنفس "
            "Client ID/Secret، أو اتلغى/انتهت صلاحيته. "
            f"Google قال: {msg}"
        ) from exc

    if not creds.token:
        raise RuntimeError("Google رجّع OAuth من غير Access Token.")

    return creds.token


def _request_json(url: str, token: str, *, params: dict | None = None) -> dict:
    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=35,
    )

    if response.status_code >= 400:
        detail = _google_error(response)

        if response.status_code == 403:
            raise RuntimeError(
                "Google رفض قراءة الشيت (403). اتأكد إن: "
                "1) نفس Gmail اللي عمل OAuth هو اللي عنده Access على الشيت، "
                "2) Google Sheets API مفعّلة في نفس Google Cloud Project. "
                f"التفاصيل: {detail}"
            )
        if response.status_code == 404:
            raise RuntimeError(
                "Google مش لاقي الشيت (404). اتأكد من لينك الشيت ومن إن حساب Gmail "
                f"عنده صلاحية عليه. التفاصيل: {detail}"
            )
        if response.status_code == 401:
            raise RuntimeError(
                "Google رفض الـAccess Token (401). اعمل OAuth من جديد بنفس "
                f"Client ID/Secret. التفاصيل: {detail}"
            )

        raise RuntimeError(
            f"Google Sheets API رجعت HTTP {response.status_code}: {detail}"
        )

    try:
        return response.json()
    except Exception as exc:
        raise RuntimeError("Google رجّع Response غير مفهوم أثناء قراءة الشيت.") from exc


def _worksheet_title(
    spreadsheet_id: str,
    token: str,
    worksheet_name: str,
    gid: Optional[int],
) -> str:
    metadata = _request_json(
        f"{SHEETS_API}/{spreadsheet_id}",
        token,
        params={"fields": "sheets.properties(sheetId,title,index)"},
    )

    sheets = metadata.get("sheets") or []
    if not sheets:
        raise RuntimeError("الشيت موجود لكن Google ما رجّعش أي Tabs داخله.")

    props = [s.get("properties", {}) for s in sheets]

    if worksheet_name:
        for p in props:
            if str(p.get("title", "")).strip() == worksheet_name.strip():
                return str(p["title"])
        names = "، ".join(str(p.get("title", "")) for p in props[:12])
        raise RuntimeError(
            f'مش لاقي Tab باسم "{worksheet_name}". الموجود: {names}'
        )

    if gid is not None:
        for p in props:
            try:
                if int(p.get("sheetId")) == int(gid):
                    return str(p["title"])
            except Exception:
                continue
        raise RuntimeError(f"مش لاقي Tab بالـgid={gid} داخل الشيت.")

    # First tab by index.
    props.sort(key=lambda p: int(p.get("index", 0)))
    return str(props[0]["title"])


def load_google_sheet(url: str, worksheet_name: str = "") -> pd.DataFrame:
    """
    Read a private Google Sheet as the Gmail user that granted OAuth access.

    This implementation talks directly to Google Sheets API v4. It does not need
    Drive API, a service-account JSON file, or gspread.
    """
    url = (url or "").strip()
    worksheet_name = (worksheet_name or "").strip()

    if not url:
        raise ValueError("Google Sheet URL فاضي.")

    spreadsheet_id = _sheet_id_from_url(url)
    if not spreadsheet_id:
        raise ValueError(
            "لينك Google Sheet غير صحيح. لازم يكون بالشكل "
            "https://docs.google.com/spreadsheets/d/.../edit"
        )

    if not google_user_oauth_configured():
        raise RuntimeError(
            "Google OAuth مش متظبط في Streamlit Secrets."
        )

    token = _access_token()
    gid = _gid_from_url(url)
    title = _worksheet_title(
        spreadsheet_id,
        token,
        worksheet_name,
        gid,
    )

    # Escape apostrophes in sheet titles for A1 notation.
    safe_title = title.replace("'", "''")
    a1_range = f"'{safe_title}'!A:ZZ"
    encoded_range = quote(a1_range, safe="")

    payload = _request_json(
        f"{SHEETS_API}/{spreadsheet_id}/values/{encoded_range}",
        token,
        params={
            "majorDimension": "ROWS",
            "valueRenderOption": "FORMATTED_VALUE",
        },
    )

    values = payload.get("values") or []
    if not values:
        raise RuntimeError(f'الـTab "{title}" فاضية أو مفيهاش بيانات مقروءة.')

    return _safe_dataframe(values)
