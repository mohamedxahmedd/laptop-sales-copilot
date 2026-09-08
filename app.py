import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Support Streamlit Community Cloud secrets automatically.
try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, (str, int, float, bool)):
            os.environ.setdefault(str(_k), str(_v))
except Exception:
    pass

from src.inventory import load_google_sheet, load_uploaded_file, normalize_inventory, google_user_oauth_configured
from src.parser import ai_parse
from src import scoring as scoring_engine
rank_inventory = scoring_engine.rank_inventory
reason_for = scoring_engine.reason_for
specs_line = scoring_engine.specs_line
need_summary = scoring_engine.need_summary

# Backward-safe import: avoids a hard crash if Streamlit briefly serves a mixed
# commit while files are updating. V4 scoring.py defines the real function.
constraint_summary = getattr(scoring_engine, "constraint_summary", lambda req: [])
from src.ai import generate_sales_message
from src.benefits import build_benefits
from src.utils import money

ROOT = Path(__file__).parent

st.set_page_config(
    page_title="Laptop Sales Copilot",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    :root {
        --radius-xl: 26px;
        --radius-lg: 18px;
        --muted: rgba(127,127,127,.78);
    }

    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    .stApp { direction: rtl; }
    .block-container {
        max-width: 1180px;
        padding-top: 1rem;
        padding-bottom: 4rem;
    }

    .topbar {
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:16px;
        margin-bottom:12px;
    }
    .brand {
        font-size:1.08rem;
        font-weight:850;
        letter-spacing:-.2px;
    }
    .status {
        font-size:.9rem;
        opacity:.72;
    }

    .hero {
        padding: 28px;
        border: 1px solid rgba(127,127,127,.18);
        border-radius: var(--radius-xl);
        margin-bottom: 18px;
        background:
          radial-gradient(circle at 85% 20%, rgba(80,110,255,.16), transparent 34%),
          radial-gradient(circle at 5% 90%, rgba(20,190,145,.10), transparent 28%),
          rgba(127,127,127,.035);
    }
    .eyebrow {
        display:inline-block;
        font-size:.86rem;
        font-weight:800;
        padding:6px 10px;
        border-radius:999px;
        border:1px solid rgba(127,127,127,.22);
        margin-bottom:10px;
    }
    .hero-title {
        font-size:2.35rem;
        font-weight:900;
        line-height:1.2;
        letter-spacing:-.8px;
        margin-bottom:8px;
    }
    .hero-sub {
        font-size:1.08rem;
        opacity:.74;
        line-height:1.85;
        max-width:850px;
    }

    .step-title {
        font-size:1.32rem;
        font-weight:900;
        margin-top:20px;
        margin-bottom:8px;
    }
    .step-no {
        display:inline-flex;
        width:30px; height:30px;
        align-items:center; justify-content:center;
        border-radius:9px;
        background:rgba(90,100,255,.11);
        font-size:.92rem;
        margin-left:6px;
    }

    div[data-testid="stTextArea"] textarea,
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input {
        font-size:1.07rem !important;
        border-radius:14px !important;
    }

    .stButton > button {
        min-height:52px;
        border-radius:14px;
        font-size:1.02rem;
        font-weight:800;
    }

    .result-label {
        font-size:.82rem;
        font-weight:850;
        opacity:.68;
        text-transform:uppercase;
        margin-bottom:4px;
    }
    .result-model {
        font-size:1.38rem;
        font-weight:900;
        line-height:1.25;
        margin-bottom:7px;
    }
    .spec-line {
        font-size:1rem;
        opacity:.82;
        line-height:1.7;
    }
    .price {
        font-size:1.55rem;
        font-weight:900;
        white-space:nowrap;
    }
    .match {
        font-size:.88rem;
        opacity:.68;
        margin-top:4px;
    }

    .benefit-box {
        padding:13px 15px;
        margin:8px 0;
        border-radius:14px;
        border:1px solid rgba(127,127,127,.16);
        background:rgba(127,127,127,.035);
        line-height:1.65;
    }

    .fit-box {
        padding:12px 14px;
        border-radius:14px;
        background:rgba(0,165,115,.07);
        border:1px solid rgba(0,165,115,.16);
        margin-top:10px;
        font-size:.95rem;
    }

    code {
        direction: rtl;
        text-align:right;
        white-space:pre-wrap !important;
        line-height:1.75 !important;
        font-size:1rem !important;
    }

    div[data-testid="stExpander"] details { border-radius:16px; }
    div[data-testid="stMetricValue"] { font-size:1.35rem; }

    @media(max-width:720px) {
        .block-container { padding-left:.75rem; padding-right:.75rem; }
        .hero { padding:20px; }
        .hero-title { font-size:1.78rem; }
        .hero-sub { font-size:1rem; }
        .topbar { align-items:flex-start; flex-direction:column; gap:2px; }
    }
</style>
""", unsafe_allow_html=True)

def require_password():
    password = os.getenv("APP_PASSWORD", "").strip()
    if not password:
        return True
    if st.session_state.get("authed"):
        return True
    st.markdown("## 🔐 دخول")
    entered = st.text_input("كلمة السر", type="password")
    if st.button("دخول", use_container_width=True, type="primary"):
        if entered == password:
            st.session_state.authed = True
            st.rerun()
        else:
            st.error("كلمة السر غير صحيحة.")
    return False

if not require_password():
    st.stop()

@st.cache_data(ttl=60, show_spinner=False)
def load_seed():
    return pd.read_csv(ROOT / "data" / "seed_inventory.csv")

@st.cache_data(ttl=60, show_spinner=False)
def load_google_cached(url, worksheet, auth_fingerprint):
    # auth_fingerprint is intentionally non-secret; it only invalidates the cache
    # when auth mode changes. Credentials themselves are read from environment/secrets.
    return load_google_sheet(url, worksheet)

def get_inventory():
    default_source = os.getenv("DEFAULT_INVENTORY_SOURCE", "PDF seed")
    source = st.session_state.get("source", default_source)

    if source == "PDF seed":
        raw = load_seed()
    elif source == "Upload CSV / Excel":
        up = st.session_state.get("uploaded_inventory")
        if up is None:
            return None, ["ارفع ملف المخزون من الإعدادات."]
        raw = load_uploaded_file(up)
    else:
        url = st.session_state.get("google_sheet_url", "") or os.getenv("GOOGLE_SHEET_URL", "")
        url = url.strip()
        if not url:
            return None, ["حط لينك Google Sheet من الإعدادات."]
        worksheet = st.session_state.get("worksheet_name", "") or os.getenv("GOOGLE_SHEET_WORKSHEET", "")
        auth_mode = "user-oauth" if google_user_oauth_configured() else "public"
        raw = load_google_cached(url, worksheet.strip(), auth_mode)
    return normalize_inventory(raw)

from src.iti_api import is_configured as iti_configured, model_name as iti_model
if iti_configured():
    ai_status = f"🟢 AI جاهز — {iti_model()}"
else:
    ai_status = "🟡 AI غير متصل — البحث الأساسي شغال"

st.markdown(
    f'<div class="topbar"><div class="brand">💻 Laptop Sales Copilot</div><div class="status">{ai_status}</div></div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("⚙️ الإعدادات")
    st.caption("الإعدادات مش محتاج تفتحها أثناء البيع العادي.")

    st.subheader("المخزون")
    source_options = ["PDF seed", "Upload CSV / Excel", "Google Sheet"]
    if "source" not in st.session_state:
        _default_source = os.getenv("DEFAULT_INVENTORY_SOURCE", "PDF seed")
        st.session_state["source"] = _default_source if _default_source in source_options else "PDF seed"
    st.selectbox(
        "مصدر المخزون",
        source_options,
        key="source",
    )
    if st.session_state.source == "Upload CSV / Excel":
        st.file_uploader("ملف المخزون", type=["csv", "xlsx", "xls"], key="uploaded_inventory")
    elif st.session_state.source == "Google Sheet":
        st.text_input("Google Sheet URL", key="google_sheet_url")
        st.text_input("اسم الـSheet - اختياري", key="worksheet_name")
        if google_user_oauth_configured():
            st.success("🔐 Google OAuth متصل — الشيت الـPrivate هيتقرأ بصلاحية Gmail بتاعك")
        else:
            st.warning("Google OAuth مش متظبط في Secrets؛ الشيت لازم يكون Public لحد ما تضيف بيانات OAuth.")
        st.caption("لو اللينك فيه gid=... وسيبت اسم الـSheet فاضي، السيستم هيفتح نفس الـtab الموجود في اللينك.")

    st.divider()
    st.subheader("رسالة العميل")
    st.text_input("اسم المحل - اختياري", key="shop_name")
    st.caption("اختيار نوع الرسالة موجود تحت كل جهاز.")

try:
    result = get_inventory()
    if result[0] is None:
        st.warning(result[1][0])
        st.stop()
    inventory, warnings = result
except Exception as e:
    st.error(f"مشكلة في قراءة المخزون: {e}")
    st.stop()

st.markdown("""
<div class="hero">
    <div class="eyebrow">مساعدك الشخصي في البيع</div>
    <div class="hero-title">خد كلام العميل → واطلعله أنسب لاب ورسالة بيع جاهزة</div>
    <div class="hero-sub">
        مش بيديك أقوى جهاز وخلاص. النظام بيحدد احتياج العميل الحقيقي، يلتزم بالميزانية،
        ويفضّل الجهاز اللي يحقق المطلوب بأفضل قيمة.
    </div>
</div>
""", unsafe_allow_html=True)

m1, m2, m3 = st.columns(3)
m1.metric("موديلات متاحة", int((inventory["qty"] > 0).sum()))
m2.metric("موديلات بسعر", int(((inventory["qty"] > 0) & inventory["price_egp"].notna()).sum()))
m3.metric("إجمالي الوحدات", int(inventory["qty"].clip(lower=0).sum()))

st.markdown('<div class="step-title"><span class="step-no">1</span> قولّي العميل محتاج إيه</div>', unsafe_allow_html=True)

tab_message, tab_quick = st.tabs(["💬 الصق رسالة العميل", "⚡ اختيار سريع"])

query = ""

with tab_message:
    query_message = st.text_area(
        "رسالة العميل",
        height=135,
        placeholder="مثال: أنا طالب هندسة وبستخدم SolidWorks وAutoCAD وميزانيتي 25 ألف...",
        label_visibility="collapsed",
        key="query_message",
    )
    st.caption("الأدق: اكتب البرنامج + الميزانية + هل الشغل خفيف ولا تقيل.")

with tab_quick:
    q1, q2 = st.columns([1.2, 1])
    with q1:
        use_label = st.selectbox(
            "الاستخدام",
            [
                "برمجة", "برامج هندسية", "عمارة و3D", "جيمينج",
                "مونتاج", "فوتوشوب وجرافيك", "AI / Machine Learning",
                "شغل مكتبي", "استخدام عام"
            ],
            key="quick_use",
        )
        details = st.text_input(
            "البرامج أو التفاصيل",
            placeholder="مثال: Flutter + Android Studio",
            key="quick_details",
        )
    with q2:
        no_budget = st.checkbox("الميزانية مش محددة", key="no_budget")
        budget = st.number_input(
            "أقصى ميزانية",
            min_value=0,
            max_value=200000,
            value=25000,
            step=1000,
            disabled=no_budget,
            key="quick_budget",
        )
        level_label = st.selectbox(
            "طبيعة الشغل",
            ["عادي / متوسط", "خفيف / طالب", "تقيل", "تقيل جدًا"],
            key="quick_level",
        )

    if st.button("استخدم الاختيار السريع", key="build_quick", use_container_width=True):
        level_phrase = {
            "عادي / متوسط": "",
            "خفيف / طالب": "استخدام خفيف طالب",
            "تقيل": "شغل تقيل",
            "تقيل جدًا": "شغل تقيل جدا",
        }[level_label]
        parts = [use_label]
        if details.strip():
            parts.append(details.strip())
        if level_phrase:
            parts.append(level_phrase)
        if not no_budget and budget:
            parts.append(f"في حدود {int(budget)} جنيه")
        st.session_state.quick_query_built = " - ".join(parts)
        st.success("تمام، الاختيار السريع جاهز. دوس زر الترشيح تحت.")

query = (st.session_state.get("quick_query_built") or "").strip()
if st.session_state.get("query_message", "").strip():
    query = st.session_state.query_message.strip()

st.markdown('<div class="step-title"><span class="step-no">2</span> هات الترشيحات</div>', unsafe_allow_html=True)
go = st.button("🔎 رشّحلي الأنسب", type="primary", use_container_width=True)

if go:
    if not query:
        st.warning("اكتب رسالة العميل أو استخدم الاختيار السريع الأول.")
    else:
        with st.spinner("بفهم الاستخدام وبقارن السعر بالمواصفات..."):
            req = ai_parse(query)
            ranked, meta = rank_inventory(inventory, req, top_n=6)

        st.session_state.last_req = req
        st.session_state.last_ranked = ranked
        st.session_state.last_meta = meta
        st.session_state.sales_messages = {}

if "last_req" in st.session_state:
    req = st.session_state.last_req
    ranked = st.session_state.last_ranked
    meta = st.session_state.last_meta
    need = meta.get("need_profile", {})

    st.divider()
    st.markdown("### 🧠 فهمت طلب العميل كده")
    chips = constraint_summary(req)

    if req.get("strict_hardware"):
        st.success("🔒 **بحث دقيق:** أي مواصفة صريحة طلبتها هتتطبق حرفيًا، من غير بدائل مخفية.")

    st.info(need_summary(req, need))
    if chips:
        st.markdown("**الشروط المطبقة حرفيًا:** " + " · ".join(f"`{x}`" for x in chips))

    if meta.get("used_stretch"):
        st.warning("استخدمت الزيادة فقط لأن العميل قال صراحة إنه ممكن يزود الميزانية.")

    if ranked.empty:
        if req.get("strict_hardware"):
            st.error("مفيش جهاز **متاح في المخزون** مطابق 100% للمواصفات الصريحة دي.")
            st.caption("النظام مش هيعرض GPU أو RAM مختلفة ويعتبرها مطابقة. غيّر الشرط فقط لو العميل موافق.")
        else:
            st.error("مفيش جهاز متاح يطابق الشروط دي داخل الميزانية الحالية.")
    else:
        st.markdown("### ⭐ الترشيح الأساسي")

        def render_card(idx, row, pos=0, primary=False):
            labels = ["⭐ الأنسب", "💰 قيمة ممتازة", "⚡ بديل إضافي"]
            with st.container(border=True):
                l, r = st.columns([3.5, 1.2], vertical_alignment="top")
                with l:
                    label = "✅ مطابق للمواصفات المطلوبة" if req.get("strict_hardware") else labels[min(pos, 2)]
                    st.markdown(f'<div class="result-label">{label}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="result-model">{row["model"]}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="spec-line">{specs_line(row)}</div>', unsafe_allow_html=True)
                    st.markdown("**ليه مناسب للعميل؟**")
                    for b in build_benefits(row, req)[:4]:
                        st.markdown(f'<div class="benefit-box">✓ {b}</div>', unsafe_allow_html=True)
                    st.caption(reason_for(row, req, need))

                with r:
                    st.markdown(f'<div class="price">{money(row["price_egp"])}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="match">تطابق {row["match_score"]:.0f}%</div>', unsafe_allow_html=True)
                    st.caption(f"المتاح: {int(row['qty'])}")

                st.markdown("#### 📲 Message للعميل")
                st.caption("الرسالة بتتغير حسب اللي العميل قاله فعلًا؛ لو قال مواصفة بس، مش هنفترض استخدام من عندنا.")

                c1, c2 = st.columns([1.25, 2.4])
                with c1:
                    style_label = st.selectbox(
                        "الأسلوب",
                        ["جذابة وبيعية", "مختصرة", "تقنية", "ودية"],
                        key=f"style_{idx}",
                        label_visibility="collapsed",
                    )

                styles = {
                    "جذابة وبيعية": "attractive",
                    "مختصرة": "short",
                    "تقنية": "technical",
                    "ودية": "friendly",
                }

                msg_key = f"msg_{idx}"

                with c2:
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button(
                            "✨ جهّز Message",
                            key=f"msgbtn_{idx}",
                            use_container_width=True,
                            type="primary" if primary else "secondary",
                        ):
                            with st.spinner("بكتب رسالة مناسبة لنوع طلب العميل..."):
                                st.session_state.sales_messages[msg_key] = generate_sales_message(
                                    row,
                                    req,
                                    message_style=styles[style_label],
                                    shop_name=st.session_state.get("shop_name", ""),
                                    previous_message="",
                                )

                    with b2:
                        if st.button(
                            "🔥 صياغة أقوى",
                            key=f"regen_{idx}",
                            use_container_width=True,
                            disabled=msg_key not in st.session_state.get("sales_messages", {}),
                        ):
                            with st.spinner("بكتب زاوية بيع أقوى ومختلفة..."):
                                old_message = st.session_state.sales_messages.get(msg_key, "")
                                st.session_state.sales_messages[msg_key] = generate_sales_message(
                                    row,
                                    req,
                                    message_style=styles[style_label],
                                    shop_name=st.session_state.get("shop_name", ""),
                                    previous_message=old_message,
                                )

                if msg_key in st.session_state.get("sales_messages", {}):
                    st.code(st.session_state.sales_messages[msg_key], language=None)
                    st.caption("لو الصياغة مش على مزاجك، دوس «صياغة أقوى» وهيعيد كتابة الرسالة من زاوية بيع مختلفة من غير Template ثابت.")

        items = list(ranked.iterrows())
        first_idx, first_row = items[0]
        render_card(first_idx, first_row, 0, primary=True)

        if len(items) > 1:
            with st.expander(f"عرض البدائل ({len(items)-1})"):
                for pos, (idx, row) in enumerate(items[1:], start=1):
                    render_card(idx, row, pos, primary=False)

        with st.expander("تفاصيل تقنية للترتيب"):
            cols = ["model","cpu","ram_gb","storage_gb","gpu","gpu_vram_gb","screen_inches","price_egp","qty","fit_score","match_score","meets_needs"]
            st.dataframe(ranked[cols], use_container_width=True, hide_index=True)

with st.expander("📦 عرض المخزون الحالي"):
    st.dataframe(
        inventory[["model", "specs", "qty", "screen_inches", "price_egp"]],
        use_container_width=True,
        hide_index=True,
    )
