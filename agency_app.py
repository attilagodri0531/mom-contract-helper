# --- 🔐 LOGIN SYSTEM ---
# This stops strangers from using your API key
if "APP_PASSWORD" in st.secrets:
    password = st.sidebar.text_input("Enter Password to Login", type="password")
    if password != st.secrets["APP_PASSWORD"]:
        st.warning("🔒 Please enter the correct password to access the bot.")
        st.stop()  # STOPS the code here. Nothing below runs.
import streamlit as st
from docxtpl import DocxTemplate
from num2words import num2words
import datetime
import io
import os
import base64
from openai import OpenAI
import json

# --- PAGE CONFIG ---
st.set_page_config(page_title="Agency Bot / 中介助手", page_icon="🏠", layout="wide")
st.title("🏠 Smart Contract Bot / 智能合同助手")

# --- 🧠 MEMORY INITIALIZATION ---
KEYS = [
    # data (persistent)
    "t_name_data","t_bp_data","t_bd_data","t_mn_data","t_id_data","t_add_data",
    "l_name_data","l_bp_data","l_bd_data","l_mn_data","l_id_data","l_add_data",

    # inputs (widgets)
    "t_name_input","t_bp_input","t_bd_input","t_mn_input","t_id_input","t_add_input",
    "l_name_input","l_bp_input","l_bd_input","l_mn_input","l_id_input","l_add_input",

    # phones/emails
    "t_phone","t_email","l_phone","l_email",

    # generated doc bytes
    "generated_doc",
]
for k in KEYS:
    st.session_state.setdefault(k, "")

def scan_id(uploaded_file, client):
    """Scan an ID image and return parsed JSON."""
    bytes_data = uploaded_file.getvalue()
    base64_img = base64.b64encode(bytes_data).decode("utf-8")
    mime = uploaded_file.type or "image/jpeg"

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Extract fields from this ID card. Return strict JSON with keys: "
                        "name, birth_place, birth_date, mother, id_num, address. "
                        "birth_date must be ISO format YYYY-MM-DD if possible. "
                        "If a field is missing, return empty string. No extra keys."
                    )
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{base64_img}"}
                }
            ],
        }],
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content)

# --- RAW TEXT PARSING FEATURE ---
def parse_raw_personal_data(raw_text: str, client):
    raw_text = (raw_text or "").strip()
    if not raw_text:
        return {"name": "", "birth_place": "", "birth_date": "", "mother": "", "id_num": "", "address": ""}

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You extract structured fields from messy user-provided text. "
                    "Return STRICT JSON ONLY. No commentary."
                ),
            },
            {
                "role": "user",
                "content": (
                    "You will receive a block of text with personal data copied from somewhere "
                    "(may contain HU/CN/EN labels, random separators, line breaks). "
                    "Extract and return strict JSON with exactly these keys:\n"
                    "name, birth_place, birth_date, mother, id_num, address\n\n"
                    "Rules:\n"
                    "- birth_date should be ISO YYYY-MM-DD if possible; otherwise keep the original date string.\n"
                    "- If a field is missing or uncertain, return empty string.\n"
                    "- No extra keys.\n\n"
                    f"RAW TEXT:\n{raw_text}"
                ),
            },
        ],
        response_format={"type": "json_object"},
    )

    data = json.loads(response.choices[0].message.content)
    allowed = ["name", "birth_place", "birth_date", "mother", "id_num", "address"]
    cleaned = {k: str(data.get(k, "") or "") for k in allowed}
    return cleaned

def set_if(overwrite: bool, key: str, value: str):
    if overwrite or not st.session_state.get(key):
        st.session_state[key] = value or ""

def apply_person_data(target_id: str, data: dict, overwrite: bool):
    if target_id == "landlord":
        set_if(overwrite, "l_name_data", data.get("name", ""))
        set_if(overwrite, "l_bp_data",   data.get("birth_place", ""))
        set_if(overwrite, "l_bd_data",   data.get("birth_date", ""))
        set_if(overwrite, "l_mn_data",   data.get("mother", ""))
        set_if(overwrite, "l_id_data",   data.get("id_num", ""))
        set_if(overwrite, "l_add_data",  data.get("address", ""))

        st.session_state.l_name_input = st.session_state.l_name_data
        st.session_state.l_bp_input   = st.session_state.l_bp_data
        st.session_state.l_bd_input   = st.session_state.l_bd_data
        st.session_state.l_mn_input   = st.session_state.l_mn_data
        st.session_state.l_id_input   = st.session_state.l_id_data
        st.session_state.l_add_input  = st.session_state.l_add_data

        st.toast("✅ Landlord Saved!")
    else:
        set_if(overwrite, "t_name_data", data.get("name", ""))
        set_if(overwrite, "t_bp_data",   data.get("birth_place", ""))
        set_if(overwrite, "t_bd_data",   data.get("birth_date", ""))
        set_if(overwrite, "t_mn_data",   data.get("mother", ""))
        set_if(overwrite, "t_id_data",   data.get("id_num", ""))
        set_if(overwrite, "t_add_data",  data.get("address", ""))

        st.session_state.t_name_input = st.session_state.t_name_data
        st.session_state.t_bp_input   = st.session_state.t_bp_data
        st.session_state.t_bd_input   = st.session_state.t_bd_data
        st.session_state.t_mn_input   = st.session_state.t_mn_data
        st.session_state.t_id_input   = st.session_state.t_id_data
        st.session_state.t_add_input  = st.session_state.t_add_data

        st.toast("✅ Tenant Saved!")

# --- SIDEBAR: INTELLIGENCE CENTER ---
with st.sidebar:
    st.header("⚙️ Tools / 工具")

    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
        st.success("🔑 Key Loaded! / 密钥已加载")
    else:
        api_key = st.text_input("OpenAI Key", type="password")

    st.divider()

    target_id = st.radio(
        "Who is this? / 扫描对象",
        options=["landlord", "tenant"],
        format_func=lambda x: "Landlord (Bérbeadó) / 房东" if x == "landlord" else "Tenant (Bérlő) / 租客"
    )

    overwrite = st.toggle("Overwrite existing fields / 覆盖已有字段", value=True)

    if api_key:
        client = OpenAI(api_key=api_key)

        st.subheader("🧾 RAW Personal Data / 原始个人信息")
        raw_text = st.text_area(
            "Paste here (any format). AI will extract name / birth / mother / ID / address.",
            key=f"raw_text_{target_id}",
            height=140,
            placeholder=(
                "Example:\n"
                "Név/Name: Zhang Wei\n"
                "Születési hely/Birth place: Beijing\n"
                "Születési idő/Birth date: 1998.03.14\n"
                "Anyja neve/Mother: Li Hua\n"
                "ID: AB123456\n"
                "Lakcím/Address: Budapest, ...\n"
            ),
        )
        if st.button("🧾 Parse & Auto-Fill / 解析并填写", key=f"raw_parse_{target_id}"):
            with st.spinner("🤖 Parsing text... / 正在解析..."):
                try:
                    data = parse_raw_personal_data(raw_text, client)
                    apply_person_data(target_id, data, overwrite)
                except Exception as e:
                    st.error(f"RAW Parse Error: {e}")

        st.divider()

        uploaded_file = st.file_uploader(
            "Upload ID",
            type=["jpg", "png", "jpeg"],
            key=f"uploader_{target_id}"
        )

        if uploaded_file and st.button("✨ Auto-Fill / 自动填写", key=f"autofill_{target_id}"):
            with st.spinner("🤖 AI is reading... / 正在识别..."):
                try:
                    data = scan_id(uploaded_file, client)
                    apply_person_data(target_id, data, overwrite)
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        st.warning("Enter your OpenAI key to enable scanning / parsing.")

# --- MAIN FORM ---
template_path = "template.docx"
if not os.path.exists(template_path):
    st.error("❌ Template missing!")
    st.stop()

tab1, tab2, tab3, tab4 = st.tabs(
    ["💶 Rent / 租金", "👤 Landlord / 房东", "👤 Tenant / 租客", "🏠 Property / 房产"]
)

with tab1:
    col1, col2 = st.columns(2)
    currency = col1.radio("Currency / 货币", ["HUF (Ft)", "EUR (€)"])
    c1, c2, c3 = st.columns(3)
    price = c1.number_input("Monthly Rent / 月租金", min_value=0, value=0, step=100)
    deposit = c2.number_input("Deposit / 押金", min_value=0, value=0, step=100)
    pay_day = c3.number_input("Pay Day / 付款日", min_value=0, max_value=31, value=0, step=1)
    st.divider()
    c1, c2 = st.columns(2)
    sign_date = c1.date_input("Sign Date / 签约日期", datetime.date.today())
    start_date = c2.date_input("Start Date / 起租日期", datetime.date.today())

with tab2:
    st.header("Landlord Info / 房东信息")
    l_name = st.text_input("Name / 姓名", key="l_name_input")
    c1, c2 = st.columns(2)
    l_birth_place = c1.text_input("Birth Place / 出生地", key="l_bp_input")
    l_birth_date  = c2.text_input("Birth Date / 出生日期", key="l_bd_input")
    l_mother      = st.text_input("Mother's Name / 母亲姓名", key="l_mn_input")
    l_id          = st.text_input("ID Number / 证件号码", key="l_id_input")
    l_address     = st.text_input("Address / 地址", key="l_add_input")
    c1, c2 = st.columns(2)
    l_phone = c1.text_input("Phone / 电话", key="l_phone")
    l_email = c2.text_input("Email / 邮箱", key="l_email")

with tab3:
    st.header("Tenant Info / 租客信息")
    t_name = st.text_input("Name / 姓名", key="t_name_input")
    c1, c2 = st.columns(2)
    t_birth_place = c1.text_input("Birth Place / 出生地", key="t_bp_input")
    t_birth_date  = c2.text_input("Birth Date / 出生日期", key="t_bd_input")
    t_mother      = st.text_input("Mother's Name / 母亲姓名", key="t_mn_input")
    t_id          = st.text_input("ID Number / 证件号码", key="t_id_input")
    t_address     = st.text_input("Address / 地址", key="t_add_input")
    c1, c2 = st.columns(2)
    t_phone = c1.text_input("Phone / 电话", key="t_phone")
    t_email = c2.text_input("Email / 邮箱", key="t_email")
    st.divider()
    people_count = st.number_input("Occupants / 入住人数", 1, 10, 1)
    movers_text = st.text_area("Other Movers / 其他入住人员", placeholder="Example: Li Ming (Wife)")

with tab4:
    st.header("Property Info / 房产信息")
    prop_address = st.text_input("Full Address / 完整地址")
    c1, c2, c3 = st.columns(3)
    district = c1.text_input("District / 区")
    hrsz = c2.text_input("HRSZ / 地籍号")
    size = c3.number_input("Size (sqm) / 面积", min_value=0, value=0, step=1)
    rooms = st.number_input("Rooms / 房间数", min_value=0, value=0, step=1)

st.divider()

if st.button("🚀 Generate Contract / 生成合同", type="primary"):
    doc = DocxTemplate(template_path)

    def fmt_money(val: float, currency_choice: str) -> str:
        if float(val) == 0.0:
            return "0"
        if currency_choice == "HUF (Ft)":
            return f"{val:,.0f}".replace(",", ".")
        return f"{val:,.2f}"

    if currency == "HUF (Ft)":
        curr_suf, text_suf = "Ft", "forint"
    else:
        curr_suf, text_suf = "EUR", "euró"

    p_fmt = fmt_money(price, currency)
    d_fmt = fmt_money(deposit, currency)

    p_text = num2words(price, lang="hu") + f" {text_suf}"
    d_text = num2words(deposit, lang="hu") + f" {text_suf}"

    start_hu = start_date.strftime("%Y. %m. %d.")
    start_cn = f"{start_date.year} 年 {start_date.month} 月 {start_date.day} 日"
    sign_hu = sign_date.strftime("%Y. %m. %d.")

    def fmt_num(val):
        try:
            v = float(val)
            if v.is_integer():
                return str(int(v))
            return str(v).replace(".", ",")
        except Exception:
            return str(val)

    context = {
        "LANDLORD_NAME": l_name,
        "LANDLORD_BIRTHPLACE": l_birth_place,
        "LANDLORD_BIRTHDATE": l_birth_date,
        "LANDLORD_MOTHER": l_mother,
        "LANDLORD_ID": l_id,
        "LANDLORD_ADDRESS": l_address,
        "LANDLORD_PHONE": l_phone,
        "LANDLORD_EMAIL": l_email,

        "TENANT_NAME": t_name,
        "TENANT_BIRTHPLACE": t_birth_place,
        "TENANT_BIRTHDATE": t_birth_date,
        "TENANT_MOTHER": t_mother,
        "TENANT_ID": t_id,
        "TENANT_ADDRESS": t_address,
        "TENANT_PHONE": t_phone,
        "TENANT_EMAIL": t_email,

        "MOVERS": movers_text if movers_text else None,
        "PEOPLE_COUNT": people_count,

        "PROPERTY_ADDRESS": prop_address,
        "DISTRICT": district,
        "HRSZ": hrsz,
        "SIZE": fmt_num(size),
        "ROOM_NUM": str(int(rooms)),

        "START_DATE_HU": start_hu,
        "START_DATE_CN": start_cn,
        "PAY_DAY": pay_day,
        "PAY_MAX_DAY": min(int(pay_day) + 5, 31),

        "PRICE": (f"{p_fmt} {curr_suf}" if p_fmt != "0" else "0"),
        "PRICE_TEXT": p_text,
        "DEPOSIT": (f"{d_fmt} {curr_suf}" if d_fmt != "0" else "0"),
        "DEPOSIT_TEXT": d_text,

        "SIGN_DATE": sign_hu,
    }

    doc.render(context)
    bio = io.BytesIO()
    doc.save(bio)
    st.session_state["generated_doc"] = bio.getvalue()
    st.success("✅ Contract Ready! / 合同已就绪")

if st.session_state["generated_doc"]:
    safe_name = t_name.replace(" ", "_") if t_name else "Contract"
    st.download_button(
        label="📥 Download .docx",
        data=st.session_state["generated_doc"],
        file_name=f"Contract_{safe_name}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
