from __future__ import annotations

import secrets
import time

from .benefits import build_benefits
from .scoring import specs_line, constraint_summary
from .utils import money


STYLE_GUIDE = {
    "attractive": "مقنع وشيك وبيبيع بالمعلومة، باللهجة المصرية الطبيعية، من غير مبالغة أو كلام محفوظ",
    "short": "قصير جدًا ومركز، لكن يفضل فيه سبب واضح يخلي العميل يهتم بالجهاز",
    "technical": "تقني وواضح، يشرح دور القطع المهمة في استخدام العميل من غير تعقيد زيادة",
    "friendly": "ودود وطبيعي جدًا، كأنك بتكلم العميل بنفسك على واتساب",
}

OPENING_DIRECTIONS = [
    "ابدأ مباشرة من الحاجة اللي العميل طلبها، من غير مقدمات عامة.",
    "ابدأ بجملة قصيرة فيها ثقة: الجهاز ده مطابق للنقطة الأساسية اللي العميل بيدور عليها.",
    "ابدأ باسم الجهاز والمواصفة الأهم، وبعدها قول ليه الاختيار منطقي.",
    "ابدأ بأسلوب استشاري هادي، كأنك بتقول للعميل إنك لقيتله اختيار يستاهل يبص عليه.",
    "ابدأ من القيمة: ليه الجهاز ده اختيار محسوب بدل ما يكون مجرد جهاز مواصفاته عالية.",
    "ابدأ بطريقة WhatsApp طبيعية جدًا، جملة واحدة قصيرة قبل اسم الجهاز.",
]

STRUCTURE_DIRECTIONS = [
    "رتب الرسالة: Hook قصير → الجهاز والمواصفات → 3 فوائد عملية → السعر → CTA.",
    "رتب الرسالة: الجهاز أولًا → أهم ميزتين للاستخدام → نقطة قيمة مقابل السعر → السعر → CTA.",
    "رتب الرسالة: المواصفة اللي العميل طلبها → الجهاز → باقي المواصفات كفوائد → السعر → CTA.",
    "رتب الرسالة: سؤال/جملة جذب قصيرة → الجهاز → ليه كل قطعة تفرق → السعر → نهاية طبيعية.",
    "خلي الرسالة سريعة القراءة: سطور قصيرة، ومن غير عنوان تقليدي ثابت زي 'ليه مناسب ليك؟' كل مرة.",
]

CTA_DIRECTIONS = [
    "اختم بسؤال بسيط يخلي العميل يرد، من غير ضغط شراء.",
    "اختم بـCTA طبيعي زي إنك تعرض تبعتله باقي التفاصيل لو الرينج مناسب.",
    "اختم بجملة قصيرة تخليه ياخد الخطوة اللي بعدها، من غير استعجال مصطنع.",
    "اختم بسؤال عن هل الجهاز داخل الرينج المناسب ليه، بدل جملة بيع محفوظة.",
]

PHRASES_TO_AVOID = [
    "بناءً على استخدامك",
    "الاختيار ده مناسب جدًا ليك",
    "ليه مناسب ليك؟",
    "وحش",
    "أقوى جهاز في السوق",
    "فرصة لا تعوض",
    "متفوتش الفرصة",
]


def _customer_context(req):
    use_cases = req.get("use_cases") or ["general"]
    software = req.get("software") or []
    hard = constraint_summary(req)

    has_real_use_case = any(x != "general" for x in use_cases) or bool(software)
    has_hardware = bool(req.get("strict_hardware")) or bool(hard)
    has_budget = req.get("budget_max") is not None or req.get("budget_min") is not None

    if has_hardware and not has_real_use_case and not has_budget:
        kind = "exact_hardware_only"
        rule = (
            "العميل قال مواصفة/مواصفات Hardware فقط وماقالش استخدامه. "
            "ممنوع تقول 'بناءً على استخدامك' أو تدّعي إن الجهاز مناسب لبرمجة/جيمينج/هندسة. "
            "ابدأ من إن الجهاز مطابق للمواصفة اللي طلبها، واشرح فائدة القطع بشكل عام فقط."
        )
    elif has_hardware and has_real_use_case:
        kind = "hardware_plus_use"
        rule = (
            "العميل محدد Hardware وكمان قال استخدامه. أكد التطابق مع الـHardware، "
            "وبعدها اربط باقي المواصفات بالاستخدام الفعلي."
        )
    elif has_real_use_case and has_budget:
        kind = "use_plus_budget"
        rule = (
            "العميل محدد استخدام وميزانية. ركز على إن الجهاز يحقق المطلوب داخل الرينج "
            "من غير overkill، واربط كل قطعة بالاستخدام."
        )
    elif has_real_use_case:
        kind = "use_only"
        rule = (
            "العميل قال الاستخدام فقط. اشرح ليه الجهاز مناسب للاستخدام، "
            "لكن ما تفترضش برامج أو متطلبات ماقالهاش."
        )
    elif has_budget:
        kind = "budget_only"
        rule = (
            "العميل قال ميزانية بس. ما تفترضش استخدام. ركز على القيمة والمواصفات الموجودة "
            "واسأله في الآخر عن الاستخدام لو ده هيساعد في اختيار أدق."
        )
    else:
        kind = "generic"
        rule = (
            "معلومات العميل قليلة. ما تخترعش استخدام. اعرض الجهاز والمواصفات بشكل مفيد "
            "واختم بسؤال واحد ذكي يكشف الاستخدام."
        )

    return {
        "kind": kind,
        "rule": rule,
        "has_real_use_case": has_real_use_case,
        "has_hardware": has_hardware,
        "has_budget": has_budget,
    }


def _variation_brief():
    return {
        "opening": secrets.choice(OPENING_DIRECTIONS),
        "structure": secrets.choice(STRUCTURE_DIRECTIONS),
        "cta": secrets.choice(CTA_DIRECTIONS),
        "nonce": f"{int(time.time() * 1000)}-{secrets.token_hex(3)}",
    }


def _fallback_opening(req, context):
    hard = constraint_summary(req)
    gpu = req.get("gpu_model_exact")

    if context["kind"] == "exact_hardware_only":
        if gpu:
            return secrets.choice([
                f"لو أهم حاجة عندك هي {gpu}، فالجهاز ده جاي بالمواصفة دي فعلًا.",
                f"بالنسبة لطلبك على {gpu} تحديدًا، عندي الاختيار ده.",
                f"لقيتلك جهاز بالمواصفة اللي طلبتها تحديدًا: {gpu}.",
            ])
        if hard:
            return secrets.choice([
                "لقيتلك جهاز مطابق للمواصفات اللي طلبتها.",
                "المواصفات اللي طلبتها موجودة في الجهاز ده.",
                "ده من الأجهزة المطابقة لطلبك حرفيًا.",
            ])

    if context["kind"] in {"hardware_plus_use", "use_plus_budget", "use_only"}:
        return secrets.choice([
            "الجهاز ده اختيار محسوب جدًا للطلب اللي عندك.",
            "ده من الاختيارات اللي مواصفاتها راكبة صح على احتياجك.",
            "لو عايز اختيار متوازن بدل ما تدفع في قوة زيادة، بص على الجهاز ده.",
        ])

    return secrets.choice([
        "بص على الاختيار ده، مواصفاته متوازنة جدًا.",
        "الجهاز ده يستاهل يبقى في أول اختياراتك.",
        "عندي اختيار كويس جدًا بالمواصفات دي.",
    ])


def fallback_sales_message(row, req, shop_name="", message_style="attractive", previous_message=""):
    benefits = build_benefits(row, req)
    context = _customer_context(req)
    opening = _fallback_opening(req, context)

    shop = f"{shop_name}\n" if shop_name else ""
    price = money(row.get("price_egp"))

    selected = list(benefits[:])
    secrets.SystemRandom().shuffle(selected)
    selected = selected[:2] if message_style == "short" else selected[:3]
    benefit_lines = "\n".join(f"• {b}" for b in selected)

    closings = [
        "لو الرينج مناسبك، أبعتلك باقي التفاصيل؟",
        "لو ده قريب من اللي بتدور عليه، أقولك باقي التفاصيل.",
        "شايفه مناسب لطلبك؟ أكمّلك التفاصيل لو حابب.",
        "لو السعر مناسب ليك، نكمّل في تفاصيل الجهاز.",
    ]
    if context["kind"] in {"budget_only", "generic"}:
        closings = [
            "ولو تقولي استخدامك الأساسي، أأكدلك هل ده أنسب اختيار ليك ولا فيه حاجة أدق.",
            "قولي هتستخدمه في إيه بالظبط وأنا أقولك هل ده الأنسب ولا فيه اختيار أحسن.",
        ]

    return (
        f"{shop}{opening}\n\n"
        f"{row['model']}\n"
        f"{specs_line(row)}\n\n"
        f"{benefit_lines}\n\n"
        f"السعر: {price}\n\n"
        f"{secrets.choice(closings)}"
    )


def _prompts(row, req, message_style, shop_name, previous_message=""):
    benefits = build_benefits(row, req)
    context = _customer_context(req)
    variation = _variation_brief()

    product = {
        "model": row["model"],
        "specs": specs_line(row),
        "price": money(row.get("price_egp")),
        "qty": int(row.get("qty", 0)),
        "benefit_facts": benefits,
        "customer_hard_constraints": constraint_summary(req),
    }

    previous_rule = ""
    if previous_message:
        previous_rule = f"""
دي آخر نسخة اتكتبت:
--- PREVIOUS MESSAGE ---
{previous_message}
--- END PREVIOUS MESSAGE ---

اكتب نسخة مختلفة بوضوح:
- غير أول جملة.
- غير ترتيب الفوائد.
- غير صياغة الـCTA.
- ما تعيدش جمل كاملة من النسخة السابقة.
"""

    system = f"""
أنت Senior Laptop Sales Consultant مصري شاطر جدًا في البيع على WhatsApp.
المطلوب رسالة تحس إنها مكتوبة بإيد سيلز فاهم، مش Template ومش AI.

الأسلوب العام:
{STYLE_GUIDE.get(message_style, STYLE_GUIDE["attractive"])}

نوع طلب العميل:
{context["kind"]}

قاعدة السياق الأساسية:
{context["rule"]}

Creative direction للنسخة دي:
- {variation["opening"]}
- {variation["structure"]}
- {variation["cta"]}
- Variation ID: {variation["nonce"]}

قواعد كتابة مهمة جدًا:
1. افهم الأول العميل قال إيه فعلًا. لو ماقالش استخدام، ممنوع تقول "بناءً على استخدامك".
2. ما تبدأش كل مرة بنفس الجملة. ممنوع Template ثابت.
3. اربط المواصفات بفوايد مفهومة:
   - RAM: مساحة أكبر للـmultitasking وتشغيل أدوات/برامج أكتر مع بعض. ما تقولش إن 32GB "تزود سرعة البروسيسور".
   - CPU: استجابة البرامج، الـbuild/compile، الحسابات أو المهام حسب الاستخدام المذكور فقط.
   - GPU/VRAM: اشرح فائدتهم حسب الاستخدام لو موجود.
     لو مفيش استخدام مذكور، اشرحهم بشكل عام: GPU acceleration / 3D / rendering / gaming / AI حسب البرنامج،
     من غير ما تقول إن العميل هيستخدمهم في حاجة محددة.
   - SSD: سرعة تشغيل وفتح برامج/ملفات ومساحة التخزين المتاحة.
4. لو العميل طلب مواصفة بعينها، أبرز إنها موجودة فعلًا في الجهاز.
5. بيع "الملاءمة" والقيمة، مش مجرد القوة الأعلى.
6. خلي الرسالة جذابة لكن believable؛ ممنوع fake urgency أو ضغط شراء.
7. ممنوع اختراع: حالة الجهاز، البطارية، الضمان، FPS، benchmark، نوع الـpanel،
   دقة الشاشة، الإكسسوارات، الحرارة أو أي معلومة مش موجودة.
8. لو معلومة مش موجودة، اسكت عنها.
9. من 0 لـ2 emoji فقط.
10. استخدم سطور قصيرة؛ الرسالة ما تبقاش مقال.
11. ما تستخدمش الجمل دي حرفيًا:
   {", ".join(PHRASES_TO_AVOID)}
12. اذكر السعر لو موجود.
13. اختم بـCTA واحد طبيعي فقط.

{previous_rule}
"""

    user = f"""
رسالة العميل الأصلية:
{req.get("original_query", "")}

بيانات الجهاز المسموح استخدامها:
{product}

اسم المحل:
{shop_name or "غير مذكور"}

اكتب الرسالة النهائية فقط. لا تشرح طريقة تفكيرك ولا تكتب عنوان قبل الرسالة.
"""
    return system, user


def generate_sales_message(
    row,
    req,
    message_style="attractive",
    shop_name="",
    previous_message="",
):
    system, user = _prompts(
        row,
        req,
        message_style,
        shop_name,
        previous_message=previous_message,
    )

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
        return ollama_chat(
            system,
            user,
            temperature=0.62,
            json_mode=False,
            timeout=120,
        )
    except Exception:
        pass

    return fallback_sales_message(
        row,
        req,
        shop_name=shop_name,
        message_style=message_style,
        previous_message=previous_message,
    )
