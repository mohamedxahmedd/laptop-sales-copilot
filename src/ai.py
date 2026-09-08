from __future__ import annotations

from .benefits import build_benefits
from .scoring import specs_line, CASE_AR
from .utils import money

STYLE_GUIDE = {
    "attractive": "مقنع وشيك وبيبيع بالمعلومة، من غير مبالغة أو زن على العميل",
    "short": "مختصر جدًا وواضح، مناسب لعميل مش بيحب الرسائل الطويلة",
    "technical": "تقني أكتر، يشرح فائدة المواصفات بشكل واضح لعميل بيفهم في الأجهزة",
    "friendly": "ودود وطبيعي جدًا كأن سيلز محترف بيرد على واتساب",
}

def fallback_sales_message(row, req, shop_name="", message_style="attractive"):
    benefits = build_benefits(row, req)
    price = money(row.get("price_egp"))
    shop = f"{shop_name}\n" if shop_name else ""
    use_cases = " + ".join(CASE_AR.get(x, x) for x in (req.get("use_cases") or ["general"]))

    benefit_lines = "\n".join(f"• {x}" for x in benefits[:4])
    return (
        f"{shop}أنسب اختيار عندي ليك هو {row['model']} 👌\n\n"
        f"{specs_line(row)}\n\n"
        f"{benefit_lines}\n\n"
        f"الجهاز مناسب جدًا لـ {use_cases} من غير ما تدفع في مواصفات زيادة مش هتستفيد منها.\n"
        f"السعر: {price}\n\n"
        f"لو مناسبك الرينج ده ابعتلي وأنا أكملك التفاصيل."
    )

def _prompts(row, req, message_style, shop_name):
    benefits = build_benefits(row, req)
    style_text = STYLE_GUIDE.get(message_style, STYLE_GUIDE["attractive"])

    product = {
        "model": row["model"],
        "specs": specs_line(row),
        "price": money(row.get("price_egp")),
        "qty": int(row.get("qty", 0)),
        "benefit_facts": benefits,
    }
    user_need = req.get("original_query", "")

    system = f"""
أنت Sales Consultant مصري محترف في بيع اللابتوبات.
مهمتك تكتب رسالة WhatsApp للعميل باللهجة المصرية الطبيعية.

أسلوب الرسالة المطلوب:
{style_text}

الهدف:
- العميل يفهم بسرعة ليه الجهاز ده مناسب له هو تحديدًا.
- ما تكتفيش بسرد المواصفات؛ اربط كل مواصفة مهمة بفائدتها العملية.
- مثال صحيح: "RAM 32GB هتريحك جدًا في فتح أكتر من برنامج ومشروع في نفس الوقت."
- مثال صحيح: "RTX A2000 8GB مفيد في الشغل الرسومي والرندر والبرامج اللي بتستفيد من الـGPU."
- لو المواصفة أقوى من احتياج العميل، ما تبيعهاش على إنها ضرورية.
- وضّح ميزة القيمة مقابل السعر لما الجهاز مناسب من غير overkill.

قواعد صارمة جدًا:
- استخدم فقط Product facts وBenefit facts اللي هتجيلك.
- ممنوع اختراع حالة الجهاز، الضمان، البطارية، نوع الـpanel، دقة الشاشة، الإكسسوارات، FPS، benchmark،
  الحرارة، مدة التشغيل، أو أي مواصفة غير موجودة.
- ممنوع تضمن أداء برنامج أو لعبة بنسبة 100%.
- ممنوع تقول "أقوى جهاز" أو "أفضل جهاز في السوق" إلا لو دي حقيقة معطاة، وهي مش معطاة هنا.
- اذكر السعر بالضبط لو موجود.
- الرسالة لازم تبقى سهلة القراءة على WhatsApp: سطور قصيرة ومسافات كويسة.
- استخدم من 0 إلى 2 emoji فقط.
- لا تستخدم Markdown headings ولا كلام AI رسمي.
- اختم بسؤال/Call-to-action طبيعي يخلي العميل يكمل الكلام.
"""

    user = f"""
رسالة العميل الأصلية:
{user_need}

بيانات الجهاز المسموح استخدامها:
{product}

اسم المحل:
{shop_name or "غير مذكور"}

اكتب الرسالة النهائية فقط، من غير شرح.
"""
    return system, user

def generate_sales_message(row, req, message_style="attractive", shop_name=""):
    system, user = _prompts(row, req, message_style, shop_name)

    # 1) ITI / DeepSeek
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

    # 2) Local Ollama fallback
    try:
        from .local_llm import chat as ollama_chat
        return ollama_chat(system, user, temperature=0.45, json_mode=False, timeout=120)
    except Exception:
        pass

    return fallback_sales_message(row, req, shop_name, message_style)
