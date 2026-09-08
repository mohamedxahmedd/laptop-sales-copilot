
import re
from typing import Optional

ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

def clean_text(value) -> str:
    if value is None:
        return ""
    return str(value).translate(ARABIC_DIGITS).strip()

def parse_number(value) -> Optional[float]:
    if value is None:
        return None
    s = clean_text(value)
    if not s or s.lower() in {"nan", "none", "null"}:
        return None
    s = s.replace("EGP", "").replace("egp", "").replace("جنيه", "")
    s = s.replace("،", "").replace(",", "").replace("٫", ".")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None

def money(value) -> str:
    if value is None:
        return "السعر غير مسجل"
    try:
        if value != value:
            return "السعر غير مسجل"
    except Exception:
        pass
    return f"{int(round(float(value))):,} جنيه"

def clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, x))
