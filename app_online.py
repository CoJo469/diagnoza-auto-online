import streamlit as st
import os
import re
from datetime import datetime
from pypdf import PdfReader
from supabase import create_client, Client

st.set_page_config(page_title="Diagnoză Auto PRO (Cloud)", page_icon="🔧", layout="wide")

st.markdown('''
<style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #161B22; border-right: 1px solid #30363D; }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label, [data-testid="stSidebar"] div {
        color: #FFFFFF !important; font-style: italic !important; font-weight: normal !important;
    }
    [data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] label, .stTextInput label, .stTextArea label, .stNumberInput label, .stSelectbox label, .stFileUploader label {
        color: #58A6FF !important; font-style: italic !important; font-weight: normal !important; font-size: 15px !important;
    }
    h1, h2, h3 { color: #58A6FF !important; font-family: 'Segoe UI', sans-serif; }
    [data-testid="stForm"] { background-color: #161B22; border: 1px solid #30363D; border-radius: 12px; padding: 20px; }
    .stTextInput input, .stTextArea textarea, .stNumberInput input {
        background-color: #0D1117 !important; color: #FFFFFF !important; border: 1px solid #484F58 !important; border-radius: 8px !important;
    }
    .stButton > button, [data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(135deg, #FF6B00 0%, #E65100 100%) !important; color: white !important; font-weight: bold !important; border: none !important; border-radius: 8px !important;
    }
    .metric-card { background-color: #161B22; border: 1px solid #30363D; border-left: 4px solid #FF6B00; border-radius: 8px; padding: 15px; text-align: center; }
    .metric-value { font-size: 28px; font-weight: bold; color: #FFFFFF; }
    .metric-label { font-size: 14px; color: #58A6FF; font-style: italic; }
</style>
''', unsafe_allow_html=True)

@st.cache_resource
def init_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

try:
    supabase = init_supabase()
except Exception:
    st.error("⚠️ Nu s-a putut realiza conexiunea cu Supabase. Verifică setările din Streamlit Secrets.")
    st.stop()

if "autentificat" not in st.session_state:
    st.session_state.autentificat = False
if "nume_garaj" not in st.session_state:
    st.session_state.nume_garaj = ""

if not st.session_state.autentificat:
    st.title("🔐 Acces Platformă — Diagnoză Auto PRO")
    with st.form("form_login"):
        garaj_input = st.text_input("Nume Garaj / Mecanic *", placeholder="ex: Service Auto Slatina")
        parola_input = st.text_input("Parolă de acces *", type="password")
        if st.form_submit_button("🔓 Intră în aplicație", use_container_width=True):
            if not garaj_input.strip():
                st.error("Introdu numele garajului!")
            elif parola_input == st.secrets.get("PAROLA_ACCES", "Atelier2026"):
                st.session_state.autentificat = True
                st.session_state.nume_garaj = garaj_input.strip()
                st.rerun()
            else:
                st.error("❌ Parolă incorectă!")
    st.stop()

if "pagina_curenta" not in st.session_state:
    st.session_state.pagina_curenta = "🔍 Caută Cazuri / Istoric"
if "mesaj_succes" not in st.session_state:
    st.session_state.mesaj_succes = None

def extrage_date_pdf(fisier_pdf):
    reader = PdfReader(fisier_pdf)
    text_complet = "".join((page.extract_text() or "") + "\n" for page in reader.pages)
    coduri_gasite = re.findall(r'\b[PBCU][0-9A-F]{4}\b', text_complet)
    return ", ".join(sorted(set(coduri_gasite))), text_complet

def urca_fisier_cloud(fisier, subfolder):
    if fisier is None:
        return ""
    nume_curat = re.sub(r'[^a-zA-Z0-9_.-]', '_', fisier.name)
    cale_storage = f"{subfolder}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{nume_curat}"
    supabase.storage.from_("atasamente").upload(path=cale_storage, file=fisier.getvalue(), file_options={"content-type": fisier.type})
    return supabase.storage.from_("atasamente").get_public_url(cale_storage)

st.title("🔧 Diagnoză Auto PRO — Bază de Date Online")
st.sidebar.markdown(f"👤 Conectat ca: *{st.session_state.nume_garaj}*")

optiuni_meniu = ["🔍 Caută Cazuri / Istoric", "📄 Import Raport PDF", "➕ Adaugă Caz Manual"]
meniu_ales = st.sidebar.radio("📌 MENIU PRINCIPAL", optiuni_meniu, index=optiuni_meniu.index(st.session_state.pagina_curenta))

if st.sidebar.button("🚪 Deconectare"):
    st.session_state.autentificat = False
    st.session_state.nume_garaj = ""
    st.rerun()

if meniu_ales != st.session_state.pagina_curenta:
    st.session_state.pagina_curenta = meniu_ales
    st.rerun()

if st.session_state.mesaj_succes:
    st.toast(st.session_state.mesaj_succes, icon="✅")
    st.success(st.session_state.mesaj_succes)
    st.session_state.mesaj_succes = None

if st.session_state.pagina_curenta == "🔍 Caută Cazuri / Istoric":
    toate_cazurile = supabase.table("cazuri").select("*").order("id", desc=True).execute().data or []
    total_cazuri = len(toate_cazurile)
    rezolvate = sum(1 for c in toate_cazurile if c.get("status") == "Rezolvat")
    in_lucru = total_cazuri - rezolvate

    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{total_cazuri}</div><div class="metric-label">Total Cazuri în Rețea</div></div>', unsafe_allow_html=True)
    with col_s2:
        st.markdown(f'<div class="metric-card" style="border-left-color: #2EA043;"><div class="metric-value">{rezolvate}</div><div class="metric-label">Cazuri Rezolvate</div></div>', unsafe_allow_html=True)
    with col_s3:
        st.markdown(f'<div class="metric-card" style="border-left-color: #D29922;"><div class="metric-value">{in_lucru}</div><div class="metric-label">În Investigație / Așteptare</div></div>', unsafe_allow_html=True)

    st.write("")
    st.subheader("🔎 Căutare rapidă în baza de date")
    with st.form("formular_cautare"):
        col_c1, col_c2, col_c3 = st.columns([2, 2, 1])
        with col_c1:
            cautare_cod = st.text_input("Cod de eroare (DTC) / Cod Motor / Marcă", placeholder="ex: P0299, U0100, CFFB")
        with col_c2:
            cautare_rezolvare = st.text_input("Cuvânt cheie în Rezolvare / Investigații", placeholder="ex: furtun, mufa, EGR, releu")
        with col_c3:
            st.write("")
            st.write("")
            st.form_submit_button("🔍 Caută", use_container_width=True)

    termen_cod = cautare_cod.strip().lower()
    termen_rez = cautare_rezolvare.strip().lower()
    rezultate = [
        caz for caz in toate_cazurile
        if (not termen_cod or termen_cod in f"{caz.get('coduri_eroare','')} {caz.get('cod_motor','')} {caz.get('marca_model','')}".lower())
        and (not termen_rez or termen_rez in f"{caz.get('rezolvare','')} {caz.get('investigatii','')} {caz.get('simptome','')}".lower())
    ]

    st.markdown(f"**Rezultate afișate:** `{len(rezultate)}` cazuri")
    for row in rezultate:
        culoare = "🟢" if row.get("status") == "Rezolvat" else "🟡"
        garaj_info = f" | Garaj: {row.get('garaj')}" if row.get("garaj") else ""
        titlu = f"{culoare} [{row.get('coduri_eroare')}] {row.get('marca_model')} ({row.get('an_fabricatie')}) — Motor: {row.get('cod_motor')}{garaj_info} | {row.get('data_ora')}"
        with st.expander(titlu):
            col_a, col_b = st.columns([2, 1])
            with col_a:
                st.markdown(f"**Status:** `{row.get('status')}` | **Adăugat de:** `{row.get('garaj', 'Nespecificat')}`")
                st.markdown(f"**Simptome:** {row.get('simptome') or 'Nespecificat'}")
                st.info(f"**Investigații făcute:**\n\n{row.get('investigatii')}")
                st.success(f"**Rezolvare:**\n\n{row.get('rezolvare') or 'Încă nu a fost adăugată o rezolvare.'}")
                if row.get("url_pdf"):
                    st.link_button("📄 Deschide / Descarcă Raportul PDF", row.get("url_pdf"))
            with col_b:
                if row.get("url_poza"):
                    st.image(row.get("url_poza"), caption="Imagine atașată", use_container_width=True)
                else:
                    st.caption("Fără imagini atașate.")

elif st.session_state.pagina_curenta == "📄 Import Raport PDF":
    st.header("Import automat din raport PDF")
    st.write("Încarcă raportul PDF salvat de pe testerul de diagnoză. Programul extrage automat codurile de eroare (fără VIN).")
    pdf_incarcat = st.file_uploader("Alege raportul PDF", type=["pdf"])
    if pdf_incarcat is not None:
        coduri_extrase, text_brut = extrage_date_pdf(pdf_incarcat)
        with st.expander("👁️ Vezi textul extras din PDF (pentru verificare)"):
            st.text(text_brut[:2000])
        with st.form("formular_pdf", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                marca_model = st.text_input("Marcă și Model *", placeholder="ex: Audi A4 B8")
                an_fabricatie = st.number_input("An fabricație", min_value=1980, max_value=2030, value=2014)
            with col2:
                cod_motor = st.text_input("Cod Motor *", placeholder="ex: CGLC 2.0 TDI")
                coduri_eroare = st.text_input("Coduri DTC (extrase automat) *", value=coduri_extrase)
                status = st.selectbox("Status caz", ["În investigație", "Rezolvat", "Așteaptă piese"])
            simptome = st.text_area("Simptome reclamate de client")
            investigatii = st.text_area("Investigații și măsurători făcute *", value="Scanare inițială efectuată (raport PDF atașat).")
            rezolvare = st.text_area("Concluzie și Rezolvare finală")
            poza = st.file_uploader("Atașează și o poză (opțional)", type=["jpg", "jpeg", "png"])
            if st.form_submit_button("💾 Salvează Cazul și Raportul PDF", use_container_width=True):
                if not marca_model or not cod_motor or not investigatii:
                    st.error("Completează Marcă/Model, Cod Motor și Investigații!")
                else:
                    with st.spinner("Se salvează în cloud..."):
                        url_pdf = urca_fisier_cloud(pdf_incarcat, "pdf")
                        url_poza = urca_fisier_cloud(poza, "poze")
                        supabase.table("cazuri").insert({
                            "data_ora": datetime.now().strftime("%d-%m-%Y %H:%M"),
                            "garaj": st.session_state.nume_garaj,
                            "marca_model": marca_model.strip(),
                            "an_fabricatie": int(an_fabricatie),
                            "cod_motor": cod_motor.strip().upper(),
                            "coduri_eroare": coduri_eroare.strip().upper(),
                            "simptome": simptome.strip(),
                            "investigatii": investigatii.strip(),
                            "rezolvare": rezolvare.strip(),
                            "status": status,
                            "url_poza": url_poza,
                            "url_pdf": url_pdf
                        }).execute()
                    st.session_state.mesaj_succes = f"Cazul pentru {marca_model} ({coduri_eroare.upper()}) a fost publicat online!"
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
        poza = st.file_uploader("Atașează o poză", type=["jpg", "jpeg", "png"])
        if st.form_submit_button("💾 Salvează Cazul", use_container_width=True):
            if not marca_model or not cod_motor or not coduri_eroare or not investigatii:
                st.error("Completează câmpurile obligatorii marcate cu *!")
            else:
                with st.spinner("Se salvează în cloud..."):
                    url_poza = urca_fisier_cloud(poza, "poze")
                    supabase.table("cazuri").insert({
                        "data_ora": datetime.now().strftime("%d-%m-%Y %H:%M"),
                        "garaj": st.session_state.nume_garaj,
                        "marca_model": marca_model.strip(),
                        "an_fabricatie": int(an_fabricatie),
                        "cod_motor": cod_motor.strip().upper(),
                        "coduri_eroare": coduri_eroare.strip().upper(),
                        "simptome": simptome.strip(),
                        "investigatii": investigatii.strip(),
                        "rezolvare": rezolvare.strip(),
                        "status": status,
                        "url_poza": url_poza,
                        "url_pdf": ""
                    }).execute()
                st.session_state.mesaj_succes = f"Cazul pentru {marca_model} ({coduri_eroare.upper()}) a fost publicat online!"
                st.session_state.pagina_curenta = "🔍 Caută Cazuri / Istoric"
                st.rerun()
