
from __future__ import annotations
import io
import re
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

from .utils import clean_text, parse_number

ALIASES = {
    "model": ["model", "الموديل", "اﻟﻣودﯾل", "موديل", "device", "laptop"],
    "specs": ["specs", "specifications", "المواصفات", "اﻟﻣوﺻﻔﺎت", "مواصفات"],
    "qty": ["qty", "quantity", "stock", "العدد", "اﻟﻌدد", "كمية"],
    "screen_inches": ["screen", "screen_inches", "الشاشه", "الشاشة", "اﻟﺷﺎﺷﮫ"],
    "price_egp": ["price", "price_egp", "السعر", "اﻟﺳﻌر"],
    "camera": ["camera", "الكاميرا", "اﻟﻛﺎﻣﯾرا"],
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
    # Works for sheets accessible without Google auth.
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

def load_google_sheet(
    url: str,
    worksheet_name: str = "",
    service_account_json: str = "",
) -> pd.DataFrame:
    if service_account_json:
        import gspread
        gc = gspread.service_account(filename=service_account_json)
        sh = gc.open_by_url(url)
        ws = sh.worksheet(worksheet_name) if worksheet_name else sh.sheet1
        return pd.DataFrame(ws.get_all_records())
    return pd.read_csv(google_sheet_to_csv_url(url))

def load_uploaded_file(file) -> pd.DataFrame:
    name = file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(file)
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(file)
    raise ValueError("Supported files: CSV, XLSX, XLS")

def normalize_inventory(df: pd.DataFrame) -> Tuple[pd.DataFrame, list[str]]:
    warnings = []
    df = map_columns(df.copy())

    required = ["model", "specs"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {', '.join(missing)}")

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

    # Drop completely empty rows
    df = df[(df["model"] != "") | (df["specs"] != "")].reset_index(drop=True)

    parsed = df.apply(lambda r: parse_specs(r["model"], r["specs"]), axis=1, result_type="expand")
    for c in parsed.columns:
        df[c] = parsed[c]

    return df, warnings

def parse_specs(model: str, specs: str) -> dict:
    text = f"{model} {specs}".upper().replace("\\", " / ")
    text = re.sub(r"\s+", " ", text)

    touch = "TOUCH" in text or "X360" in text

    # RAM / storage: prefer numeric chunks around separators.
    nums = [int(x) for x in re.findall(r"(?<!\d)(4|8|16|24|32|48|64|128|256|512|1024|2048)(?!\d)", specs.upper())]
    ram = None
    storage = None
    # Common sheet format is CPU - RAM - SSD - GPU
    candidates_ram = [n for n in nums if n in {4, 8, 16, 24, 32, 48, 64, 128}]
    candidates_storage = [n for n in nums if n in {128, 256, 512, 1024, 2048}]
    if candidates_ram:
        ram = candidates_ram[0]
    if candidates_storage:
        # avoid taking 128 CPU fragments; generally the last storage-like value before GPU
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
    # Search explicit memory after GPU-ish area: "4G", "6GB", "8G".
    mems = re.findall(r"(?<!\d)(2|4|6|8|12|16)\s*G(?:B)?\b", text)
    if mems and gpu not in {"IRIS XE", "IRIS PLUS", "UHD GRAPHICS", "RADEON GRAPHICS"}:
        vram = int(mems[-1])
    return gpu, vram
