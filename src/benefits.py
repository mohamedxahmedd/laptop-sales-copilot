from __future__ import annotations
import math
import pandas as pd

CASE_AR = {
    "gaming": "الجيمينج",
    "programming": "البرمجة",
    "engineering": "البرامج الهندسية",
    "architecture": "العمارة والـ3D",
    "video_editing": "المونتاج",
    "photoshop_design": "الفوتوشوب والجرافيك",
    "ai_ml": "الـAI وMachine Learning",
    "office": "الشغل المكتبي",
    "general": "الاستخدام اليومي",
}

def _valid(v):
    return v is not None and not (isinstance(v, float) and math.isnan(v))

def _gpu_integrated(gpu: str) -> bool:
    t = (gpu or "").upper()
    return any(x in t for x in ["IRIS", "UHD", "RADEON GRAPHICS", "INTEGRATED", "UNKNOWN"])

def build_benefits(row, req):
    """
    Returns factual, conservative benefit statements derived only from the row specs
    and the customer's stated use-case. These are fed to the LLM so the sales message
    stays attractive without inventing claims.
    """
    benefits = []

    cases = req.get("use_cases") or ["general"]
    software = req.get("software") or []
    usage = " + ".join(CASE_AR.get(c, c) for c in cases)

    ram = row.get("ram_gb")
    if _valid(ram):
        ram = int(ram)
        if ram >= 32:
            benefits.append(
                f"RAM {ram}GB: مساحة مريحة جدًا لتشغيل أكتر من برنامج وملف في نفس الوقت، "
                f"وده مهم خصوصًا مع {usage} والمشاريع الكبيرة."
            )
        elif ram >= 16:
            benefits.append(
                f"RAM {ram}GB: مناسبة جدًا للشغل اليومي والـmultitasking بدون ما تكون دافع زيادة في رام مش محتاجها."
            )
        elif ram >= 8:
            benefits.append(
                f"RAM {ram}GB: مناسبة للاستخدام الخفيف والمتوسط، لكن الشغل التقيل جدًا ممكن يستفيد من رام أعلى."
            )

    cpu = row.get("cpu")
    if cpu and str(cpu).lower() != "unknown":
        benefits.append(
            f"المعالج {cpu}: هو المسؤول عن سرعة تنفيذ الأوامر وتشغيل البرامج، "
            f"ومستواه مناسب للنوع ده من الاستخدام حسب الترشيح."
        )

    gpu = row.get("gpu")
    vram = row.get("gpu_vram_gb")
    if gpu and not _gpu_integrated(gpu):
        if _valid(vram) and float(vram) > 0:
            benefits.append(
                f"كارت الشاشة {gpu} بذاكرة {int(float(vram))}GB: بيساعد في المهام اللي بتستفيد من الـGPU "
                f"زي 3D والرندر والمونتاج وبعض البرامج الهندسية حسب البرنامج."
            )
        else:
            benefits.append(
                f"كارت الشاشة {gpu}: كارت منفصل بيدي مساحة أفضل للمهام الرسومية مقارنةً بالكارت المدمج."
            )
    elif gpu:
        benefits.append(
            "كارت الشاشة المدمج مناسب لو استخدام العميل مش محتاج 3D أو رندر أو GPU قوي، "
            "وده بيساعد نحافظ على السعر بدل ما ندفعه في قوة مش هيستفيد منها."
        )

    storage = row.get("storage_gb")
    if _valid(storage):
        storage = int(storage)
        if storage >= 512:
            benefits.append(
                f"SSD {storage}GB: بيدي استجابة أسرع في فتح الويندوز والبرامج والملفات، "
                "ومساحته عملية لعدد كويس من البرامج والمشاريع."
            )
        else:
            benefits.append(
                f"SSD {storage}GB: سريع في التشغيل وفتح البرامج، مع مساحة مناسبة للاستخدام الأساسي."
            )

    if bool(row.get("touch")):
        benefits.append(
            "الشاشة Touch: ميزة عملية لو العميل بيحب التنقل والضغط المباشر على الشاشة أو العرض السريع."
        )

    screen = row.get("screen_inches")
    if _valid(screen):
        screen = int(float(screen))
        if screen >= 17:
            benefits.append(
                f"شاشة {screen} بوصة: مساحة عرض كبيرة ومريحة للتايملاين، الأكواد، الجداول أو الرسومات."
            )
        elif screen <= 14:
            benefits.append(
                f"شاشة {screen} بوصة: حجم عملي للتنقل والحمل مع مساحة شغل مناسبة."
            )

    if software:
        benefits.append(
            "الترشيح معمول بناءً على البرامج اللي ذكرتها: " + "، ".join(software[:5]) + "."
        )

    # Keep the model prompt compact and useful.
    return benefits[:6]
