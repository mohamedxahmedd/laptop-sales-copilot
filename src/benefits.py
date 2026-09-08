from __future__ import annotations
import math

def _valid(v):
    return v is not None and not (isinstance(v, float) and math.isnan(v))

def _integrated(gpu: str):
    t = (gpu or "").upper()
    return any(x in t for x in ["IRIS", "UHD", "RADEON GRAPHICS", "INTEGRATED", "UNKNOWN"])

def _has(cases, *names):
    return any(n in cases for n in names)

def build_benefits(row, req):
    cases = req.get("use_cases") or ["general"]
    benefits = []

    ram = row.get("ram_gb")
    if _valid(ram):
        ram = int(ram)
        if _has(cases, "programming", "office"):
            benefits.append(
                f"RAM {ram}GB: " +
                ("هتريحك جدًا مع الـIDE والمتصفح وتبويبات كتير وأدوات الشغل مع بعض، وتديك مساحة أكبر لو استخدمت Emulator أو Docker/VMs بعدين."
                 if ram >= 32 else
                 "مناسبة جدًا للبرمجة والمذاكرة والـmultitasking اليومي من غير ما تدفع في رام أعلى بدون احتياج."
                 if ram >= 16 else
                 "تمشي مع المذاكرة والبرمجة الخفيفة، لكن الشغل الأتقل يستفيد من رام أعلى.")
            )
        elif _has(cases, "gaming"):
            benefits.append(f"RAM {ram}GB: بتدي مساحة للعبة وبرامج الخلفية مع بعض؛ " + ("32GB كمان تدي headroom مريح للمستقبل." if ram >= 32 else "16GB مستوى عملي جدًا للجيمينج الحديث." if ram >= 16 else "الألعاب الأتقل غالبًا تستفيد من رام أعلى."))
        elif _has(cases, "architecture", "engineering"):
            benefits.append(f"RAM {ram}GB: مهمة مع المشاريع الكبيرة وفتح ملفات ورسومات أكتر في نفس الوقت داخل البرامج الهندسية.")
        elif _has(cases, "video_editing"):
            benefits.append(f"RAM {ram}GB: بتساعد في الـtimeline والـmultitasking، خصوصًا مع المشاريع والمؤثرات الأتقل.")
        elif _has(cases, "photoshop_design"):
            benefits.append(f"RAM {ram}GB: مفيدة للملفات الكبيرة والـlayers الكتير وفتح أكتر من برنامج تصميم مع بعض.")
        elif _has(cases, "ai_ml"):
            benefits.append(f"RAM {ram}GB: بتساعد في تجهيز الداتا وتشغيل notebooks وأدوات أكتر مع بعض؛ الاحتياج الفعلي يعتمد على المشروع.")
        else:
            benefits.append(f"RAM {ram}GB: بتدي مساحة أفضل للـmultitasking وتشغيل أكتر من برنامج مع بعض.")

    cpu = row.get("cpu")
    if cpu and str(cpu).lower() != "unknown":
        if _has(cases, "programming"): benefits.append(f"المعالج {cpu}: مهم في سرعة الـIDE والـbuild/compile وتشغيل أدوات التطوير.")
        elif _has(cases, "gaming"): benefits.append(f"المعالج {cpu}: بيكمّل كارت الشاشة وبيتعامل مع منطق اللعبة وبرامج الخلفية.")
        elif _has(cases, "architecture", "engineering"): benefits.append(f"المعالج {cpu}: مهم في سرعة تنفيذ الأوامر والحسابات وفتح المشاريع في البرامج الهندسية.")
        elif _has(cases, "video_editing"): benefits.append(f"المعالج {cpu}: بيساعد في استجابة برنامج المونتاج ومعالجة أجزاء كبيرة من الـtimeline والتصدير حسب البرنامج.")
        elif _has(cases, "photoshop_design"): benefits.append(f"المعالج {cpu}: مهم في استجابة Photoshop والفلاتر وفتح وحفظ الملفات.")
        else: benefits.append(f"المعالج {cpu}: يدي استجابة أسرع في البرامج والاستخدام اليومي.")

    gpu = row.get("gpu")
    vram = row.get("gpu_vram_gb")
    if gpu and not _integrated(gpu):
        vr = f" بذاكرة {int(float(vram))}GB" if _valid(vram) and float(vram) > 0 else ""
        if _has(cases, "programming", "office"): benefits.append(f"كارت الشاشة {gpu}{vr}: مش هو العامل الأساسي في البرمجة والمذاكرة العادية، لكن وجوده مفيد لو دخلت بعدين AI/CUDA أو 3D أو شغل رسومي.")
        elif _has(cases, "gaming"): benefits.append(f"كارت الشاشة {gpu}{vr}: هو الجزء الأساسي في الشغل الرسومي للألعاب، والـVRAM تساعد مع الخامات والجرافيكس حسب اللعبة.")
        elif _has(cases, "architecture"): benefits.append(f"كارت الشاشة {gpu}{vr}: مهم للـ3D والـviewport والرندر في البرامج اللي بتستفيد من الـGPU، والـVRAM تفيد مع المشاهد والخامات الأتقل.")
        elif _has(cases, "engineering"): benefits.append(f"كارت الشاشة {gpu}{vr}: مفيد للـ3D والـviewport وبعض العمليات المسرّعة بالـGPU في البرامج الهندسية.")
        elif _has(cases, "video_editing"): benefits.append(f"كارت الشاشة {gpu}{vr}: بيساعد في GPU acceleration والمؤثرات والـplayback في برامج المونتاج اللي تدعمه.")
        elif _has(cases, "photoshop_design"): benefits.append(f"كارت الشاشة {gpu}{vr}: يفيد في بعض المؤثرات والتسريع، لكن المعالج والرام يفضلوا أهم في شغل 2D العادي.")
        elif _has(cases, "ai_ml"): benefits.append(f"كارت الشاشة {gpu}{vr}: مهم لو شغلك AI/ML بيستخدم GPU acceleration، والـVRAM بتفرق في حجم الـworkload حسب المشروع.")
        else: benefits.append(f"كارت الشاشة {gpu}{vr}: كارت منفصل يفيد في المهام الرسومية والبرامج اللي بتستخدم GPU acceleration.")
    elif gpu:
        benefits.append("كارت الشاشة المدمج مناسب لو الاستخدام مش محتاج 3D/Render/Gaming/AI تقيل، وده يساعد تحافظ على السعر.")

    storage = row.get("storage_gb")
    if _valid(storage):
        storage = int(storage)
        benefits.append(f"SSD {storage}GB: يخلي تشغيل النظام وفتح البرامج والمشاريع أسرع، " + ("ومساحته عملية جدًا للشغل اليومي." if storage >= 512 else "ومساحته مناسبة للاستخدام الأساسي."))

    if bool(row.get("touch")):
        benefits.append("الشاشة Touch: إضافة عملية للتصفح والعرض والشرح السريع لو الميزة دي تهمك.")

    software = req.get("software") or []
    if software:
        benefits.append("الترشيح متظبط على البرامج اللي ذكرتها: " + "، ".join(software[:5]) + ".")

    return benefits[:6]
