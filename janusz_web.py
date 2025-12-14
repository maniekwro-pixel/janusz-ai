import streamlit as st
import google.generativeai as genai
from PIL import Image
import os
import datetime
import gspread
from google.oauth2.service_account import Credentials
import re

# ================= KONFIGURACJA =================
st.set_page_config(page_title="Janusz Global", page_icon="🌍")
st.title("🌍 Janusz: Księgowość Globalna")

# 1. Konfiguracja GEMINI (AI)
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    API_KEY = "BRAK_KLUCZA" # Lokalnie wpisz tu swój klucz do testów

genai.configure(api_key=API_KEY)

# ================= FUNKCJE LOGICZNE =================

def get_janusz_response(user_input, attachment=None):
    model = genai.GenerativeModel(
        model_name="gemini-flash-latest",
        system_instruction="""
        Jesteś Januszem, księgowym.
        Analizuj dokumenty: Data, Sprzedawca, Kwota Brutto.
        Na końcu napisz: "KWOTA: [liczba]".
        """
    )
    content = [user_input]
    if attachment:
        content.append(attachment)
    response = model.generate_content(content)
    return response.text

# --- NOWA FUNKCJA LOGOWANIA (ODPORNA NA BŁĘDY) ---
def get_google_creds():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    # SPOSÓB 1: CHMURA (Nowy format TOML)
    if "gcp_service_account" in st.secrets:
        try:
            # Streamlit sam zamienia sekcję [gcp_service_account] na słownik!
            # Tworzymy kopię, żeby nie psuć oryginału
            creds_dict = dict(st.secrets["gcp_service_account"])
            
            # 🔧 AUTONAPRAWA KLUCZA PRYWATNEGO
            # Zamieniamy dosłowne znaczki "\n" na prawdziwe nowe linie
            if "\\n" in creds_dict["private_key"]:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
            return Credentials.from_service_account_info(creds_dict, scopes=scopes)
        except Exception as e:
            st.error(f"⚠️ Błąd odczytu sekretów TOML: {e}")
            return None

    # SPOSÓB 2: Lokalny plik (Komputer)
    elif os.path.exists("credentials.json"):
        return Credentials.from_service_account_file("credentials.json", scopes=scopes)
    
    return None

def save_to_google_sheets(pytanie, odpowiedz, kwota_str):
    try:
        credentials = get_google_creds()
        
        if not credentials:
            st.error("❌ Błąd krytyczny: Brak dostępu do Google (Sprawdź sekrety).")
            return False

        client = gspread.authorize(credentials)
        sheet = client.open("Wydatki Janusza").sheet1 # <-- Upewnij się co do nazwy pliku!
        
        data_teraz = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        sheet.append_row([data_teraz, pytanie, odpowiedz, kwota_str])
        return True

    except Exception as e:
        st.error(f"Błąd zapisu: {e}")
        return False

# ================= INTERFEJS =================

with st.sidebar:
    st.header("📂 Źródło")
    input_method = st.radio("Metoda:", ["Wgraj plik", "Aparat"])

uploaded_image = None

if input_method == "Wgraj plik":
    f = st.file_uploader("Plik", type=["jpg", "png", "pdf"])
    if f: uploaded_image = Image.open(f)
elif input_method == "Aparat":
    f = st.camera_input("Foto")
    if f: uploaded_image = Image.open(f)

st.divider()
user_prompt = st.text_area("Polecenie:", value="Rozlicz to.")
run_btn = st.button("🚀 Wyślij")

if run_btn:
    if not uploaded_image and len(user_prompt) < 5:
        st.warning("Daj mi jakieś dane!")
    else:
        with st.spinner("Przetwarzanie..."):
            try:
                # 1. AI
                if uploaded_image:
                    resp = get_janusz_response(user_prompt, uploaded_image)
                else:
                    resp = get_janusz_response(user_prompt)
                
                st.success("Janusz:")
                st.write(resp)
                
                # 2. Kwota
                kwota = "0.00"
                match = re.search(r"KWOTA:\s*([\d\.,]+)", resp)
                if match: kwota = match.group(1).replace(",", ".")
                
                # 3. Zapis
                if save_to_google_sheets(user_prompt, resp, kwota):
                    st.toast("✅ Zapisano!", icon="☁️")
                    
            except Exception as e:
                st.error(f"Wystąpił błąd: {e}")