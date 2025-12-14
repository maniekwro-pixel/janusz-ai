import streamlit as st
import google.generativeai as genai
from PIL import Image
import os
import datetime
import gspread
from google.oauth2.service_account import Credentials
import re
import json

# ================= KONFIGURACJA =================
st.set_page_config(page_title="Janusz 2.5", page_icon="🚀")
st.title("🚀 Janusz 2.5: Wersja Przyszłości")

# 1. Konfiguracja GEMINI (AI)
try:
    # Szukamy klucza wszędzie gdzie się da
    API_KEY = st.secrets.get("GEMINI_API_KEY", None)
    if not API_KEY and "gcp_service_account" in st.secrets:
        if "GEMINI_API_KEY" in st.secrets["gcp_service_account"]:
             API_KEY = st.secrets["gcp_service_account"]["GEMINI_API_KEY"]
             
    if not API_KEY:
        API_KEY = "BRAK_KLUCZA" 

    genai.configure(api_key=API_KEY)
except Exception as e:
    st.error(f"Błąd konfiguracji AI: {e}")

# ================= FUNKCJE LOGICZNE =================

def get_janusz_response(user_input, attachment=None):
    try:
        # 👇 TUTAJ JEST ZMIANA! Używamy Twojego najnowszego modelu
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash", 
            system_instruction="""
            Jesteś Januszem, księgowym.
            Analizuj dokumenty: Data, Sprzedawca, Kwota Brutto.
            Na końcu napisz w nowej linii: "KWOTA: [liczba]".
            """
        )
        content = [user_input]
        if attachment:
            content.append(attachment)
        response = model.generate_content(content)
        return response.text
    except Exception as e:
        # Obsługa błędu "Quota" (Limity)
        if "429" in str(e):
            return "☕ Janusz musi wypić kawę (Limit zapytań wyczerpany). Odczekaj minutę i spróbuj ponownie."
        return f"Błąd AI: {str(e)}"

# --- PANCERNA FUNKCJA LOGOWANIA (GCP) ---
def get_google_creds():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    # OPCJA 1: Format TOML [gcp_service_account]
    if "gcp_service_account" in st.secrets:
        try:
            creds_dict = dict(st.secrets["gcp_service_account"])
            # Fix na entery w kluczu
            if "private_key" in creds_dict and "\\n" in creds_dict["private_key"]:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            return Credentials.from_service_account_info(creds_dict, scopes=scopes)
        except Exception:
            pass

    # OPCJA 2: Format JSON string
    if "GOOGLE_CREDENTIALS" in st.secrets:
        try:
            val = st.secrets["GOOGLE_CREDENTIALS"]
            creds_dict = json.loads(val) if isinstance(val, str) else val
            return Credentials.from_service_account_info(creds_dict, scopes=scopes)
        except Exception:
            pass
            
    # OPCJA 3: Plik lokalny
    if os.path.exists("credentials.json"):
        return Credentials.from_service_account_file("credentials.json", scopes=scopes)
    
    return None

def save_to_google_sheets(pytanie, odpowiedz, kwota_str):
    try:
        credentials = get_google_creds()
        if not credentials:
            st.error("❌ Błąd: Nie widzę kluczy do Google Sheets.")
            return False

        client = gspread.authorize(credentials)
        sheet = client.open("Wydatki Janusza").sheet1
        
        data_teraz = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        sheet.append_row([data_teraz, pytanie, odpowiedz, kwota_str])
        return True

    except Exception as e:
        st.error(f"Błąd zapisu do Excela: {e}")
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
    if not uploaded_image and len(user_prompt) < 2:
        st.warning("Pusto!")
    else:
        with st.spinner("Janusz 2.5 analizuje..."):
            # 1. AI
            gemini_att = uploaded_image if uploaded_image else None
            resp = get_janusz_response(user_prompt, gemini_att)
            
            st.success("Janusz:")
            st.write(resp)
            
            # 2. Zapis (Tylko jeśli nie ma błędu kawy)
            if "Janusz musi wypić kawę" not in resp and "Błąd AI" not in resp:
                kwota = "0.00"
                match = re.search(r"KWOTA:\s*([\d\.,]+)", resp)
                if match: kwota = match.group(1).replace(",", ".")
                
                if save_to_google_sheets(user_prompt, resp, kwota):
                    st.toast("✅ Zapisano w Arkuszu!", icon="🔥")


