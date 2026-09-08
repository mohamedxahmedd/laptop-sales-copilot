from __future__ import annotations
from .benefits import build_benefits
from .scoring import specs_line, constraint_summary
from .utils import money

STYLE_GUIDE = {
    "attractive": "جذابة وبيعية بالمعلومة، مصرية طبيعية، من غير مبالغة",
    "short": "مختصرة جدًا لكن مفيدة",
    "technical": "تقنية وواضحة وتشرح سبب فائدة القطع",
    "friendly": "ودية وطبيعية جدًا",
}

def fallback_sales_message(row, req, shop_name="", message_style="attractive"):
    benefits = build_benefits(row, req)
    lines = "\n".join(f"• {b}" for b in benefits[:4])
    return f"""بناءً على استخدامك، الاختيار ده مناسب جدًا ليك 👌

{row['model']}
{specs_line(row)}

ليه مناسب ليك؟
{lines}

السعر: {money(row.get('price_egp'))}

لو مناسبك، أقولك باقي التفاصيل ونكمل؟"""

def _prompts(row, req, message_style, shop_name):
    benefits = build_benefits(row, req)
    product = {
        "model": row["model"],
        "specs": specs_line(row),
        "price": money(row.get("price_egp")),
        "qty": int(row.get("qty", 0)),
        "benefit_facts": benefits,
        "customer_hard_constraints": constraint_summary(req),
    }
    system = f"""
أنت Senior Laptop Sales Consultant مصري.
اكتب رسالة WhatsApp باللهجة المصرية الطبيعية. الأسلوب: {STYLE_GUIDE.get(message_style, STYLE_GUIDE["attractive"])}.

الرسالة لازم تربط كل مواصفة مهمة بفائدتها في استخدام العميل تحديدًا:
- RAM: ما تقولش إنها "بتسرّع" الجهاز بشكل مطلق؛ وضح إنها تدي مساحة للـmultitasking والأدوات الثقيلة.
- CPU: وضح دوره حسب الاستخدام.
- GPU/VRAM: وضح فائدتهم فقط لو الاستخدام يستفيد منهم.
- لو الاستخدام برمجة/مذاكرة عادية، قول إن GPU مش العامل الأساسي ووضح إمتى ممكن يفيد.
- اذكر السعر واختم CTA طبيعي.

ممنوع اختراع أي معلومة غير Product facts وBenefit facts.
ممنوع بطارية/ضمان/حالة/FPS/benchmark/panel/resolution/accessories.
ممنوع تبديل أي Hardware صريح طلبه العميل.
ممنوع المبالغة من نوع "أقوى جهاز في السوق".
خلي الرسالة جذابة وسهلة القراءة، 0-2 emoji فقط.
"""
    user = f"""طلب العميل:
{req.get("original_query", "")}

Product facts:
{product}

اسم المحل:
{shop_name or "غير مذكور"}

اكتب الرسالة النهائية فقط."""
    return system, user

def generate_sales_message(row, req, message_style="attractive", shop_name=""):
    system, user = _prompts(row, req, message_style, shop_name)
    try:
        from .iti_api import is_configured, chat, model_name
        if is_configured():
            return chat(messages=[{"role": "user", "content": user}], system_prompt=system, model_id=model_name(), timeout=120)
    except Exception:
        pass
    try:
        from .local_llm import chat as ollama_chat
        return ollama_chat(system, user, temperature=0.35, json_mode=False, timeout=120)
    except Exception:
        pass
    return fallback_sales_message(row, req, shop_name, message_style)
