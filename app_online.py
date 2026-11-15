import streamlit as st
import os
import re
from datetime import datetime
from pypdf import PdfReader
from supabase import create_client, Client

st.set_page_config(page_title="Diagnoză Auto PRO Online", page_icon="🔧", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #161B22; border-right: 1px solid #30363D; }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label, [data-testid="stSidebar"] div[role="radiogroup"] label div p {
        color: #FFFFFF !important;
        font-style: italic !important;
        font-weight: normal !important;
        font-size: 16px !important;
    }
    h1, h2, h3 { color: #58A6FF !important; font-family: 'Segoe UI', sans-serif; }
    [data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] label, .stTextInput label p, .stTextArea label p, .stNumberInput label p, .stSelectbox label p, .stFileUploader label p {
        color: #58A6FF !important;
        font-style: italic !important;
        font-weight: normal !important;
        font-size: 15px !important;
    }
    [data-testid="stForm"] { background-color: #161B22; border: 1px solid #30363D; border-radius: 12px; padding: 20px; }
    .stTextInput input, .stTextArea textarea, .stNumberInput input { background-color: #0D1117 !important; color: #FFFFFF !important; border: 1px solid #484F58 !important; border-radius: 8px !important; }
    .stButton > button, [data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(135deg, #FF6B00 0%, #E65100 100%) !important;
        color: #FFFFFF !important; font-weight: bold !important; border: none !important; border-radius: 8px !important; padding: 10px 20px !important;
    }
    .streamlit-expanderHeader { background-color: #161B22 !important; border: 1px solid #30363D !important; border-radius: 8px !important; color: #FFFFFF !important; }
    .streamlit-expanderContent { background-color: #12161C !important; border: 1px solid #30363D !important; border-top: none !important; }
    .metric-card { background-color: #161B22; border: 1px solid #30363D; border-left: 4px solid #FF6B00; border-radius: 8px; padding: 15px; text-align: center; }
    .metric-value { font-size: 28px; font-weight: bold; color: #FFFFFF; }
    .metric-label { font-size: 14px; color: #58A6FF; font-style: italic; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_supabase()

if "autentificat" not in st.session_state:
    st.session_state.autentificat = False
if "garaj_curent" not in st.session_state:
    st.session_state.garaj_curent = ""

if not st.session_state.autentificat:
    st.title("🔐 Autentificare — Diagnoză Auto PRO")
    with st.form("login_form"):
        user_input = st.text_input("Nume Garaj (Utilizator)", placeholder="ex: Atelier Costi")
        parola_input = st.text_input("Parolă de acces", type="password")
        if st.form_submit_button("🔓 Intră în aplicație", use_container_width=True):
            garaje_dict = st.secrets.get("garaje", {})
            if user_input.strip() in garaje_dict and garaje_dict[user_input.strip()] == parola_input:
                st.session_state.autentificat = True
                st.session_state.garaj_curent = user_input.strip()
                st.rerun()
            else:
                st.error("Nume garaj sau parolă incorectă!")
    st.stop()

if "pagina_curenta" not in st.session_state:
    st.session_state.pagina_curenta = "🔍 Caută Cazuri / Istoric"
if "mesaj_succes" not in st.session_state:
    st.session_state.mesaj_succes = None

def extrage_date_pdf(fisier_pdf):
    reader = PdfReader(fisier_pdf)
    text_complet = "".join(page.extract_text() + "\n" for page in reader.pages)
    coduri_gasite = re.findall(r'\b[PBCU][0-9A-F]{4}\b', text_complet)
    return ", ".join(sorted(set(coduri_gasite))), text_complet

def incarca_fisier_cloud(fisier, folder):
    nume_curat = re.sub(r'[^a-zA-Z0-9._-]', '_', fisier.name)
    cale = f"{folder}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{nume_curat}"
    supabase.storage.from_("atasamente").upload(cale, fisier.getvalue(), {"content-type": fisier.type})
    return supabase.storage.from_("atasamente").get_public_url(cale)

st.title(f"🔧 Diagnoză Auto PRO — {st.session_state.garaj_curent}")

admin_user = st.secrets.get("ADMIN_USER", "")
optiuni_meniu = ["🔍 Caută Cazuri / Istoric", "📄 Import Raport PDF", "➕ Adaugă Caz Manual"]
if st.session_state.garaj_curent == admin_user:
    optiuni_meniu.append("🛡️ Administrare Garaje")

if st.session_state.pagina_curenta not in optiuni_meniu:
    st.session_state.pagina_curenta = optiuni_meniu[0]

meniu_ales = st.sidebar.radio("📌 MENIU PRINCIPAL", optiuni_meniu, index=optiuni_meniu.index(st.session_state.pagina_curenta))
if meniu_ales != st.session_state.pagina_curenta:
    st.session_state.pagina_curenta = meniu_ales
    st.rerun()

if st.sidebar.button("🚪 Deconectare"):
    st.session_state.autentificat = False
    st.session_state.garaj_curent = ""
    st.rerun()

if st.session_state.mesaj_succes:
    st.toast(st.session_state.mesaj_succes, icon="✅")
    st.success(st.session_state.mesaj_succes)
    st.session_state.mesaj_succes = None

if st.session_state.pagina_curenta == "🔍 Caută Cazuri / Istoric":
    toate_cazurile = supabase.table("cazuri").select("*").order("id", desc=True).execute().data
    total_cazuri = len(toate_cazurile)
    rezolvate = sum(1 for c in toate_cazurile if c.get("status") == "Rezolvat")
    in_lucru = total_cazuri - rezolvate

    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{total_cazuri}</div><div class="metric-label">Total Cazuri Cloud</div></div>', unsafe_allow_html=True)
    with col_s2:
        st.markdown(f'<div class="metric-card" style="border-left-color: #2EA043;"><div class="metric-value">{rezolvate}</div><div class="metric-label">Cazuri Rezolvate</div></div>', unsafe_allow_html=True)
    with col_s3:
        st.markdown(f'<div class="metric-card" style="border-left-color: #D29922;"><div class="metric-value">{in_lucru}</div><div class="metric-label">În Investigație</div></div>', unsafe_allow_html=True)

    st.write("")
    with st.form("formular_cautare"):
        col_c1, col_c2, col_c3 = st.columns([2, 2, 1])
        with col_c1:
            cautare_cod = st.text_input("Cod de eroare (DTC) / Cod Motor / Marcă", placeholder="ex: P0299, CFFB")
        with col_c2:
            cautare_rezolvare = st.text_input("Cuvânt cheie în Rezolvare / Investigații", placeholder="ex: furtun, mufa, EGR")
        with col_c3:
            st.write("")
            st.write("")
            st.form_submit_button("🔍 Caută", use_container_width=True)

    rezultate = []
    for c in toate_cazurile:
        potrivire_cod = True
        potrivire_rez = True
        if cautare_cod.strip():
            t = cautare_cod.strip().lower()
            potrivire_cod = any(t in str(c.get(k, "")).lower() for k in ["coduri_eroare", "cod_motor", "marca_model"])
        if cautare_rezolvare.strip():
            t = cautare_rezolvare.strip().lower()
            potrivire_rez = any(t in str(c.get(k, "")).lower() for k in ["rezolvare", "investigatii", "simptome"])
        if potrivire_cod and potrivire_rez:
            rezultate.append(c)

    st.markdown(f"**Rezultate afișate:** `{len(rezultate)}` cazuri")
    for row in rezultate:
        culoare = "🟢" if row.get("status") == "Rezolvat" else "🟡"
        titlu = f"{culoare} [{row.get('coduri_eroare')}] {row.get('marca_model')} ({row.get('an_fabricatie')}) — Motor: {row.get('cod_motor')} | Garaj: {row.get('garaj')} | {row.get('data_ora')}"
        with st.expander(titlu):
            col_a, col_b = st.columns([2, 1])
            with col_a:
                st.markdown(f"**Status:** `{row.get('status')}` | **Adăugat de:** `{row.get('garaj')}`")
                st.markdown(f"**Simptome:** {row.get('simptome') or 'Nespecificat'}")
                st.info(f"**Investigații făcute:**\n\n{row.get('investigatii')}")
                st.success(f"**Rezolvare:**\n\n{row.get('rezolvare') or 'Încă nu a fost adăugată o rezolvare.'}")
                if row.get("url_pdf"):
                    st.link_button("📄 Deschide / Descarcă Raportul PDF", row["url_pdf"])
            with col_b:
                if row.get("url_poza"):
                    st.image(row["url_poza"], caption="Imagine atașată", use_container_width=True)

elif st.session_state.pagina_curenta == "📄 Import Raport PDF":
    st.header("Import automat din raport PDF")
    pdf_incarcat = st.file_uploader("Alege raportul PDF", type=["pdf"])
    if pdf_incarcat is not None:
        coduri_extrase, text_brut = extrage_date_pdf(pdf_incarcat)
        with st.expander("👁️ Vezi textul extras din PDF"):
            st.text(text_brut[:2000])
        with st.form("formular_pdf", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                marca_model = st.text_input("Marcă și Model *")
                an_fabricatie = st.number_input("An fabricație", min_value=1980, max_value=2030, value=2015)
            with col2:
                cod_motor = st.text_input("Cod Motor *")
                coduri_eroare = st.text_input("Coduri DTC (extrase automat) *", value=coduri_extrase)
                status = st.selectbox("Status caz", ["În investigație", "Rezolvat", "Așteaptă piese"])
            simptome = st.text_area("Simptome reclamate")
            investigatii = st.text_area("Investigații și măsurători făcute *", value="Scanare inițială efectuată (raport PDF atașat).")
            rezolvare = st.text_area("Concluzie și Rezolvare finală")
            poza = st.file_uploader("Atașează o poză (opțional)", type=["jpg", "jpeg", "png"])
            if st.form_submit_button("💾 Salvează Cazul și Raportul PDF", use_container_width=True):
                if not marca_model or not cod_motor or not investigatii:
                    st.error("Completează Marcă/Model, Cod Motor și Investigații!")
                else:
                    url_pdf = incarca_fisier_cloud(pdf_incarcat, "pdf")
                    url_poza = incarca_fisier_cloud(poza, "poze") if poza else ""
                    supabase.table("cazuri").insert({
                        "data_ora": datetime.now().strftime("%d-%m-%Y %H:%M"),
                        "garaj": st.session_state.garaj_curent,
                        "marca_model": marca_model, "an_fabricatie": an_fabricatie,
                        "cod_motor": cod_motor.upper(), "coduri_eroare": coduri_eroare.upper(),
                        "simptome": simptome, "investigatii": investigatii, "rezolvare": rezolvare,
                        "status": status, "url_poza": url_poza, "url_pdf": url_pdf
                    }).execute()
                    st.session_state.mesaj_succes = f"Cazul pentru {marca_model} a fost salvat în cloud!"
                    st.session_state.pagina_curenta = "🔍 Caută Cazuri / Istoric"
                    st.rerun()

elif st.session_state.pagina_curenta == "➕ Adaugă Caz Manual":
    st.header("Înregistrare investigație manuală")
    with st.form("formular_manual", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            marca_model = st.text_input("Marcă și Model *")
            an_fabricatie = st.number_input("An fabricație", min_value=1980, max_value=2030, value=2015)
        with col2:
            cod_motor = st.text_input("Cod Motor *")
            coduri_eroare = st.text_input("Coduri de eroare (DTC) *")
            status = st.selectbox("Status caz", ["Rezolvat", "În investigație", "Așteaptă piese"])
        simptome = st.text_area("Simptome reclamate")
        investigatii = st.text_area("Investigații și măsurători făcute *")
        rezolvare = st.text_area("Concluzie și Rezolvare finală")
        poza = st.file_uploader("Atașează o poză (opțional)", type=["jpg", "jpeg", "png"])
        if st.form_submit_button("💾 Salvează Cazul", use_container_width=True):
            if not marca_model or not cod_motor or not coduri_eroare or not investigatii:
                st.error("Completează câmpurile obligatorii marcate cu *!")
            else:
                url_poza = incarca_fisier_cloud(poza, "poze") if poza else ""
                supabase.table("cazuri").insert({
                    "data_ora": datetime.now().strftime("%d-%m-%Y %H:%M"),
                    "garaj": st.session_state.garaj_curent,
                    "marca_model": marca_model, "an_fabricatie": an_fabricatie,
                    "cod_motor": cod_motor.upper(), "coduri_eroare": coduri_eroare.upper(),
                    "simptome": simptome, "investigatii": investigatii, "rezolvare": rezolvare,
                    "status": status, "url_poza": url_poza, "url_pdf": ""
                }).execute()
                st.session_state.mesaj_succes = f"Cazul pentru {marca_model} a fost salvat în cloud!"
                st.session_state.pagina_curenta = "🔍 Caută Cazuri / Istoric"
                st.rerun()

elif st.session_state.pagina_curenta == "🛡️ Administrare Garaje":
    st.header("🛡️ Panou Administrare Garaje")
    st.info("Pentru a adăuga un garaj nou sau a bloca accesul unuia existent, modifică secțiunea **[garaje]** din **Streamlit Cloud -> Settings -> Secrets**.")

