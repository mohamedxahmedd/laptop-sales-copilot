from __future__ import annotations
import math
import re
from typing import Dict, List, Tuple
import pandas as pd

from .utils import clamp, money

CASE_AR = {
    "gaming": "جيمينج",
    "programming": "برمجة",
    "engineering": "برامج هندسية",
    "architecture": "عمارة و3D",
    "video_editing": "مونتاج",
    "photoshop_design": "فوتوشوب وجرافيك",
    "ai_ml": "AI / Machine Learning",
    "office": "شغل مكتبي",
    "general": "استخدام عام",
}

# Targets represent "enough for a good experience", not "the strongest possible".
BASE_NEEDS = {
    "office":            {"cpu": 44, "gpu": 10, "ram": 8,  "storage": 256, "vram": 0, "nvidia": False},
    "general":           {"cpu": 52, "gpu": 15, "ram": 8,  "storage": 256, "vram": 0, "nvidia": False},
    "programming":       {"cpu": 62, "gpu": 18, "ram": 16, "storage": 512, "vram": 0, "nvidia": False},
    "photoshop_design":  {"cpu": 60, "gpu": 25, "ram": 16, "storage": 512, "vram": 0, "nvidia": False},
    "engineering":       {"cpu": 68, "gpu": 48, "ram": 16, "storage": 512, "vram": 4, "nvidia": False},
    "architecture":      {"cpu": 72, "gpu": 60, "ram": 16, "storage": 512, "vram": 4, "nvidia": False},
    "video_editing":     {"cpu": 70, "gpu": 58, "ram": 16, "storage": 512, "vram": 4, "nvidia": False},
    "gaming":            {"cpu": 66, "gpu": 64, "ram": 16, "storage": 512, "vram": 4, "nvidia": False},
    "ai_ml":             {"cpu": 70, "gpu": 80, "ram": 16, "storage": 512, "vram": 6, "nvidia": True},
}

SOFTWARE_NEEDS = {
    "VS Code / Web":    {"cpu": 56, "gpu": 12, "ram": 16, "storage": 512, "vram": 0},
    "Visual Studio":    {"cpu": 62, "gpu": 16, "ram": 16, "storage": 512, "vram": 0},
    "Android Studio":   {"cpu": 68, "gpu": 20, "ram": 16, "storage": 512, "vram": 0},
    "Flutter":          {"cpu": 64, "gpu": 18, "ram": 16, "storage": 512, "vram": 0},
    "Docker":           {"cpu": 68, "gpu": 12, "ram": 24, "storage": 512, "vram": 0},
    "AutoCAD":          {"cpu": 62, "gpu": 30, "ram": 16, "storage": 512, "vram": 2},
    "SolidWorks":       {"cpu": 72, "gpu": 55, "ram": 16, "storage": 512, "vram": 4},
    "Revit":            {"cpu": 72, "gpu": 50, "ram": 16, "storage": 512, "vram": 4},
    "Lumion":           {"cpu": 75, "gpu": 78, "ram": 16, "storage": 512, "vram": 6, "nvidia": True},
    "3ds Max":          {"cpu": 74, "gpu": 66, "ram": 16, "storage": 512, "vram": 4},
    "SketchUp":         {"cpu": 62, "gpu": 36, "ram": 16, "storage": 512, "vram": 2},
    "Enscape":          {"cpu": 72, "gpu": 75, "ram": 16, "storage": 512, "vram": 6, "nvidia": True},
    "V-Ray":            {"cpu": 76, "gpu": 72, "ram": 32, "storage": 512, "vram": 6},
    "ANSYS":            {"cpu": 78, "gpu": 46, "ram": 32, "storage": 512, "vram": 4},
    "MATLAB":           {"cpu": 68, "gpu": 20, "ram": 16, "storage": 512, "vram": 0},
    "CATIA":            {"cpu": 72, "gpu": 52, "ram": 16, "storage": 512, "vram": 4},
    "Inventor":         {"cpu": 70, "gpu": 48, "ram": 16, "storage": 512, "vram": 4},
    "Civil 3D":         {"cpu": 70, "gpu": 45, "ram": 16, "storage": 512, "vram": 4},
    "Premiere Pro":     {"cpu": 70, "gpu": 60, "ram": 16, "storage": 512, "vram": 4},
    "After Effects":    {"cpu": 78, "gpu": 54, "ram": 32, "storage": 512, "vram": 4},
    "DaVinci Resolve":  {"cpu": 72, "gpu": 78, "ram": 16, "storage": 512, "vram": 6},
    "Photoshop":        {"cpu": 60, "gpu": 24, "ram": 16, "storage": 512, "vram": 0},
    "Illustrator":      {"cpu": 56, "gpu": 16, "ram": 16, "storage": 512, "vram": 0},
    "Lightroom":        {"cpu": 62, "gpu": 22, "ram": 16, "storage": 512, "vram": 0},
    "PyTorch":          {"cpu": 70, "gpu": 84, "ram": 32, "storage": 512, "vram": 8, "nvidia": True},
    "TensorFlow":       {"cpu": 70, "gpu": 84, "ram": 32, "storage": 512, "vram": 8, "nvidia": True},
    "Stable Diffusion": {"cpu": 68, "gpu": 88, "ram": 32, "storage": 512, "vram": 8, "nvidia": True},
    "CUDA":             {"cpu": 68, "gpu": 82, "ram": 16, "storage": 512, "vram": 6, "nvidia": True},
}

def _intel_generation(cpu: str):
    t = (cpu or "").upper()
    m = re.search(r"\bI[3579][ -]?(\d{4,5})", t)
    if not m:
        return None
    n = m.group(1)
    # 12800 -> 12th, 11850 -> 11th, 1035 -> 10th, 8850 -> 8th, 6820 -> 6th
    if len(n) == 5:
        return int(n[:2])
    if n.startswith(("10", "11", "12", "13", "14")):
        return int(n[:2])
    return int(n[0])

def cpu_score(cpu: str) -> float:
    t = (cpu or "").upper()
    if "UNKNOWN" in t:
        return 34
    if "ULTRA 9" in t: base = 96
    elif "ULTRA 7" in t: base = 90
    elif "ULTRA 5" in t: base = 82
    elif re.search(r"\bI9\b", t): base = 82
    elif re.search(r"\bI7\b", t): base = 69
    elif re.search(r"\bI5\b", t): base = 55
    elif "RYZEN 9" in t or re.search(r"\bR9\b", t): base = 88
    elif "RYZEN 7" in t or re.search(r"\bR7\b", t): base = 72
    elif "RYZEN 5" in t or re.search(r"\bR5\b", t): base = 57
    elif "CELERON" in t: base = 18
    else: base = 43

    gen = _intel_generation(t)
    if gen:
        base += {14: 14, 13: 12, 12: 10, 11: 7, 10: 4, 9: 2, 8: 0, 7: -3, 6: -5}.get(gen, 0)

    # AMD family bump
    nums = [int(x) for x in re.findall(r"\b([35678]\d{3})[A-Z]*\b", t)]
    if nums and ("RYZEN" in t or re.search(r"\bR[3579]\b", t)):
        n = max(nums)
        if n >= 7000: base += 12
        elif n >= 6000: base += 10
        elif n >= 5000: base += 7
        elif n >= 4000: base += 3
        elif n >= 3000: base -= 1

    if "HK" in t: base += 7
    elif re.search(r"\dH\b", t) or re.search(r"\bH\b", t): base += 5
    elif re.search(r"\dP\b", t) or re.search(r"\bP\b", t): base += 1
    elif re.search(r"\dU\b", t) or re.search(r"\bU\b", t): base -= 3

    return clamp(base)

def gpu_score(gpu: str, vram) -> float:
    t = (gpu or "").upper()
    mapping = [
        ("A4000", 96), ("RTX 3060", 91), ("A2000", 82), ("A1000", 68),
        ("A500", 52), ("T1200", 55), ("T1000", 49), ("T600", 42),
        ("P1000", 36), ("IRIS XE", 25), ("IRIS PLUS", 19),
        ("RADEON GRAPHICS", 22), ("UHD", 12), ("INTEGRATED", 10),
    ]
    score = 28
    for key, val in mapping:
        if key in t:
            score = val
            break
    if vram and not any(k in t for k in ["IRIS", "UHD", "RADEON GRAPHICS", "INTEGRATED"]):
        score += min(10, max(0, (float(vram) - 4) * 2.5))
    return clamp(score)

def ram_score(ram) -> float:
    if not ram: return 20
    ram = float(ram)
    if ram >= 64: return 100
    if ram >= 32: return 90
    if ram >= 24: return 82
    if ram >= 16: return 72
    if ram >= 8: return 48
    return 25

def storage_score(storage) -> float:
    if not storage: return 25
    storage = float(storage)
    if storage >= 2048: return 100
    if storage >= 1024: return 90
    if storage >= 512: return 76
    if storage >= 256: return 52
    return 32

def _merge_need(dst: Dict, src: Dict):
    for k in ("cpu", "gpu", "ram", "storage", "vram"):
        if k in src and src[k] is not None:
            dst[k] = max(dst.get(k, 0), src[k])
    if src.get("nvidia"):
        dst["nvidia"] = True

def infer_need_profile(req: Dict) -> Dict:
    cases = req.get("use_cases") or ["general"]
    need = {"cpu": 0, "gpu": 0, "ram": 0, "storage": 0, "vram": 0, "nvidia": False}

    for case in cases:
        _merge_need(need, BASE_NEEDS.get(case, BASE_NEEDS["general"]))

    for software in req.get("software") or []:
        if software in SOFTWARE_NEEDS:
            _merge_need(need, SOFTWARE_NEEDS[software])

    level = req.get("workload_level", "balanced")
    if level == "light":
        need["cpu"] = max(40, need["cpu"] - 8)
        need["gpu"] = max(10, need["gpu"] - 10)
        if "ai_ml" not in cases and not any(x in (req.get("software") or []) for x in ["After Effects", "ANSYS", "PyTorch", "TensorFlow", "Stable Diffusion"]):
            need["ram"] = min(need["ram"], 16)
    elif level == "heavy":
        need["cpu"] = min(100, need["cpu"] + 7)
        need["gpu"] = min(100, need["gpu"] + 8)
        need["ram"] = max(need["ram"], 24)
    elif level == "extreme":
        need["cpu"] = min(100, need["cpu"] + 12)
        need["gpu"] = min(100, need["gpu"] + 12)
        need["ram"] = max(need["ram"], 32)

    if req.get("ram_min"):
        need["ram"] = max(need["ram"], int(req["ram_min"]))
    if req.get("wants_nvidia"):
        need["nvidia"] = True

    return need

def _ram_capacity_score(ram):
    if ram is None or (isinstance(ram, float) and math.isnan(ram)):
        return 0
    return float(ram)

def _storage_capacity_score(storage):
    if storage is None or (isinstance(storage, float) and math.isnan(storage)):
        return 0
    return float(storage)

def _sufficiency(actual: float, target: float) -> float:
    """
    Saturates at 100 once the requirement is met.
    This is the key behavior that stops the strongest laptop winning automatically.
    """
    if target <= 0:
        return 100.0
    if actual >= target:
        return 100.0
    ratio = max(0.0, actual / target)
    return 100.0 * (ratio ** 1.7)

def _capacity_sufficiency(actual: float, target: float) -> float:
    if target <= 0:
        return 100
    if actual >= target:
        return 100
    return 100 * ((max(0, actual) / target) ** 1.9)

def _is_integrated_gpu(gpu: str) -> bool:
    t = (gpu or "").upper()
    return any(x in t for x in ["IRIS", "UHD", "RADEON GRAPHICS", "INTEGRATED", "UNKNOWN"])

def canonical_gpu_name(value: str) -> str:
    t = (value or "").upper().replace("NVIDIA", "").replace("GEFORCE", "").replace("QUADRO", "")
    t = re.sub(r"\s+", " ", t).strip()
    m = re.search(r"\bA\s*(500|1000|2000|3000|4000|4500|5000|5500)\b", t)
    if m: return f"A{m.group(1)}"
    m = re.search(r"\bRTX\s*(2050|2060|2070|2080|3050|3060|3070|3080|4050|4060|4070|4080|4090)\b", t)
    if m: return f"RTX {m.group(1)}"
    m = re.search(r"\b(P1000|T600|T1000|T1200|T2000)\b", t)
    if m: return m.group(1)
    return re.sub(r"[^A-Z0-9]+", "", t)

def constraint_summary(req: Dict) -> list[str]:
    parts = []
    if req.get("gpu_model_exact"):
        g = req["gpu_model_exact"]
        if req.get("gpu_vram_exact_gb"): g += f" {int(req['gpu_vram_exact_gb'])}GB"
        parts.append(f"GPU: {g}")
    if req.get("ram_exact_gb"): parts.append(f"RAM: {int(req['ram_exact_gb'])}GB")
    elif req.get("ram_min"): parts.append(f"RAM ≥ {int(req['ram_min'])}GB")
    if req.get("storage_exact_gb"): parts.append(f"SSD: {int(req['storage_exact_gb'])}GB")
    elif req.get("storage_min_gb"): parts.append(f"SSD ≥ {int(req['storage_min_gb'])}GB")
    if req.get("screen_inches"): parts.append(f'Screen: {req["screen_inches"]:g}"')
    if req.get("wants_touch"): parts.append("Touch")
    if req.get("budget_max"): parts.append(f"Budget ≤ {money(req['budget_max'])}")
    return parts

def hard_filter(df: pd.DataFrame, req: Dict, use_stretch=False) -> pd.DataFrame:
    out = df[df["qty"] > 0].copy()

    if req.get("gpu_model_exact"):
        wanted = canonical_gpu_name(req["gpu_model_exact"])
        out = out[out["gpu"].map(canonical_gpu_name) == wanted]
    if req.get("gpu_vram_exact_gb") is not None:
        out = out[out["gpu_vram_gb"].fillna(-1).astype(float) == float(req["gpu_vram_exact_gb"])]

    if req.get("ram_exact_gb") is not None:
        out = out[out["ram_gb"].fillna(-1).astype(float) == float(req["ram_exact_gb"])]
    elif req.get("ram_min"):
        out = out[out["ram_gb"].fillna(0).astype(float) >= float(req["ram_min"])]

    if req.get("storage_exact_gb") is not None:
        out = out[out["storage_gb"].fillna(-1).astype(float) == float(req["storage_exact_gb"])]
    elif req.get("storage_min_gb"):
        out = out[out["storage_gb"].fillna(0).astype(float) >= float(req["storage_min_gb"])]

    if req.get("screen_inches"):
        target = float(req["screen_inches"])
        out = out[(out["screen_inches"].fillna(-99) - target).abs() <= 0.6]
    if req.get("wants_touch"):
        out = out[out["touch"] == True]
    if req.get("wants_nvidia") and not req.get("gpu_model_exact"):
        out = out[~out["gpu"].map(_is_integrated_gpu)]

    bmin = req.get("budget_min")
    bmax = req.get("budget_stretch") if use_stretch and req.get("budget_stretch") else req.get("budget_max")
    if bmin is not None:
        out = out[out["price_egp"].notna() & (out["price_egp"] >= bmin)]
    if bmax is not None:
        out = out[out["price_egp"].notna() & (out["price_egp"] <= bmax)]
    return out

def _price_score(price, budget_max, candidate_prices) -> float:
    if price is None or pd.isna(price):
        return 30

    p = float(price)
    if budget_max:
        # Cheap enough is rewarded, but not so heavily that an underpowered device wins.
        ratio = min(1.0, p / float(budget_max))
        return 100 - (ratio * 38)  # 62 at the full budget, 81 at half budget

    valid = [float(x) for x in candidate_prices if pd.notna(x)]
    if len(valid) < 2:
        return 70
    lo, hi = min(valid), max(valid)
    if hi <= lo:
        return 70
    return 100 - ((p - lo) / (hi - lo)) * 55

def _overkill_penalty(c, g, ram, storage, need, price, candidate_prices) -> float:
    # Hardware above the target gives no fit bonus. Very large excess + high price gets a small penalty.
    cpu_excess = max(0, c - need["cpu"])
    gpu_excess = max(0, g - need["gpu"])
    ram_excess = max(0, (ram or 0) - need["ram"])
    penalty = min(10, cpu_excess * 0.035 + gpu_excess * 0.055 + ram_excess * 0.08)

    valid = [float(x) for x in candidate_prices if pd.notna(x)]
    if price is not None and pd.notna(price) and valid:
        median = sorted(valid)[len(valid)//2]
        if float(price) > median * 1.35:
            penalty += 4
    return penalty

def rank_inventory(df: pd.DataFrame, req: Dict, top_n=5) -> Tuple[pd.DataFrame, Dict]:
    meta = {
        "used_stretch": False,
        "no_exact": False,
        "need_profile": infer_need_profile(req),
        "strict_hardware": bool(req.get("strict_hardware")),
        "explicit_constraints": req.get("explicit_constraints") or [],
    }

    filtered = hard_filter(df, req, use_stretch=False)

    # Only use extra budget if the customer explicitly allowed it.
    if filtered.empty and req.get("budget_stretch"):
        filtered = hard_filter(df, req, use_stretch=True)
        meta["used_stretch"] = not filtered.empty

    if filtered.empty:
        meta["no_exact"] = True
        return filtered, meta

    need = meta["need_profile"]
    prices = filtered["price_egp"].tolist()
    budget_for_score = req.get("budget_max") or (req.get("budget_stretch") if meta["used_stretch"] else None)

    scored_rows = []
    for idx, r in filtered.iterrows():
        c = cpu_score(r["cpu"])
        g = gpu_score(r["gpu"], r["gpu_vram_gb"])
        ram = _ram_capacity_score(r["ram_gb"])
        storage = _storage_capacity_score(r["storage_gb"])
        vram = float(r["gpu_vram_gb"]) if pd.notna(r["gpu_vram_gb"]) and r["gpu_vram_gb"] else 0.0

        cpu_fit = _sufficiency(c, need["cpu"])
        gpu_fit = _sufficiency(g, need["gpu"])
        ram_fit = _capacity_sufficiency(ram, need["ram"])
        storage_fit = _capacity_sufficiency(storage, need["storage"])
        vram_fit = _capacity_sufficiency(vram, need["vram"]) if need["vram"] else 100

        cases = req.get("use_cases") or ["general"]
        if "gaming" in cases or "ai_ml" in cases or "architecture" in cases:
            weights = {"cpu": .24, "gpu": .36, "ram": .18, "storage": .08, "vram": .14}
        elif "video_editing" in cases or "engineering" in cases:
            weights = {"cpu": .29, "gpu": .31, "ram": .20, "storage": .09, "vram": .11}
        elif "programming" in cases:
            weights = {"cpu": .38, "gpu": .08, "ram": .34, "storage": .16, "vram": .04}
        elif "photoshop_design" in cases:
            weights = {"cpu": .34, "gpu": .14, "ram": .28, "storage": .18, "vram": .06}
        else:
            weights = {"cpu": .34, "gpu": .08, "ram": .28, "storage": .24, "vram": .06}

        fit = (
            cpu_fit * weights["cpu"] +
            gpu_fit * weights["gpu"] +
            ram_fit * weights["ram"] +
            storage_fit * weights["storage"] +
            vram_fit * weights["vram"]
        )

        # Strong penalty if NVIDIA is genuinely required by the workload.
        nvidia_penalty = 0
        if need.get("nvidia") and _is_integrated_gpu(r["gpu"]):
            nvidia_penalty = 28

        price_fit = _price_score(r["price_egp"], budget_for_score, prices)
        overkill = _overkill_penalty(c, g, ram, storage, need, r["price_egp"], prices)

        # Fit dominates, but after a machine is "enough", price/value determines the winner.
        total = fit * 0.78 + price_fit * 0.22 - overkill - nvidia_penalty

        meets = (
            cpu_fit >= 86 and
            gpu_fit >= 82 and
            ram_fit >= 82 and
            storage_fit >= 72 and
            vram_fit >= 75 and
            nvidia_penalty == 0
        )

        scored_rows.append({
            "idx": idx,
            "match_score": clamp(total),
            "fit_score": fit,
            "meets_needs": bool(meets),
            "cpu_fit": cpu_fit,
            "gpu_fit": gpu_fit,
            "ram_fit": ram_fit,
            "price_fit": price_fit,
        })

    scored = pd.DataFrame(scored_rows).set_index("idx")
    for col in scored.columns:
        filtered[col] = filtered.index.map(scored[col])

    ordered = filtered.sort_values(
        ["meets_needs", "match_score", "price_egp"],
        ascending=[False, False, True],
    )

    if req.get("strict_hardware"):
        return ordered.head(min(top_n, 6)).copy(), meta

    best = ordered.iloc[0]
    picks = [ordered.index[0]]

    others = ordered.drop(index=picks, errors="ignore")
    if not others.empty and pd.notna(best["price_egp"]):
        value_pool = others[
            (others["fit_score"] >= float(best["fit_score"]) - 8) &
            (others["price_egp"].notna()) &
            (others["price_egp"] <= float(best["price_egp"]) * 0.90)
        ]
        if not value_pool.empty:
            picks.append(value_pool.sort_values(["price_egp", "match_score"], ascending=[True, False]).index[0])

    others = ordered.drop(index=picks, errors="ignore")
    while len(picks) < min(3, top_n) and not others.empty:
        idx = others.index[0]
        if float(others.loc[idx, "match_score"]) < float(best["match_score"]) - 6:
            break
        picks.append(idx)
        others = others.drop(index=[idx])

    return ordered.loc[picks].copy(), meta

def need_summary(req: Dict, need: Dict) -> str:
    cases = " + ".join(CASE_AR.get(c, c) for c in (req.get("use_cases") or ["general"]))
    sw = req.get("software") or []
    level_ar = {
        "light": "خفيف",
        "balanced": "متوسط / طبيعي",
        "heavy": "تقيل",
        "extreme": "تقيل جدًا",
    }.get(req.get("workload_level", "balanced"), "متوسط / طبيعي")

    bits = [f"الاستخدام: {cases}", f"الحمل: {level_ar}"]
    if sw:
        bits.append("البرامج: " + "، ".join(sw))
    bits.append(f"المستهدف: RAM {int(need['ram'])}GB")
    if need["gpu"] >= 45:
        bits.append("كارت شاشة منفصل مهم")
    elif need["gpu"] <= 25:
        bits.append("مش محتاج تدفع زيادة في كارت شاشة قوي")
    return " | ".join(bits)

def reason_for(row, req: Dict, need: Dict | None = None) -> str:
    need = need or infer_need_profile(req)
    cases = req.get("use_cases", ["general"])
    labels = " + ".join(CASE_AR.get(c, c) for c in cases)

    parts = [f"مناسب لـ {labels}"]
    if req.get("software"):
        parts.append("خصوصًا " + "، ".join(req["software"][:3]))

    if row.get("cpu") and row["cpu"] != "Unknown":
        parts.append(f"بروسيسور {row['cpu']}")
    if row.get("ram_gb"):
        parts.append(f"رام {int(row['ram_gb'])}GB")

    gpu = row.get("gpu")
    if gpu and "Integrated / Unknown" not in gpu:
        v = row.get("gpu_vram_gb")
        gpu_txt = f"{gpu}" + (f" {int(v)}GB" if pd.notna(v) and v else "")
        parts.append(f"كارت {gpu_txt}")

    if need["gpu"] <= 25 and gpu_score(row.get("gpu"), row.get("gpu_vram_gb")) > 55:
        parts.append("لكن كارت الشاشة أقوى من المطلوب شوية")

    if row.get("price_egp") is not None and pd.notna(row["price_egp"]):
        parts.append(f"بسعر {money(row['price_egp'])}")

    return "، ".join(parts) + "."

def specs_line(row) -> str:
    parts = []
    if row.get("cpu") and row["cpu"] != "Unknown":
        parts.append(str(row["cpu"]))
    if row.get("ram_gb") and pd.notna(row["ram_gb"]):
        parts.append(f"RAM {int(row['ram_gb'])}GB")
    if row.get("storage_gb") and pd.notna(row["storage_gb"]):
        parts.append(f"SSD {int(row['storage_gb'])}GB")
    if row.get("gpu") and row["gpu"] != "Integrated / Unknown":
        gpu = str(row["gpu"])
        if row.get("gpu_vram_gb") and pd.notna(row["gpu_vram_gb"]):
            gpu += f" {int(row['gpu_vram_gb'])}GB"
        parts.append(gpu)
    if row.get("screen_inches") and pd.notna(row["screen_inches"]):
        parts.append(f'{int(row["screen_inches"])}"')
    if row.get("touch"):
        parts.append("Touch")
    return " | ".join(parts)
