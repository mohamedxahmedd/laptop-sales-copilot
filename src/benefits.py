from __future__ import annotations
import math

def _valid(v):
    return v is not None and not (isinstance(v, float) and math.isnan(v))

def _gpu_integrated(gpu: str) -> bool:
    t = (gpu or "").upper()
    return any(x in t for x in ["IRIS", "UHD", "RADEON GRAPHICS", "INTEGRATED", "UNKNOWN"])

def _has(cases, *items):
    return any(x in cases for x in items)

def ram_benefit(ram: int, cases):
    if _has(cases, "gaming"):
        if ram >= 32:
            return f"RAM {ram}GB: تديك Headroom مريح للعبة مع Discord والمتصفح وبرامج الخلفية من غير ضغط سريع على الذاكرة."
        if ram >= 16:
            return f"RAM {ram}GB: سعة عملية جدًا للجيمينج الحديث وتشغيل اللعبة مع البرامج الأساسية في الخلفية."
        return f"RAM {ram}GB: تمشي مع استخدامات وألعاب أخف، لكن الألعاب الحديثة غالبًا تستفيد من سعة أعلى."

    if _has(cases, "programming", "office"):
        if ram >= 32:
            return f"RAM {ram}GB: تريحك مع IDE + متصفح + Tabs كتير، وتدي مساحة أفضل لو دخلت Emulator أو Docker/VMs."
        if ram >= 16:
            return f"RAM {ram}GB: مناسبة جدًا للبرمجة والمذاكرة والـmultitasking اليومي بين الـIDE والمتصفح والملفات."
        return f"RAM {ram}GB: مناسبة للمذاكرة والبرمجة الخفيفة، لكن المشاريع والأدوات الأتقل تستفيد من سعة أعلى."

    if _has(cases, "architecture", "engineering"):
        if ram >= 32:
            return f"RAM {ram}GB: مريحة مع المشاريع الكبيرة وفتح أكتر من ملف/برنامج هندسي في نفس الوقت."
        return f"RAM {ram}GB: بداية قوية للـCAD والشغل الهندسي المتوسط، وحجم المشروع هو اللي يحدد احتياجك لأكتر."

    if _has(cases, "video_editing"):
        if ram >= 32:
            return f"RAM {ram}GB: مريحة للمشاريع الأتقل والـmultitasking بين برنامج المونتاج وباقي الأدوات."
        return f"RAM {ram}GB: مناسبة للمونتاج المتوسط، والمشاريع الكبيرة والمؤثرات الكتير تستفيد من سعة أعلى."

    if _has(cases, "photoshop_design"):
        if ram >= 32:
            return f"RAM {ram}GB: ممتازة للملفات الكبيرة والـlayers الكتير وتشغيل Photoshop مع أدوات تانية."
        return f"RAM {ram}GB: مناسبة جدًا للتصميم اليومي وPhotoshop والـmultitasking."

    if _has(cases, "ai_ml"):
        return f"RAM {ram}GB: تساعد في تجهيز الداتا والـnotebooks وتشغيل الأدوات مع بعض؛ حجم المشروع هو اللي يحدد احتياجك الفعلي."

    return f"RAM {ram}GB: تديك مساحة أفضل للـmultitasking وتشغيل أكتر من برنامج مع بعض."

def cpu_benefit(cpu: str, cases):
    if _has(cases, "gaming"):
        return f"المعالج {cpu}: مهم في الألعاب اللي تعتمد على الـCPU وبيساعد يحافظ على التوازن مع كارت الشاشة وبرامج الخلفية."
    if _has(cases, "programming"):
        return f"المعالج {cpu}: هو اللي هتحس بيه في استجابة الـIDE والـbuild/compile وتشغيل أدوات التطوير."
    if _has(cases, "architecture", "engineering"):
        return f"المعالج {cpu}: مهم في الحسابات، تنفيذ الأوامر، واستجابة المشاريع داخل برامج الـCAD والـ3D."
    if _has(cases, "video_editing"):
        return f"المعالج {cpu}: بيساعد في استجابة الـtimeline والمعالجة والتصدير حسب البرنامج والـcodec."
    if _has(cases, "photoshop_design"):
        return f"المعالج {cpu}: مهم جدًا في استجابة Photoshop والفلاتر وفتح وحفظ الملفات."
    if _has(cases, "office"):
        return f"المعالج {cpu}: يدي استجابة سريعة في التصفح، Office، المحاضرات وبرامج الدراسة."
    if _has(cases, "ai_ml"):
        return f"المعالج {cpu}: مهم في تجهيز الداتا وتشغيل الأدوات والعمليات اللي مش رايحة على الـGPU."
    return f"المعالج {cpu}: مسؤول عن استجابة البرامج وتنفيذ الأوامر في الاستخدام اليومي."

def gpu_benefit(gpu: str, vram, cases):
    vr = f" بذاكرة {int(float(vram))}GB" if _valid(vram) and float(vram) > 0 else ""

    if _has(cases, "gaming"):
        return f"كارت الشاشة {gpu}{vr}: هو أهم جزء في الأداء الرسومي للألعاب، والـVRAM بتساعد مع الخامات والجرافيكس حسب اللعبة والإعدادات."
    if _has(cases, "architecture"):
        return f"كارت الشاشة {gpu}{vr}: مهم في الـviewport والـ3D والرندر داخل البرامج اللي بتستخدم GPU acceleration، والـVRAM بتفيد مع المشاهد والخامات الأتقل."
    if _has(cases, "engineering"):
        return f"كارت الشاشة {gpu}{vr}: مفيد للـ3D والـviewport وبعض التسريع الرسومي في البرامج الهندسية."
    if _has(cases, "video_editing"):
        return f"كارت الشاشة {gpu}{vr}: بيساعد في GPU acceleration والمؤثرات والـplayback داخل برامج المونتاج اللي بتدعمه."
    if _has(cases, "ai_ml"):
        return f"كارت الشاشة {gpu}{vr}: مهم لو شغلك AI/ML بيستخدم GPU acceleration، والـVRAM بتحدد جزء من حجم الـworkload الممكن."
    if _has(cases, "photoshop_design"):
        return f"كارت الشاشة {gpu}{vr}: يفيد في بعض التأثيرات والتسريع، لكن المعالج والرام يفضلوا أهم في شغل 2D العادي."
    if _has(cases, "programming", "office"):
        return f"كارت الشاشة {gpu}{vr}: مش العامل الأساسي في البرمجة والمذاكرة العادية، لكنه مفيد لو دخلت AI/CUDA أو 3D أو شغل رسومي."
    return f"كارت الشاشة {gpu}{vr}: كارت منفصل يفيد في الألعاب، 3D، الرندر والبرامج اللي تستخدم GPU acceleration حسب البرنامج."

def storage_benefit(storage: int):
    if storage >= 1024:
        return f"SSD {storage}GB: سرعة في تشغيل النظام وفتح البرامج، ومعاك مساحة كبيرة للمشاريع والألعاب والملفات."
    if storage >= 512:
        return f"SSD {storage}GB: سرعة في تشغيل النظام وفتح البرامج، ومساحة عملية لمعظم الاستخدامات."
    return f"SSD {storage}GB: سريع في تشغيل النظام والبرامج، لكن المساحة محدودة نسبيًا لو عندك ألعاب أو مشاريع كبيرة."

def build_benefits(row, req):
    cases = req.get("use_cases") or ["general"]
    software = req.get("software") or []

    ram = row.get("ram_gb")
    cpu = row.get("cpu")
    gpu = row.get("gpu")
    vram = row.get("gpu_vram_gb")
    storage = row.get("storage_gb")
    screen = row.get("screen_inches")
    touch = bool(row.get("touch"))

    parts = {}

    if _valid(ram):
        parts["ram"] = ram_benefit(int(ram), cases)
    if cpu and str(cpu).lower() != "unknown":
        parts["cpu"] = cpu_benefit(str(cpu), cases)
    if gpu:
        if _gpu_integrated(gpu):
            if _has(cases, "gaming", "architecture", "engineering", "video_editing", "ai_ml"):
                parts["gpu"] = "كارت الشاشة هنا مدمج؛ لو الاستخدام تقيل رسوميًا فالكارت المنفصل عادةً أنسب."
            else:
                parts["gpu"] = "الكارت المدمج كفاية لو الاستخدام مش محتاج GPU قوي، وده يمنعك تدفع زيادة في قوة مش أساسية."
        else:
            parts["gpu"] = gpu_benefit(str(gpu), vram, cases)
    if _valid(storage):
        parts["storage"] = storage_benefit(int(storage))
    if touch:
        parts["touch"] = "الشاشة Touch ميزة إضافية لو أنت محتاج اللمس فعلًا، لكنها مش سبب الترشيح الأساسي لو ماطلبتهاش."
    if _valid(screen):
        s = int(float(screen))
        if s >= 17:
            parts["screen"] = f"شاشة {s} بوصة تدي مساحة عرض كبيرة للألعاب، الـtimeline، الأكواد أو الرسومات."
        elif s <= 14:
            parts["screen"] = f"شاشة {s} بوصة تخلي الجهاز أريح في التنقل والمذاكرة والشغل خارج المكتب."

    # Order by what matters to THIS customer.
    if _has(cases, "gaming"):
        order = ["gpu", "cpu", "ram", "storage", "screen", "touch"]
    elif _has(cases, "programming", "office"):
        order = ["cpu", "ram", "storage", "gpu", "screen", "touch"]
    elif _has(cases, "architecture", "engineering"):
        order = ["gpu", "ram", "cpu", "storage", "screen", "touch"]
    elif _has(cases, "video_editing"):
        order = ["gpu", "cpu", "ram", "storage", "screen", "touch"]
    elif _has(cases, "photoshop_design"):
        order = ["cpu", "ram", "storage", "gpu", "screen", "touch"]
    elif _has(cases, "ai_ml"):
        order = ["gpu", "ram", "cpu", "storage", "screen", "touch"]
    else:
        order = ["cpu", "ram", "gpu", "storage", "screen", "touch"]

    benefits = [parts[k] for k in order if k in parts]
    if software:
        benefits.append("الترشيح متظبط على البرامج اللي ذكرتها: " + "، ".join(software[:5]) + ".")
    return benefits[:6]
