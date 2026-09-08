from __future__ import annotations
import re
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

from .utils import clean_text, parse_number

ALIASES = {
    "model": [
        "model", "الموديل", "اﻟﻣودﯾل", "موديل", "device", "laptop",
        "device model", "اسم الجهاز", "الجهاز", "اسم الموديل"
    ],
    "specs": [
        "specs", "specifications", "المواصفات", "اﻟﻣوﺻﻔﺎت", "مواصفات",
        "configuration", "config", "configuration/specs"
    ],
    "qty": [
        "qty", "quantity", "stock", "العدد", "اﻟﻌدد", "كمية", "الكميه", "الكمية",
        "available", "availability", "المتاح", "متاح"
    ],
    "screen_inches": [
        "screen", "screen_inches", "screen size", "display", "display size",
        "الشاشه", "الشاشة", "اﻟﺷﺎﺷﮫ", "حجم الشاشة"
    ],
    "price_egp": [
        "price", "price_egp", "selling price", "sale price",
        "السعر", "اﻟﺳﻌر", "سعر", "سعر البيع", "price egp"
    ],
    "camera": ["camera", "الكاميرا", "اﻟﻛﺎﻣﯾرا"],
    "cpu_direct": [
        "cpu", "processor", "processor cpu", "المعالج", "بروسيسور", "البروسيسور"
    ],
    "ram_direct": [
        "ram", "memory", "ram gb", "memory gb", "الرام", "رام", "الرامات", "رامات"
    ],
    "storage_direct": [
        "storage", "ssd", "ssd gb", "hard", "hard disk", "disk",
        "الهارد", "هارد", "مساحة", "التخزين"
    ],
    "gpu_direct": [
        "gpu", "graphics", "graphics card", "vga", "video card",
        "كارت الشاشة", "كارت شاشه", "كارت الشاشة / gpu", "كارت"
    ],
    "vram_direct": [
        "vram", "gpu memory", "graphics memory", "vram gb",
        "ذاكرة كارت الشاشة", "ذاكرة الكارت"
    ],
    "touch_direct": [
        "touch", "touchscreen", "touch screen", "تاتش", "لمس", "شاشة تاتش"
    ],
}



def _canon(s: str) -> str:
    return re.sub(r"[\s_\-]+", "", clean_text(s).lower())


def map_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename = {}
    canon_cols = {_canon(c): c for c in df.columns}
    for target, aliases in ALIASES.items():
        for a in aliases:
            key = _canon(a)
            if key in canon_cols:
                rename[canon_cols[key]] = target
                break
    return df.rename(columns=rename)


def google_sheet_to_csv_url(url: str, worksheet_gid: Optional[str] = None) -> str:
    # Public/read-without-auth fallback only.
    if "docs.google.com/spreadsheets" not in url:
        return url
    m = re.search(r"/d/([^/]+)", url)
    if not m:
        return url
    sheet_id = m.group(1)
    gid = worksheet_gid
    if not gid:
        gm = re.search(r"[#&?]gid=(\d+)", url)
        gid = gm.group(1) if gm else "0"
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def _gid_from_url(url: str) -> Optional[int]:
    m = re.search(r"(?:[#?&]gid=)(\d+)", url or "")
    return int(m.group(1)) if m else None


def _values_to_dataframe(values: list[list[str]]) -> pd.DataFrame:
    if not values:
        return pd.DataFrame()

    headers = [clean_text(x) for x in values[0]]
    # Make empty/duplicate header cells safe for pandas/gspread-like tables.
    seen = {}
    safe_headers = []
    for i, h in enumerate(headers):
        base = h or f"column_{i+1}"
        count = seen.get(base, 0)
        seen[base] = count + 1
        safe_headers.append(base if count == 0 else f"{base}_{count+1}")

    width = len(safe_headers)
    rows = []
    for row in values[1:]:
        padded = list(row[:width]) + [""] * max(0, width - len(row))
        rows.append(padded[:width])
    return pd.DataFrame(rows, columns=safe_headers)


def google_user_oauth_configured() -> bool:
    import os
    return all((os.getenv(k, "").strip() for k in [
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "GOOGLE_REFRESH_TOKEN",
    ]))


def _user_oauth_gspread_client():
    import os
    import gspread
    from google.oauth2.credentials import Credentials

    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials(
        token=None,
        refresh_token=os.getenv("GOOGLE_REFRESH_TOKEN", "").strip(),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID", "").strip(),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET", "").strip(),
        scopes=scopes,
    )
    return gspread.authorize(creds)


def load_google_sheet(
    url: str,
    worksheet_name: str = "",
    service_account_json: str = "",
) -> pd.DataFrame:
    """
    Load a Google Sheet using this priority:
    1) User OAuth from GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET / GOOGLE_REFRESH_TOKEN
       (best for a private sheet shared with the user's Gmail account).
    2) Legacy service-account file, if explicitly supplied.
    3) Public CSV export fallback.

    If worksheet_name is blank and the URL contains #gid=..., that exact tab is used.
    """
    worksheet_name = (worksheet_name or "").strip()
    gid = _gid_from_url(url)

    if google_user_oauth_configured():
        gc = _user_oauth_gspread_client()
        sh = gc.open_by_url(url)
        if worksheet_name:
            ws = sh.worksheet(worksheet_name)
        elif gid is not None:
            ws = sh.get_worksheet_by_id(gid)
        else:
            ws = sh.sheet1
        return _values_to_dataframe(ws.get_all_values())

    if service_account_json:
        import gspread
        gc = gspread.service_account(filename=service_account_json)
        sh = gc.open_by_url(url)
        if worksheet_name:
            ws = sh.worksheet(worksheet_name)
        elif gid is not None:
            ws = sh.get_worksheet_by_id(gid)
        else:
            ws = sh.sheet1
        return _values_to_dataframe(ws.get_all_values())

    return pd.read_csv(google_sheet_to_csv_url(url))


def load_uploaded_file(file) -> pd.DataFrame:
    name = file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(file)
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(file)
    raise ValueError("Supported files: CSV, XLSX, XLS")



def _parse_capacity_gb(value):
    """Parse RAM/storage values such as 16, 16GB, 512 GB, 1TB."""
    text = clean_text(value).upper()
    if not text:
        return None
    n = parse_number(text)
    if n is None:
        return None
    if "TB" in text or "تيرا" in text:
        n *= 1024
    return float(n)


def _parse_bool(value) -> bool:
    t = clean_text(value).lower()
    if not t:
        return False
    yes = {"1", "true", "yes", "y", "touch", "تاتش", "نعم", "اه", "أه", "ايوه", "أيوه"}
    return t in yes or "touch" in t or "تاتش" in t


def _build_specs_from_columns(df: pd.DataFrame) -> pd.Series:
    """
    Build a parseable specs string when the source sheet keeps CPU/RAM/SSD/GPU
    in separate columns instead of one `specs` column.
    """
    preferred = [
        "cpu_direct", "ram_direct", "storage_direct",
        "gpu_direct", "vram_direct", "touch_direct"
    ]
    excluded = {
        "model", "qty", "screen_inches", "price_egp", "camera", "specs"
    }

    # First use recognized hardware columns, then any remaining descriptive columns.
    cols = [c for c in preferred if c in df.columns]
    for c in df.columns:
        if c not in excluded and c not in cols:
            # Ignore completely empty columns.
            try:
                if df[c].map(clean_text).eq("").all():
                    continue
            except Exception:
                pass
            cols.append(c)

    def row_to_specs(row):
        parts = []
        for c in cols:
            val = clean_text(row.get(c))
            if not val:
                continue
            label = str(c).replace("_direct", "").replace("_", " ")
            parts.append(f"{label}: {val}")
        return " | ".join(parts)

    return df.apply(row_to_specs, axis=1)


def normalize_inventory(df: pd.DataFrame) -> Tuple[pd.DataFrame, list[str]]:
    warnings = []
    original_columns = [clean_text(c) for c in df.columns]
    df = map_columns(df.copy())

    # Model is the only truly mandatory field.
    if "model" not in df.columns:
        raise ValueError(
            "Missing column: model. "
            f"Detected columns: {', '.join(original_columns)}"
        )

    # The original PDF seed used one `specs` column, but many live inventory
    # sheets split CPU/RAM/SSD/GPU into separate columns. Support both formats.
    if "specs" not in df.columns:
        df["specs"] = _build_specs_from_columns(df)
        warnings.append(
            "عمود specs غير موجود؛ تم تكوين المواصفات تلقائيًا من أعمدة الشيت."
        )

    for c in ["qty", "screen_inches", "price_egp", "camera"]:
        if c not in df.columns:
            df[c] = None
            warnings.append(f"Column '{c}' not found; using empty values.")

    df["model"] = df["model"].map(clean_text)
    df["specs"] = df["specs"].map(clean_text)
    df["qty"] = df["qty"].map(parse_number).fillna(0).astype(int)
    df["screen_inches"] = df["screen_inches"].map(parse_number)
    df["price_egp"] = df["price_egp"].map(parse_number)
    df["camera"] = df["camera"].map(clean_text)

    # Drop completely empty rows.
    df = df[(df["model"] != "") | (df["specs"] != "")].reset_index(drop=True)

    parsed = df.apply(
        lambda r: parse_specs(r["model"], r["specs"]),
        axis=1,
        result_type="expand",
    )
    for c in parsed.columns:
        df[c] = parsed[c]

    # Direct structured sheet columns are more reliable than re-parsing the
    # synthesized specs string, so let them override parsed values when present.
    if "cpu_direct" in df.columns:
        direct = df["cpu_direct"].map(clean_text)
        mask = direct != ""
        df.loc[mask, "cpu"] = direct[mask]

    if "ram_direct" in df.columns:
        direct = df["ram_direct"].map(_parse_capacity_gb)
        mask = direct.notna()
        df.loc[mask, "ram_gb"] = direct[mask]

    if "storage_direct" in df.columns:
        direct = df["storage_direct"].map(_parse_capacity_gb)
        mask = direct.notna()
        df.loc[mask, "storage_gb"] = direct[mask]

    if "gpu_direct" in df.columns:
        def parse_direct_gpu(value):
            text = clean_text(value)
            if not text:
                return ("", None)
            return detect_gpu(text.upper())

        gpu_parsed = df["gpu_direct"].map(parse_direct_gpu)
        direct_gpu = gpu_parsed.map(lambda x: x[0])
        direct_vram = gpu_parsed.map(lambda x: x[1])

        mask = direct_gpu != ""
        df.loc[mask, "gpu"] = direct_gpu[mask]

        vmask = direct_vram.notna()
        df.loc[vmask, "gpu_vram_gb"] = direct_vram[vmask]

    if "vram_direct" in df.columns:
        direct = df["vram_direct"].map(_parse_capacity_gb)
        mask = direct.notna()
        df.loc[mask, "gpu_vram_gb"] = direct[mask]

    if "touch_direct" in df.columns:
        direct = df["touch_direct"].map(_parse_bool)
        # Explicit touch column should be authoritative when supplied.
        df["touch"] = direct

    return df, warnings


def parse_specs(model: str, specs: str) -> dict:
    text = f"{model} {specs}".upper().replace("\\", " / ")
    text = re.sub(r"\s+", " ", text)

    touch = "TOUCH" in text or "X360" in text

    nums = [int(x) for x in re.findall(r"(?<!\d)(4|8|16|24|32|48|64|128|256|512|1024|2048)(?!\d)", specs.upper())]
    ram = None
    storage = None
    candidates_ram = [n for n in nums if n in {4, 8, 16, 24, 32, 48, 64, 128}]
    candidates_storage = [n for n in nums if n in {128, 256, 512, 1024, 2048}]
    if candidates_ram:
        ram = candidates_ram[0]
    if candidates_storage:
        storage = candidates_storage[-1]
        if ram == 128 and len(candidates_ram) > 1:
            ram = candidates_ram[1]

    cpu = detect_cpu(text)
    gpu, vram = detect_gpu(text)

    return {
        "cpu": cpu,
        "gpu": gpu,
        "gpu_vram_gb": vram,
        "ram_gb": ram,
        "storage_gb": storage,
        "touch": touch,
    }


def detect_cpu(text: str) -> str:
    patterns = [
        r"(ULTRA\s*[579]\s*\d*)",
        r"(I[3579][ -]?\d{4,5}[A-Z]{0,2})",
        r"(I[3579]\s+\d{1,2}TH)",
        r"(I[3579]\s+\d{4,5})",
        r"(RYZEN\s*[3579]\s*PRO\s*\d{4}[A-Z]*)",
        r"(R[3579]\s*PRO\s*\d{4}[A-Z]*)",
        r"(RYZEN\s*[3579]\s*\d{4}[A-Z]*)",
        r"(CELERON\s*[A-Z]?\d+)",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip()
    return "Unknown"


def detect_gpu(text: str):
    patterns = [
        (r"(RTX\s*A4000)", 8),
        (r"(RTX\s*A2000)", None),
        (r"(RTX\s*A1000)", None),
        (r"(RTX\s*A500)", None),
        (r"(RTX\s*3060)", None),
        (r"(QUADRO\s*P1000)", None),
        (r"\b(T1200)\b", None),
        (r"\b(T1000)\b", None),
        (r"\b(T600)\b", None),
        (r"\b(A4000)\b", None),
        (r"\b(A2000)\b", None),
        (r"\b(A1000)\b", None),
        (r"\b(A500)\b", None),
        (r"(IRIS\s*XE)", 0),
        (r"(IRIS\s*PLUS)", 0),
        (r"(UHD\s*GRAPHICS)", 0),
        (r"(RADEON\s*GRAPHICS)", 0),
        (r"(AMD\s*VGA)", None),
    ]
    gpu = "Integrated / Unknown"
    default_vram = None
    for p, v in patterns:
        m = re.search(p, text)
        if m:
            gpu = re.sub(r"\s+", " ", m.group(1)).strip()
            default_vram = v
            break

    vram = default_vram
    mems = re.findall(r"(?<!\d)(2|4|6|8|12|16)\s*G(?:B)?\b", text)
    if mems and gpu not in {"IRIS XE", "IRIS PLUS", "UHD GRAPHICS", "RADEON GRAPHICS"}:
        vram = int(mems[-1])
    return gpu, vram
