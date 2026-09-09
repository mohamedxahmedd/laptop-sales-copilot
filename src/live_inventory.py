from __future__ import annotations

import os
import re
from typing import Optional, Tuple
from urllib.parse import quote

import pandas as pd
import requests

from .utils import clean_text, parse_number


SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"


ALIASES = {
    "model": [
        "model", "model name", "device", "device model", "laptop", "laptop model",
        "product", "product name", "item", "item name",
        "الموديل", "موديل", "اسم الموديل", "اسم الجهاز", "الجهاز", "الصنف", "اسم الصنف",
    ],
    "specs": [
        "specs", "spec", "specifications", "configuration", "config",
        "configuration/specs", "details", "description",
        "المواصفات", "مواصفات", "التفاصيل",
    ],
    "qty": [
        "qty", "quantity", "stock", "available", "availability", "available qty",
        "العدد", "كمية", "الكميه", "الكمية", "المتاح", "متاح",
    ],
    "screen_inches": [
        "screen", "screen size", "screen_inches", "display", "display size",
        "الشاشة", "الشاشه", "حجم الشاشة",
    ],
    "price_egp": [
        "price", "price egp", "price_egp", "selling price", "sale price",
        "السعر", "سعر", "سعر البيع",
    ],
    "camera": ["camera", "الكاميرا"],
    "cpu_direct": [
        "cpu", "processor", "processor cpu", "processor model",
        "المعالج", "بروسيسور", "البروسيسور",
    ],
    "ram_direct": [
        "ram", "memory", "ram gb", "memory gb",
        "رام", "الرام", "رامات", "الرامات",
    ],
    "storage_direct": [
        "storage", "ssd", "ssd gb", "hard", "hard disk", "disk", "drive",
        "هارد", "الهارد", "التخزين", "مساحة",
    ],
    "gpu_direct": [
        "gpu", "graphics", "graphics card", "video card", "vga",
        "كارت الشاشة", "كارت شاشه", "كارت",
    ],
    "vram_direct": [
        "vram", "vram gb", "gpu memory", "graphics memory",
        "ذاكرة كارت الشاشة", "ذاكرة الكارت",
    ],
    "touch_direct": [
        "touch", "touchscreen", "touch screen", "تاتش", "لمس", "شاشة تاتش",
    ],
}


def _canon(value) -> str:
    text = clean_text(value).lower()
    text = (
        text.replace("أ", "ا")
        .replace("إ", "ا")
        .replace("آ", "ا")
        .replace("ة", "ه")
        .replace("ى", "ي")
    )
    return re.sub(r"[^0-9a-z\u0600-\u06ff]+", "", text)


_CANON_ALIASES = {
    target: {_canon(alias) for alias in aliases}
    for target, aliases in ALIASES.items()
}
_ALL_ALIAS_KEYS = set().union(*_CANON_ALIASES.values())


def google_user_oauth_configured() -> bool:
    return all(
        os.getenv(key, "").strip()
        for key in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN")
    )


def _sheet_id_from_url(url: str) -> Optional[str]:
    match = re.search(r"/spreadsheets/d/([^/?#]+)", url or "")
    return match.group(1) if match else None


def _gid_from_url(url: str) -> Optional[int]:
    match = re.search(r"(?:[#?&]gid=)(\d+)", url or "")
    return int(match.group(1)) if match else None


def _google_error(response: requests.Response) -> str:
    try:
        payload = response.json()
        err = payload.get("error", {})
        return err.get("message") or str(err)
    except Exception:
        return (response.text or f"HTTP {response.status_code}")[:600]


def _access_token() -> str:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    creds = Credentials(
        token=None,
        refresh_token=os.getenv("GOOGLE_REFRESH_TOKEN", "").strip(),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID", "").strip(),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET", "").strip(),
    )
    try:
        creds.refresh(Request())
    except Exception as exc:
        raise RuntimeError(
            "فشل تجديد Google OAuth Token. اتأكد إن Client ID / Client Secret / "
            f"Refresh Token تابعين لنفس OAuth Client. التفاصيل: {exc}"
        ) from exc

    if not creds.token:
        raise RuntimeError("Google OAuth لم يرجع Access Token.")
    return creds.token


def _request_json(url: str, token: str, params: dict | None = None) -> dict:
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
                "Google رفض قراءة الشيت (403). اتأكد إن Google Sheets API مفعلة "
                "وإن نفس Gmail اللي عمل OAuth عنده Access على الشيت. "
                f"التفاصيل: {detail}"
            )
        if response.status_code == 404:
            raise RuntimeError(
                "Google مش لاقي الشيت أو الحساب ملوش صلاحية عليه. "
                f"التفاصيل: {detail}"
            )
        raise RuntimeError(f"Google Sheets API HTTP {response.status_code}: {detail}")
    return response.json()


def _worksheet_title(spreadsheet_id: str, token: str, worksheet_name: str, gid: Optional[int]) -> str:
    metadata = _request_json(
        f"{SHEETS_API}/{spreadsheet_id}",
        token,
        params={"fields": "sheets.properties(sheetId,title,index)"},
    )
    props = [s.get("properties", {}) for s in (metadata.get("sheets") or [])]
    if not props:
        raise RuntimeError("Google لم يرجع أي Tabs داخل الشيت.")

    if worksheet_name:
        for p in props:
            if str(p.get("title", "")).strip() == worksheet_name.strip():
                return str(p["title"])
        names = "، ".join(str(p.get("title", "")) for p in props[:15])
        raise RuntimeError(f'مش لاقي Tab باسم "{worksheet_name}". الموجود: {names}')

    if gid is not None:
        for p in props:
            try:
                if int(p.get("sheetId")) == int(gid):
                    return str(p["title"])
            except Exception:
                pass
        raise RuntimeError(f"مش لاقي Tab بالـgid={gid}.")

    props.sort(key=lambda p: int(p.get("index", 0)))
    return str(props[0]["title"])


def _header_score(row: list[str]) -> tuple[int, int]:
    found_targets = set()
    nonempty = 0
    for cell in row:
        key = _canon(cell)
        if not key:
            continue
        nonempty += 1
        for target, aliases in _CANON_ALIASES.items():
            if key in aliases:
                found_targets.add(target)
                break
    # Strongly prefer rows that contain model/specs or multiple recognized fields.
    bonus = 3 if "model" in found_targets else 0
    bonus += 2 if "specs" in found_targets else 0
    return len(found_targets) + bonus, nonempty


def _detect_header_row(values: list[list[str]]) -> int:
    if not values:
        return 0

    best_idx = 0
    best = (-1, -1)
    for idx, row in enumerate(values[:25]):
        score = _header_score(row)
        if score > best:
            best = score
            best_idx = idx

    # If nothing looked like a header, use the first row with 2+ non-empty cells.
    if best[0] <= 0:
        for idx, row in enumerate(values[:25]):
            if sum(bool(clean_text(x)) for x in row) >= 2:
                return idx
        return 0
    return best_idx


def _values_to_dataframe(values: list[list[str]]) -> pd.DataFrame:
    if not values:
        return pd.DataFrame()

    header_idx = _detect_header_row(values)
    raw_headers = [clean_text(x) for x in values[header_idx]]
    if not raw_headers:
        return pd.DataFrame()

    seen = {}
    headers = []
    for i, header in enumerate(raw_headers):
        base = header or f"column_{i+1}"
        count = seen.get(base, 0)
        seen[base] = count + 1
        headers.append(base if count == 0 else f"{base}_{count+1}")

    width = len(headers)
    rows = []
    for row in values[header_idx + 1:]:
        padded = list(row[:width]) + [""] * max(0, width - len(row))
        padded = padded[:width]
        if any(clean_text(x) for x in padded):
            rows.append(padded)

    return pd.DataFrame(rows, columns=headers)


def load_google_sheet(url: str, worksheet_name: str = "") -> pd.DataFrame:
    url = (url or "").strip()
    worksheet_name = (worksheet_name or "").strip()

    sheet_id = _sheet_id_from_url(url)
    if not sheet_id:
        raise ValueError("لينك Google Sheet غير صحيح.")

    if not google_user_oauth_configured():
        raise RuntimeError("Google OAuth Secrets ناقصة في Streamlit.")

    token = _access_token()
    title = _worksheet_title(sheet_id, token, worksheet_name, _gid_from_url(url))
    safe_title = title.replace("'", "''")
    a1_range = f"'{safe_title}'!A:ZZ"

    payload = _request_json(
        f"{SHEETS_API}/{sheet_id}/values/{quote(a1_range, safe='')}",
        token,
        params={"majorDimension": "ROWS", "valueRenderOption": "FORMATTED_VALUE"},
    )

    values = payload.get("values") or []
    if not values:
        raise RuntimeError(f'الـTab "{title}" فاضية.')

    df = _values_to_dataframe(values)
    if df.empty:
        raise RuntimeError(f'الـTab "{title}" اتقرت لكن مفيش جدول بيانات واضح.')
    return df


def load_uploaded_file(file) -> pd.DataFrame:
    name = file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(file)
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(file)
    raise ValueError("Supported files: CSV, XLSX, XLS")


def map_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename = {}
    for col in df.columns:
        key = _canon(col)
        for target, aliases in _CANON_ALIASES.items():
            if key in aliases:
                if target not in rename.values():
                    rename[col] = target
                break
    return df.rename(columns=rename)


def _parse_capacity_gb(value):
    text = clean_text(value).upper()
    if not text:
        return None
    number = parse_number(text)
    if number is None:
        return None
    if "TB" in text or "تيرا" in text:
        number *= 1024
    return float(number)



def _parse_price_egp(value):
    """
    Parse laptop prices robustly.

    The live sheet may store prices in "thousands of EGP", e.g.:
      37      -> 37,000 EGP
      37.5    -> 37,500 EGP
      49,5    -> 49,500 EGP
    while normal full prices such as 37,500 / 37500 stay unchanged.

    In a laptop inventory, a positive price below 1,000 EGP is treated as
    "thousands" because that is how this sheet represents selling prices.
    """
    text = clean_text(value)
    if not text or text.lower() in {"nan", "none", "null"}:
        return None

    s = (
        text.replace("EGP", "")
        .replace("egp", "")
        .replace("جنيه", "")
        .replace("ج.م", "")
        .strip()
    )

    explicit_thousands = bool(
        re.search(r"(?:\bK\b|الف|ألف)", s, flags=re.I)
    )
    s = re.sub(r"(?:\bK\b|الف|ألف)", "", s, flags=re.I).strip()

    # Arabic decimal separator.
    s = s.replace("٫", ".")

    # Handle comma intelligently:
    # 37,500 => 37500
    # 37,5   => 37.5
    # 1,250,000 => 1250000
    if "," in s or "،" in s:
        s = s.replace("،", ",")
        if re.fullmatch(r"-?\d{1,3}(?:,\d{3})+", s):
            s = s.replace(",", "")
        elif re.fullmatch(r"-?\d+,\d{1,2}", s):
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")

    match = re.search(r"-?\d+(?:\.\d+)?", s)
    if not match:
        return None

    number = float(match.group())

    if explicit_thousands:
        number *= 1000
    elif 0 < abs(number) < 1000:
        # The live laptop sheet stores e.g. 37 / 37.5 to mean 37k / 37.5k.
        number *= 1000

    return float(number)


def _parse_bool(value) -> bool:
    t = clean_text(value).lower()
    return t in {"1", "true", "yes", "y", "touch", "تاتش", "نعم", "اه", "أه", "ايوه", "أيوه"} or "touch" in t or "تاتش" in t


def _build_specs_from_columns(df: pd.DataFrame) -> pd.Series:
    preferred = ["cpu_direct", "ram_direct", "storage_direct", "gpu_direct", "vram_direct", "touch_direct"]
    excluded = {"model", "qty", "screen_inches", "price_egp", "camera", "specs"}

    columns = [c for c in preferred if c in df.columns]
    columns += [
        c for c in df.columns
        if c not in excluded and c not in columns
        and not df[c].map(clean_text).eq("").all()
    ]

    def make(row):
        parts = []
        for col in columns:
            value = clean_text(row.get(col))
            if value:
                label = str(col).replace("_direct", "").replace("_", " ")
                parts.append(f"{label}: {value}")
        return " | ".join(parts)

    return df.apply(make, axis=1)


def normalize_inventory(df: pd.DataFrame) -> Tuple[pd.DataFrame, list[str]]:
    warnings = []
    detected = [clean_text(c) for c in df.columns]
    df = map_columns(df.copy())

    if "model" not in df.columns:
        raise ValueError(
            "مش لاقي عمود الموديل. الأعمدة اللي اتقرت من الشيت: "
            + " | ".join(detected)
        )

    # specs is NEVER mandatory.
    if "specs" not in df.columns:
        df["specs"] = _build_specs_from_columns(df)
        warnings.append("تم تكوين المواصفات تلقائيًا من أعمدة الشيت؛ عمود specs مش مطلوب.")

    for col in ["qty", "screen_inches", "price_egp", "camera"]:
        if col not in df.columns:
            df[col] = None
            warnings.append(f"العمود {col} غير موجود؛ تم تركه فارغًا.")

    df["model"] = df["model"].map(clean_text)
    df["specs"] = df["specs"].map(clean_text)
    df["qty"] = df["qty"].map(parse_number).fillna(0).astype(int)
    df["screen_inches"] = df["screen_inches"].map(parse_number)

    # Keep the exact sheet value for diagnostics, then normalize to real EGP.
    df["price_raw"] = df["price_egp"].map(clean_text)
    parsed_prices = df["price_egp"].map(_parse_price_egp)

    scaled_count = 0
    for raw, parsed in zip(df["price_raw"], parsed_prices):
        raw_number = parse_number(raw)
        if (
            parsed is not None
            and raw_number is not None
            and 0 < abs(raw_number) < 1000
            and abs(parsed) >= 1000
        ):
            scaled_count += 1

    df["price_egp"] = parsed_prices
    if scaled_count:
        warnings.append(
            f"تم تحويل {scaled_count} سعر من صيغة الآلاف في الشيت "
            "(مثال 37.5 = 37,500 جنيه)."
        )

    df["camera"] = df["camera"].map(clean_text)

    df = df[(df["model"] != "") | (df["specs"] != "")].reset_index(drop=True)

    parsed = df.apply(
        lambda row: parse_specs(row["model"], row["specs"]),
        axis=1,
        result_type="expand",
    )
    for col in parsed.columns:
        df[col] = parsed[col]

    if "cpu_direct" in df.columns:
        direct = df["cpu_direct"].map(clean_text)
        df.loc[direct != "", "cpu"] = direct[direct != ""]

    if "ram_direct" in df.columns:
        direct = df["ram_direct"].map(_parse_capacity_gb)
        df.loc[direct.notna(), "ram_gb"] = direct[direct.notna()]

    if "storage_direct" in df.columns:
        direct = df["storage_direct"].map(_parse_capacity_gb)
        df.loc[direct.notna(), "storage_gb"] = direct[direct.notna()]

    if "gpu_direct" in df.columns:
        gp = df["gpu_direct"].map(lambda v: detect_gpu(clean_text(v).upper()) if clean_text(v) else ("", None))
        gpu = gp.map(lambda x: x[0])
        vram = gp.map(lambda x: x[1])
        df.loc[gpu != "", "gpu"] = gpu[gpu != ""]
        df.loc[vram.notna(), "gpu_vram_gb"] = vram[vram.notna()]

    if "vram_direct" in df.columns:
        direct = df["vram_direct"].map(_parse_capacity_gb)
        df.loc[direct.notna(), "gpu_vram_gb"] = direct[direct.notna()]

    if "touch_direct" in df.columns:
        df["touch"] = df["touch_direct"].map(_parse_bool)

    return df, warnings


def parse_specs(model: str, specs: str) -> dict:
    text = f"{model} {specs}".upper().replace("\\", " / ")
    text = re.sub(r"\s+", " ", text)

    touch = "TOUCH" in text or "X360" in text

    nums = [int(x) for x in re.findall(r"(?<!\d)(4|8|16|24|32|48|64|128|256|512|1024|2048)(?!\d)", clean_text(specs).upper())]
    ram = None
    storage = None
    ram_candidates = [n for n in nums if n in {4, 8, 16, 24, 32, 48, 64, 128}]
    storage_candidates = [n for n in nums if n in {128, 256, 512, 1024, 2048}]
    if ram_candidates:
        ram = ram_candidates[0]
    if storage_candidates:
        storage = storage_candidates[-1]
        if ram == 128 and len(ram_candidates) > 1:
            ram = ram_candidates[1]

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
        r"(CORE\s*ULTRA\s*[579]\s*\d*[A-Z]*)",
        r"(ULTRA\s*[579]\s*\d*[A-Z]*)",
        r"(I[3579][ -]?\d{4,5}[A-Z]{0,3})",
        r"(I[3579]\s+\d{1,2}TH)",
        r"(RYZEN\s*[3579]\s*PRO\s*\d{4}[A-Z]*)",
        r"(R[3579]\s*PRO\s*\d{4}[A-Z]*)",
        r"(RYZEN\s*[3579]\s*\d{4}[A-Z]*)",
        r"(CELERON\s*[A-Z]?\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip()
    return "Unknown"


def detect_gpu(text: str):
    patterns = [
        (r"(RTX\s*A5500)", None),
        (r"(RTX\s*A5000)", None),
        (r"(RTX\s*A4500)", None),
        (r"(RTX\s*A4000)", None),
        (r"(RTX\s*A3000)", None),
        (r"(RTX\s*A2000)", None),
        (r"(RTX\s*A1000)", None),
        (r"(RTX\s*A500)", None),
        (r"(RTX\s*4090)", None),
        (r"(RTX\s*4080)", None),
        (r"(RTX\s*4070)", None),
        (r"(RTX\s*4060)", None),
        (r"(RTX\s*4050)", None),
        (r"(RTX\s*3080)", None),
        (r"(RTX\s*3070)", None),
        (r"(RTX\s*3060)", None),
        (r"(RTX\s*3050)", None),
        (r"(QUADRO\s*P1000)", None),
        (r"\b(T2000|T1200|T1000|T600)\b", None),
        (r"\b(A5500|A5000|A4500|A4000|A3000|A2000|A1000|A500)\b", None),
        (r"(IRIS\s*XE)", 0),
        (r"(IRIS\s*PLUS)", 0),
        (r"(UHD\s*GRAPHICS)", 0),
        (r"(RADEON\s*GRAPHICS)", 0),
        (r"(AMD\s*VGA)", None),
    ]

    gpu = "Integrated / Unknown"
    default_vram = None
    for pattern, value in patterns:
        match = re.search(pattern, text)
        if match:
            gpu = re.sub(r"\s+", " ", match.group(1)).strip()
            default_vram = value
            break

    vram = default_vram
    memories = re.findall(r"(?<!\d)(2|4|6|8|12|16|24)\s*G(?:B)?\b", text)
    if memories and gpu not in {"IRIS XE", "IRIS PLUS", "UHD GRAPHICS", "RADEON GRAPHICS"}:
        vram = int(memories[-1])

    return gpu, vram


def schema_debug(df: pd.DataFrame) -> str:
    return " | ".join(str(c) for c in df.columns)
