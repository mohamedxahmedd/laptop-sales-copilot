from __future__ import annotations
import json
import re
from typing import Dict, List

from .utils import clean_text

USE_CASE_KEYWORDS = {
    "gaming": [
        "gaming", "جيمينج", "العاب", "ألعاب", "game", "games", "valorant", "warzone",
        "fortnite", "gta", "فيفا", "fc 25", "pubg", "ببجي"
    ],
    "programming": [
        "programming", "coding", "developer", "development", "برمجه", "برمجة", "مطور", "برامج برمجه", "برامج برمجة",
        "flutter", "android studio", "visual studio", "vscode", "vs code", "web development",
        "backend", "frontend", "docker", "برامج برمجة"
    ],
    "engineering": [
        "engineering", "مهندس", "هندسه", "هندسة", "هندسيه", "هندسية", "برامج هندسيه", "برامج هندسية", "solidworks", "solid works", "autocad", "auto cad",
        "ansys", "matlab", "catia", "inventor", "civil 3d"
    ],
    "architecture": [
        "architecture", "architect", "عماره", "عمارة", "معماري", "معماريه", "معمارية", "revit", "lumion", "3ds max", "3d max",
        "sketchup", "enscape", "vray", "v-ray"
    ],
    "video_editing": [
        "video editing", "editing", "مونتاج", "premiere", "after effects", "aftereffect",
        "davinci", "resolve", "4k", "فيديو"
    ],
    "photoshop_design": [
        "photoshop", "فوتوشوب", "illustrator", "graphic design", "جرافيك", "تصميم", "lightroom"
    ],
    "ai_ml": [
        "machine learning", "deep learning", "ai", "ml", "ذكاء اصطناعي", "cuda", "pytorch",
        "tensorflow", "stable diffusion", "llm", "data science"
    ],
    "office": [
        "office", "word", "excel", "powerpoint", "اوفيس", "أوفيس", "شغل مكتبي", "تصفح", "zoom",
        "محاسبه", "محاسبة"
    ],
}

SOFTWARE_ALIASES = {
    "VS Code / Web": ["vscode", "vs code", "web development", "frontend", "backend", "برمجة ويب"],
    "Visual Studio": ["visual studio"],
    "Android Studio": ["android studio"],
    "Flutter": ["flutter"],
    "Docker": ["docker"],
    "AutoCAD": ["autocad", "auto cad"],
    "SolidWorks": ["solidworks", "solid works"],
    "Revit": ["revit"],
    "Lumion": ["lumion"],
    "3ds Max": ["3ds max", "3d max"],
    "SketchUp": ["sketchup"],
    "Enscape": ["enscape"],
    "V-Ray": ["v-ray", "vray"],
    "ANSYS": ["ansys"],
    "MATLAB": ["matlab"],
    "CATIA": ["catia"],
    "Inventor": ["inventor"],
    "Civil 3D": ["civil 3d"],
    "Premiere Pro": ["premiere"],
    "After Effects": ["after effects", "aftereffect"],
    "DaVinci Resolve": ["davinci", "resolve"],
    "Photoshop": ["photoshop", "فوتوشوب"],
    "Illustrator": ["illustrator"],
    "Lightroom": ["lightroom"],
    "PyTorch": ["pytorch"],
    "TensorFlow": ["tensorflow"],
    "Stable Diffusion": ["stable diffusion"],
    "CUDA": ["cuda"],
}

def _normalize(s: str) -> str:
    s = clean_text(s).lower()
    s = s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    s = s.replace("ة", "ه")
    return s

def _extract_numbers(text: str):
    text = text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    vals = []
    for m in re.finditer(r"(?<!\d)(\d{1,6}(?:[.,]\d+)?)(?!\d)", text):
        raw = m.group(1).replace(",", "")
        try:
            vals.append(float(raw))
        except Exception:
            pass
    return vals

def extract_budget(text: str):
    t = _normalize(text)
    nums = _extract_numbers(t)
    budget_context = any(k in t for k in [
        "ميزاني", "budget", "سعر", "جنيه", "الف", "k", "حدود", "رينج", "range", "معايا"
    ])
    if not budget_context:
        return None, None, None

    scale_thousands = ("الف" in t or re.search(r"\d+\s*k\b", t) is not None)
    vals = []
    for n in nums:
        if scale_thousands and n < 1000:
            n *= 1000
        if n >= 5000:
            vals.append(int(n))

    if not vals:
        return None, None, None

    # "20 لـ 25 ألف"
    if len(vals) >= 2 and any(w in t for w in ["من", "لحد", "الى", "الي", "بين", "range", "-", " لـ ", " ل "]):
        a, b = vals[0], vals[1]
        return min(a, b), max(a, b), None

    target = vals[0]

    # Explicit stretch: "ممكن أزود 3000" or "لحد 28"
    stretch = None
    extra_match = re.search(r"(?:ازود|أزود|زيادة|زياده)\s*(\d+(?:[.,]\d+)?)", text)
    if extra_match:
        extra = float(extra_match.group(1).replace(",", ""))
        if "الف" in t and extra < 1000:
            extra *= 1000
        stretch = int(target + extra)

    return None, target, stretch

def detect_use_cases(text: str) -> List[str]:
    t = _normalize(text)
    hits = []
    for case, words in USE_CASE_KEYWORDS.items():
        if any(_normalize(w) in t for w in words):
            hits.append(case)
    return hits or ["general"]

def detect_software(text: str) -> List[str]:
    t = _normalize(text)
    found = []
    for name, aliases in SOFTWARE_ALIASES.items():
        if any(_normalize(a) in t for a in aliases):
            found.append(name)
    return found

def detect_workload_level(text: str) -> str:
    t = _normalize(text)
    if any(k in t for k in [
        "تقيل جدا", "تقيلة جدا", "احترافي جدا", "professional heavy", "8k", "مشاريع ضخمه",
        "مشاريع ضخمة", "ريندر تقيل جدا", "heavy rendering", "extreme"
    ]):
        return "extreme"
    if any(k in t for k in [
        "تقيل", "تقيله", "تقيلة", "احترافي", "professional", "4k", "ريندر", "render",
        "مشاريع كبيره", "مشاريع كبيرة", "heavy", "virtual machine", "vms"
    ]):
        return "heavy"
    if any(k in t for k in [
        "خفيف", "خفيفه", "خفيفة", "بسيط", "بسيطه", "بسيطة", "طالب", "student",
        "تعلم", "learning", "basic", "light"
    ]):
        return "light"
    return "balanced"

GPU_PATTERNS = [
    (r"\b(?:NVIDIA\s+)?RTX\s*A\s*(5500|5000|4500|4000|3000|2000|1000|500)\b", "A"),
    (r"\b(?:NVIDIA\s+)?RTX\s*(2050|2060|2070|2080|3050|3060|3070|3080|4050|4060|4070|4080|4090)\b", "RTX"),
    (r"\b(?:NVIDIA\s+)?(?:QUADRO\s+)?P\s*(1000)\b", "P"),
    (r"\bT\s*(600|1000|1200|2000)\b", "T"),
    (r"\bA\s*(5500|5000|4500|4000|3000|2000|1000|500)\b", "A"),
]

def _extract_gpu_exact(text: str):
    t = clean_text(text).upper()
    for pattern, prefix in GPU_PATTERNS:
        m = re.search(pattern, t, flags=re.I)
        if not m:
            continue
        n = m.group(1)
        return (f"RTX {n}" if prefix == "RTX" else f"{prefix}{n}"), m.span()
    return None, None

def extract_explicit_constraints(text: str) -> Dict:
    """Deterministic exact-spec extraction. These constraints override the LLM."""
    t = _normalize(text)
    upper = clean_text(text).upper()
    out = {
        "gpu_model_exact": None,
        "gpu_vram_exact_gb": None,
        "ram_exact_gb": None,
        "ram_min": None,
        "storage_exact_gb": None,
        "storage_min_gb": None,
        "strict_hardware": False,
        "explicit_constraints": [],
    }

    gpu, span = _extract_gpu_exact(text)
    if gpu:
        out["gpu_model_exact"] = gpu
        out["strict_hardware"] = True
        out["explicit_constraints"].append(f"GPU = {gpu}")
        near = upper[max(0, span[0]-12): min(len(upper), span[1]+24)]
        vm = re.search(r"(?<!\d)(2|4|6|8|12|16|24)\s*G(?:B)?\b", near)
        if vm:
            out["gpu_vram_exact_gb"] = int(vm.group(1))
            out["explicit_constraints"].append(f"VRAM = {int(vm.group(1))}GB")

    ram_patterns = [
        r"(?:ram|رام|رامات)\s*(?:=|:)?\s*(8|16|24|32|48|64|128)\s*(?:gb|g|جيجا)?",
        r"(?<!\d)(8|16|24|32|48|64|128)\s*(?:gb|g|جيجا)?\s*(?:ram|رام|رامات)",
    ]
    for pat in ram_patterns:
        m = re.search(pat, t, flags=re.I)
        if m:
            val = int(m.group(1))
            if any(k in t for k in ["على الاقل", "علي الاقل", "at least", "minimum"]):
                out["ram_min"] = val
                out["explicit_constraints"].append(f"RAM ≥ {val}GB")
            else:
                out["ram_exact_gb"] = val
                out["explicit_constraints"].append(f"RAM = {val}GB")
            out["strict_hardware"] = True
            break

    storage_patterns = [
        r"(?:ssd|هارد|storage)\s*(?:=|:)?\s*(128|256|512|1024|2048)\s*(?:gb|g|جيجا)?",
        r"(?<!\d)(128|256|512|1024|2048)\s*(?:gb|g|جيجا)?\s*(?:ssd|هارد|storage)",
    ]
    for pat in storage_patterns:
        m = re.search(pat, t, flags=re.I)
        if m:
            val = int(m.group(1))
            if any(k in t for k in ["على الاقل", "علي الاقل", "at least", "minimum"]):
                out["storage_min_gb"] = val
                out["explicit_constraints"].append(f"SSD ≥ {val}GB")
            else:
                out["storage_exact_gb"] = val
                out["explicit_constraints"].append(f"SSD = {val}GB")
            out["strict_hardware"] = True
            break

    return out

def _overlay_explicit(base: Dict, text: str) -> Dict:
    explicit = extract_explicit_constraints(text)
    out = dict(base)
    for k, v in explicit.items():
        if k == "explicit_constraints":
            out[k] = list(v)
        elif v is not None:
            out[k] = v
    if out.get("ram_exact_gb") is not None:
        out["ram_min"] = None
    return out

def local_parse(text: str) -> Dict:
    t = _normalize(text)
    budget_min, budget_max, budget_stretch = extract_budget(text)

    base = {
        "original_query": text,
        "use_cases": detect_use_cases(text),
        "software": detect_software(text),
        "workload_level": detect_workload_level(text),
        "budget_min": budget_min,
        "budget_max": budget_max,
        "budget_stretch": budget_stretch,
        "gpu_model_exact": None,
        "gpu_vram_exact_gb": None,
        "ram_exact_gb": None,
        "ram_min": None,
        "storage_exact_gb": None,
        "storage_min_gb": None,
        "screen_inches": None,
        "wants_touch": any(k in t for k in ["touch", "تاتش", "لمس"]),
        "wants_nvidia": any(k in t for k in ["nvidia", "نفيديا", "rtx", "cuda"]),
        "prefers_lightweight": any(k in t for k in ["خفيف الوزن", "portable", "تنقل", "جامعة"]),
        "strict_hardware": False,
        "explicit_constraints": [],
        "notes": "",
        "parser": "local",
    }

    sm = re.search(r"(\d{2}(?:\.\d)?)\s*(?:inch|بوصه|بوصة)", t)
    if sm:
        base["screen_inches"] = float(sm.group(1))
        base["strict_hardware"] = True

    return _overlay_explicit(base, text)

def _coerce_json(raw: str) -> Dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = re.sub(r"^\s*json\s*", "", raw, flags=re.I)
    try:
        return json.loads(raw)
    except Exception:
        pass
    m = re.search(r"\{.*\}", raw, flags=re.S)
    if m:
        return json.loads(m.group(0))
    raise ValueError("No valid JSON object in model response.")

def _normalize_ai_data(data: Dict, text: str, parser_name: str) -> Dict:
    allowed = set(USE_CASE_KEYWORDS) | {"general"}
    cases = data.get("use_cases") or ["general"]
    if isinstance(cases, str):
        cases = [cases]
    cases = [c for c in cases if c in allowed] or ["general"]

    level = str(data.get("workload_level", "balanced")).lower()
    if level not in {"light", "balanced", "heavy", "extreme"}:
        level = "balanced"

    software = data.get("software") or []
    if isinstance(software, str):
        software = [software]

    out = {
        "original_query": text,
        "use_cases": cases,
        "software": [str(x) for x in software],
        "workload_level": level,
        "budget_min": data.get("budget_min"),
        "budget_max": data.get("budget_max"),
        "budget_stretch": data.get("budget_stretch"),
        "gpu_model_exact": data.get("gpu_model_exact"),
        "gpu_vram_exact_gb": data.get("gpu_vram_exact_gb"),
        "ram_exact_gb": data.get("ram_exact_gb"),
        "ram_min": data.get("ram_min"),
        "storage_exact_gb": data.get("storage_exact_gb"),
        "storage_min_gb": data.get("storage_min_gb"),
        "screen_inches": data.get("screen_inches"),
        "wants_touch": bool(data.get("wants_touch", False)),
        "wants_nvidia": bool(data.get("wants_nvidia", False)),
        "prefers_lightweight": bool(data.get("prefers_lightweight", False)),
        "strict_hardware": bool(data.get("strict_hardware", False)),
        "explicit_constraints": [],
        "notes": str(data.get("notes", "")),
        "parser": parser_name,
    }

    for k in ("budget_min", "budget_max", "budget_stretch", "gpu_vram_exact_gb",
              "ram_exact_gb", "ram_min", "storage_exact_gb", "storage_min_gb"):
        v = out.get(k)
        if v is not None:
            try:
                out[k] = int(float(v))
            except Exception:
                out[k] = None
    if out["screen_inches"] is not None:
        try:
            out["screen_inches"] = float(out["screen_inches"])
        except Exception:
            out["screen_inches"] = None

    return _overlay_explicit(out, text)

def ai_parse(text: str) -> Dict:
    """
    Provider order:
      1) ITI Student API (DeepSeek V3.2 by default)
      2) FREE local Ollama
      3) Deterministic local parser

    The model extracts intent only. Product ranking remains deterministic.
    """
    system = """
You are the intent parser for an Egyptian laptop-sales recommendation engine.
You understand Egyptian Arabic, Modern Standard Arabic, Arabizi, and English.

IMPORTANT:
- Do NOT recommend any laptop.
- Do NOT assume that a generic request needs the strongest hardware.
- "Programming" by itself means normal programming / web / study unless the customer explicitly mentions
  Android Studio, VMs, AI/ML, game development, heavy compiling, etc.
- "Photoshop" by itself is a moderate 2D design workload, not 3D rendering.
- "Engineering" depends heavily on named software. AutoCAD 2D is lighter than SolidWorks/Revit,
  and Lumion/3ds Max/rendering is much heavier.
- Infer workload_level from the customer's words:
  light = basic/student/light work
  balanced = normal professional use
  heavy = heavy projects/rendering/4K/many VMs
  extreme = explicitly very heavy/extreme
- Preserve named software in `software`.
- A stated budget is a hard constraint, NOT a signal to spend all of it.
- If the customer names exact hardware (example: "RTX A2000 8G", "RAM 32", "512 SSD"), treat it as a HARD constraint.
- Never silently substitute another GPU, VRAM, RAM, or SSD.
- Only set budget_stretch if the customer explicitly says they can increase the budget.

Return ONLY valid JSON with exactly these keys:
{
  "use_cases": ["gaming|programming|engineering|architecture|video_editing|photoshop_design|ai_ml|office|general"],
  "software": ["named software only"],
  "workload_level": "light|balanced|heavy|extreme",
  "budget_min": integer|null,
  "budget_max": integer|null,
  "budget_stretch": integer|null,
  "gpu_model_exact": string|null,
  "gpu_vram_exact_gb": integer|null,
  "ram_exact_gb": integer|null,
  "ram_min": integer|null,
  "storage_exact_gb": integer|null,
  "storage_min_gb": integer|null,
  "screen_inches": number|null,
  "wants_touch": boolean,
  "wants_nvidia": boolean,
  "prefers_lightweight": boolean,
  "strict_hardware": boolean,
  "notes": string
}

Budget examples:
- "في حدود 25 ألف" => budget_max 25000, budget_stretch null
- "من 20 لـ 25 ألف" => budget_min 20000, budget_max 25000
- "25 ألف وممكن أزود 3" => budget_max 25000, budget_stretch 28000
- no price => all budget fields null

Output JSON only.
"""

    try:
        from .iti_api import is_configured, chat, model_name
        if is_configured():
            raw = chat(
                messages=[{"role": "user", "content": text}],
                system_prompt=system,
                model_id=model_name(),
                timeout=120,
            )
            return _normalize_ai_data(_coerce_json(raw), text, f"iti:{model_name()}")
    except Exception:
        pass

    try:
        from .local_llm import chat as ollama_chat, model_name as ollama_model
        raw = ollama_chat(system, text, temperature=0.0, json_mode=True, timeout=90)
        return _normalize_ai_data(_coerce_json(raw), text, f"ollama:{ollama_model()}")
    except Exception:
        pass

    return local_parse(text)
