from __future__ import annotations

import secrets
import time

from .benefits import build_benefits
from .scoring import specs_line, constraint_summary
from .utils import money


STYLE_GUIDE = {
    "attractive": "سيلز مصري شاطر جدًا: واثق، مختصر، مقنع بالمعلومة، ومن غير أي إحساس Template أو AI",
    "short": "مختصر جدًا ومباشر، لكن كل جملة لها قيمة بيعية حقيقية",
    "technical": "تقني وواضح، يحول المواصفات لفوايد ويشرح ليه الجهاز اختيار منطقي",
    "friendly": "طبيعي وودود جدًا كأنك بترد بنفسك على واتساب",
}

# Large pools deliberately avoid one fixed opening/closing pattern.
OPENINGS = {
    "exact_hardware_only": [
        "لقيتلك المواصفة اللي طلبتها بالظبط.",
        "أيوه، عندي اختيار جاي بنفس الكارت اللي طلبته.",
        "بالنسبة لـ{hardware} تحديدًا، عندي الجهاز ده.",
        "لو {hardware} هو شرطك الأساسي، بص على الاختيار ده.",
        "المواصفة اللي طلبتها موجودة هنا فعلًا، ودي تفاصيل الجهاز.",
        "عندي جهاز مطابق للنقطة الأساسية اللي سألت عليها.",
    ],
    "gaming": [
        "لو هدفك الأساسي Gaming، فالاختيار ده هو اللي يستاهل تبدأ منه.",
        "للألعاب تحديدًا، الجهاز ده داخل الترشيح لسبب واضح: التوليفة بين المعالج والكارت والرام.",
        "لو عايز جهاز Gaming متوازن مش مجرد أرقام على الورق، بص على ده.",
        "للـGaming أنا ببص على الكارت والمعالج والرام كتوليفة واحدة، والجهاز ده عامل Balance كويس.",
        "لو الأولوية عندك هي اللعب، فده اختيار أقرب للي محتاجه من جهاز Workstation معمول لشغل مختلف.",
    ],
    "programming": [
        "للبرمجة أنا يهمني الجهاز يبقى سريع ومريح في الشغل اليومي، مش أدفعك في GPU مش محتاجه.",
        "لو استخدامك برمجة ومذاكرة، فالجهاز ده متظبط على الحاجات اللي هتحس بفرقها فعلًا.",
        "للبرمجة الاختيار الصح مش أقوى كارت شاشة؛ الأهم معالج ورام وSSD متوازنين، وده اللي موجود هنا.",
        "لو عايز جهاز يفضل مريح مع الـIDE والمتصفح والـmultitasking، بص على الاختيار ده.",
    ],
    "engineering": [
        "للبرامج الهندسية، التوليفة هنا معمولة على شغل CPU + GPU بشكل متوازن.",
        "لو شغلك هندسي وبيكبر مع الوقت، الاختيار ده مديك مساحة كويسة في المعالج والكارت والرام.",
        "للـCAD والـ3D والشغل الهندسي، الجهاز ده أقرب لطبيعة الاستخدام من لاب عادي.",
    ],
    "architecture": [
        "لو شغلك Revit / 3D / Rendering، هنا كارت الشاشة والرام بيفرقوا فعلًا، وده سبب ترشيح الجهاز.",
        "للعمارة والـ3D، الجهاز ده معمول للشغل اللي بيضغط على المعالج والكارت مع بعض.",
        "لو عندك Models ومشاهد تقيلة، التوليفة دي أقرب للاستخدام الفعلي من جهاز Business عادي.",
    ],
    "video_editing": [
        "للمونتاج، الجهاز ده متوازن في الحاجات اللي بتفرق فعلًا: المعالج، الرام، والكارت.",
        "لو شغلك على Premiere / Resolve، الاختيار ده داخل الترشيح عشان التوليفة مش عشان رقم واحد كبير.",
        "للمونتاج أنا بدور على جهاز ما يخنقكش مع الـtimeline والـmultitasking، وده اختيار منطقي.",
    ],
    "photoshop_design": [
        "للفوتوشوب والجرافيك، المهم استجابة المعالج والرام والـSSD أكتر من مطاردة أقوى GPU.",
        "لو شغلك Design وPhotoshop، الجهاز ده متوازن ومش محملك تكلفة مواصفات مش أساسية لشغلك.",
        "للجرافيك 2D، الاختيار ده مركز على الحاجات اللي هتحس بيها فعلًا أثناء الشغل.",
    ],
    "ai_ml": [
        "لو شغلك AI/ML، هنا الـGPU والـVRAM بيدخلوا في القرار بشكل أساسي.",
        "للـAI أنا مش ببص على اسم الجهاز بس؛ أهم نقطة هي الكارت والـVRAM وبعدهم الرام والمعالج.",
        "لو عندك CUDA / PyTorch أو Workloads على GPU، الجهاز ده داخل الترشيح بسبب التوليفة دي.",
    ],
    "budget_only": [
        "في الرينج ده، الاختيار ده مديك مواصفات كويسة مقابل السعر.",
        "لو أهم نقطة هي الميزانية، ده اختيار متوازن من غير ما أدفعك زيادة من غير سبب.",
        "داخل الرينج اللي حددته، الجهاز ده يستاهل يتشاف.",
    ],
    "generic": [
        "بص على الاختيار ده؛ مواصفاته متوازنة والسعر واضح.",
        "عندي اختيار كويس بالمواصفات دي.",
        "الجهاز ده يستاهل تحطه في المقارنة.",
    ],
}

CTAS = {
    "exact_hardware_only": [
        "لو المواصفات دي هي اللي بتدور عليها، أقولك باقي التفاصيل؟",
        "لو كده مطابق لطلبك، نكمّل في تفاصيل الجهاز.",
        "لو شرط الكارت اتحقق بالنسبة لك، أبعتهالك كاملة؟",
    ],
    "use_case": [
        "لو استخدامك ده هو الأساسي، أقولك هل ده الأنسب ولا فيه اختيار أوفر؟",
        "لو الرينج مناسبك، أكمّلك باقي التفاصيل.",
        "لو حابب، أقارنلك ده بأقرب بديل في نفس الاستخدام.",
        "لو ده داخل ميزانيتك، نكمّل في تفاصيل الجهاز؟",
    ],
    "budget_only": [
        "قولي استخدامك الأساسي وأنا أأكدلك هل ده أفضل اختيار في الرينج ولا فيه أنسب.",
        "لو تقولي هتستخدمه في إيه، أفلترلك الاختيار أدق.",
    ],
}


def _client_context(req):
    cases = [c for c in (req.get("use_cases") or ["general"]) if c != "general"]
    software = req.get("software") or []
    hard = constraint_summary(req)
    has_use = bool(cases or software)
    has_hw = bool(req.get("strict_hardware")) or bool(hard)
    has_budget = req.get("budget_max") is not None or req.get("budget_min") is not None

    if has_hw and not has_use and not has_budget:
        kind = "exact_hardware_only"
    elif has_hw and has_use:
        kind = "hardware_plus_use"
    elif has_use and has_budget:
        kind = "use_plus_budget"
    elif has_use:
        kind = "use_only"
    elif has_budget:
        kind = "budget_only"
    else:
        kind = "generic"

    primary_case = cases[0] if cases else None
    return {
        "kind": kind,
        "primary_case": primary_case,
        "cases": cases,
        "software": software,
        "hard": hard,
        "has_use": has_use,
        "has_hw": has_hw,
        "has_budget": has_budget,
    }


def _hardware_label(req):
    bits = []
    if req.get("gpu_model_exact"):
        g = str(req["gpu_model_exact"])
        if req.get("gpu_vram_exact_gb"):
            g += f" {int(req['gpu_vram_exact_gb'])}GB"
        bits.append(g)
    if req.get("ram_exact_gb"):
        bits.append(f"RAM {int(req['ram_exact_gb'])}GB")
    if req.get("storage_exact_gb"):
        bits.append(f"SSD {int(req['storage_exact_gb'])}GB")
    return " + ".join(bits) or "المواصفة اللي طلبتها"


def _opening_for(req, context):
    if context["kind"] == "exact_hardware_only":
        pool = OPENINGS["exact_hardware_only"]
    elif context["primary_case"] in OPENINGS:
        pool = OPENINGS[context["primary_case"]]
    elif context["kind"] == "budget_only":
        pool = OPENINGS["budget_only"]
    else:
        pool = OPENINGS["generic"]
    return secrets.choice(pool).format(hardware=_hardware_label(req))


def _cta_for(context):
    if context["kind"] == "exact_hardware_only":
        return secrets.choice(CTAS["exact_hardware_only"])
    if context["has_use"]:
        return secrets.choice(CTAS["use_case"])
    return secrets.choice(CTAS["budget_only"])



def _mentioned_title(query: str):
    q = (query or "").strip()
    # Common game naming pattern: FC27 / FC 27.
    m = __import__("re").search(r"\bFC\s*([0-9]{2})\b", q, flags=__import__("re").I)
    if m:
        return f"FC{m.group(1)}"
    return None


def _sales_brief(row, req):
    """
    Creates a high-level brief for the LLM. This stops the model from inventing
    a generic story and forces it to sell the actual reason this customer asked.
    """
    ctx = _client_context(req)
    original = (req.get("original_query") or "").strip()
    benefits = build_benefits(row, req)
    named_title = _mentioned_title(original)

    priority = []
    if req.get("gpu_model_exact"):
        txt = req["gpu_model_exact"]
        if req.get("gpu_vram_exact_gb"):
            txt += f" {int(req['gpu_vram_exact_gb'])}GB"
        priority.append(f"أول نقطة في الرسالة: أكد إن الجهاز جاي بـ{txt} لأن ده اللي العميل سأل عليه.")
    if req.get("ram_exact_gb"):
        priority.append(f"أكد RAM {int(req['ram_exact_gb'])}GB لأنها شرط صريح.")
    if ctx["primary_case"] == "gaming":
        priority.append("في Gaming: ابدأ بالكارت الرسومي ثم المعالج والرام. لا تجعل الـSSD هو بطل الرسالة.")
    elif ctx["primary_case"] == "programming":
        priority.append("في Programming: ابدأ بالمعالج والرام والـSSD. الـGPU ثانوي إلا لو العميل ذكر AI/3D/Game dev.")
    elif ctx["primary_case"] in {"architecture", "engineering"}:
        priority.append("في 3D/Engineering: اربط GPU/VRAM بالمشاهد والـviewport والرندر، والرام بالمشاريع الكبيرة.")
    elif ctx["primary_case"] == "video_editing":
        priority.append("في Editing: اربط CPU/GPU/RAM بالـtimeline والمؤثرات والـmultitasking بشكل محافظ.")
    elif ctx["primary_case"] == "photoshop_design":
        priority.append("في Photoshop/2D: ركز على CPU/RAM/SSD، ولا تبالغ في أهمية GPU.")
    elif ctx["primary_case"] == "ai_ml":
        priority.append("في AI/ML: GPU/VRAM هما مركز الرسالة ثم RAM/CPU.")

    if not ctx["has_use"]:
        priority.append("العميل لم يقل استخدامه: ممنوع تنسب له Gaming/Programming/Engineering من عندك.")
    if ctx["kind"] == "budget_only":
        priority.append("العميل قال Budget فقط: بيع القيمة واسأله عن الاستخدام في النهاية.")

    return {
        "customer_message": original,
        "mentioned_title": named_title,
        "context_kind": ctx["kind"],
        "primary_case": ctx["primary_case"],
        "software": ctx["software"],
        "hard_constraints": ctx["hard"],
        "must_focus_on": priority,
        "approved_benefit_facts": benefits,
        "suggested_opening_direction": _opening_for(req, ctx),
        "suggested_cta_direction": _cta_for(ctx),
        "context": ctx,
    }


def fallback_sales_message(row, req, shop_name="", message_style="attractive", previous_message=""):
    brief = _sales_brief(row, req)
    ctx = brief["context"]
    benefits = list(brief["approved_benefit_facts"])
    opening = brief["suggested_opening_direction"]
    price = money(row.get("price_egp"))

    # Prioritize benefits based on context instead of random garbage.
    selected = benefits[:4]

    # If the customer explicitly asked for a GPU, lead with the GPU benefit.
    if req.get("gpu_model_exact"):
        selected = sorted(
            selected,
            key=lambda x: 0 if "كارت الشاشة" in x else 1
        )

    if message_style == "short":
        selected = selected[:2]

    # Still vary presentation.
    if len(selected) >= 3 and secrets.randbelow(2):
        selected[1], selected[2] = selected[2], selected[1]

    if message_style == "short":
        body = "\n".join(f"• {x}" for x in selected)
    else:
        body = "\n".join(f"• {x}" for x in selected[:3])

    shop = f"{shop_name}\n" if shop_name else ""
    return (
        f"{shop}{opening}\n\n"
        f"{row['model']}\n"
        f"{specs_line(row)}\n\n"
        f"{body}\n\n"
        f"السعر: {price}\n"
        f"{brief['suggested_cta_direction']}"
    )


def _prompts(row, req, message_style, shop_name, previous_message=""):
    brief = _sales_brief(row, req)
    ctx = brief["context"]

    product = {
        "model": row["model"],
        "specs": specs_line(row),
        "price": money(row.get("price_egp")),
        "qty": int(row.get("qty", 0)),
    }

    previous_block = ""
    if previous_message:
        previous_block = f"""
آخر رسالة اتكتبت:
<<<
{previous_message}
>>>

النسخة الجديدة لازم تكون مختلفة بوضوح:
- Opening مختلف.
- ترتيب مختلف.
- زاوية بيع مختلفة.
- CTA مختلف.
- ممنوع تكرر جملة كاملة من النسخة السابقة.
"""

    variation = f"{int(time.time()*1000)}-{secrets.token_hex(4)}"

    system = f"""
أنت سيلز لابتوبات مصري Senior، بتكتب WhatsApp Copy قوية جدًا لكن طبيعية.
العميل لازم يحس إن شخص فاهم طلبه هو اللي رد عليه، مش AI ولا Template.

أسلوب النسخة:
{STYLE_GUIDE.get(message_style, STYLE_GUIDE["attractive"])}

ده Sales Brief مُستخرج من كلام العميل نفسه:
- نوع الطلب: {brief["context_kind"]}
- الاستخدام الأساسي إن وُجد: {brief["primary_case"]}
- اللعبة/العنوان المذكور إن وُجد: {brief["mentioned_title"]}
- البرامج المذكورة: {brief["software"]}
- الشروط الصريحة: {brief["hard_constraints"]}
- نقاط لازم تركز عليها: {brief["must_focus_on"]}
- فوائد مسموح لك تستخدمها: {brief["approved_benefit_facts"]}
- اتجاه Opening مقترح: {brief["suggested_opening_direction"]}
- اتجاه CTA مقترح: {brief["suggested_cta_direction"]}
- Variation: {variation}

قواعد غير قابلة للكسر:
1) الرسالة لازم تكون Fit على رسالة العميل الأصلية، مش على Template ثابت.
2) لو العميل طلب GPU محدد فقط:
   - افتح من الـGPU نفسه.
   - أكد التطابق.
   - اشرح باقي المواصفات كقيمة إضافية عامة.
   - ممنوع تقول "بناءً على استخدامك" لأنه ماقالش استخدام.
3) لو العميل قال Gaming:
   - أول فايدة تكون GPU/VRAM.
   - بعدها CPU/RAM.
   - ما تبدأش بالـTouch أو SSD.
4) لو العميل قال Programming/Study:
   - أول فايدة CPU/RAM/SSD.
   - وضح إن GPU مش أساسي للبرمجة العادية لو ده صحيح.
5) لو العميل ذكر لعبة أو برنامج بالاسم، اذكر الاسم طبيعيًا في الرسالة عشان الرد يبقى واضح إنه معمول له هو،
   لكن ممنوع تقول "هيشغلها 100%" أو تعده بـFPS إلا لو عندك بيانات مؤكدة.
   مثال: لو قال FC27، ممكن تقول "لو FC27 هي الهدف الأساسي..." ثم تشرح ليه التوليفة Gaming-oriented.
6) ما تشرحش كل قطعة بنفس طول كل مرة. اختار 2-4 نقاط الأهم للعميل ده.
7) بلاش لغة كتالوج: "إضافة عملية للتصفح والعرض والشرح السريع" ونحوها إلا لو Touch مطلوب فعلًا.
8) ما تقولش "الجهاز ده اختيار محسوب جدًا للطلب اللي عندك" أو "لو ده قريب من اللي بتدور عليه" بشكل متكرر.
9) لا تخترع بطارية، ضمان، حالة، panel، resolution، FPS، benchmark، حرارة أو accessories.
10) RAM لا "تزود السرعة" بشكل مطلق؛ فائدتها مساحة أكبر للـmultitasking والبرامج الثقيلة.
11) GPU/VRAM تتشرح حسب سياق العميل، لا كفقرة عامة محفوظة.
12) 0-2 emoji فقط.
13) 70 إلى 140 كلمة تقريبًا للنسخة الجذابة. المختصرة أقصر.
14) السعر واضح في آخر ثلث الرسالة.
15) CTA واحد طبيعي، مش ضغط شراء ولا fake urgency.
16) ممنوع عناوين AI محفوظة زي "ليه الجهاز مناسب ليك؟" كل مرة.
17) الناتج النهائي فقط، بدون شرح أو تحليل.

{previous_block}
"""

    user = f"""
رسالة العميل الأصلية:
"{brief["customer_message"]}"

الجهاز:
{product}

اسم المحل:
{shop_name or "غير مذكور"}

اكتب Message WhatsApp نهائية، بشرية، قوية، وFit على الرسالة الأصلية.
"""
    return system, user


def generate_sales_message(row, req, message_style="attractive", shop_name="", previous_message=""):
    system, user = _prompts(row, req, message_style, shop_name, previous_message)

    try:
        from .iti_api import is_configured, chat, model_name
        if is_configured():
            return chat(
                messages=[{"role": "user", "content": user}],
                system_prompt=system,
                model_id=model_name(),
                timeout=120,
            )
    except Exception:
        pass

    try:
        from .local_llm import chat as ollama_chat
        return ollama_chat(system, user, temperature=0.72, json_mode=False, timeout=120)
    except Exception:
        pass

    return fallback_sales_message(
        row, req, shop_name=shop_name, message_style=message_style, previous_message=previous_message
    )
