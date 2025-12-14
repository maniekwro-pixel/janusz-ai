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
st.set_page_config(page_title="Janusz Księgowy", page_icon="📈")
st.title("📈 Janusz: Twój Osobisty Księgowy")

# 1. Konfiguracja GEMINI (AI)
# Kod szuka klucza niezależnie od tego, gdzie go wkleiłeś w sekretach
try:
    API_KEY = st.secrets.get("GEMINI_API_KEY", None)
    if not API_KEY:
        # Fallback: Może jest w sekcji gcp przez przypadek?
        if "gcp_service_account" in st.secrets and "GEMINI_API_KEY" in st.secrets["gcp_service_account"]:
             API_KEY = st.secrets["gcp_service_account"]["GEMINI_API_KEY"]
             
    if not API_KEY:
        API_KEY = "BRAK_KLUCZA_LOKALNIE" 

    genai.configure(api_key=API_KEY)
except Exception as e:
    st.error(f"Błąd konfiguracji AI: {e}")

# ================= FUNKCJE LOGICZNE =================

def get_janusz_response(user_input, attachment=None):
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash", 
            system_instruction="""
            Jesteś Januszem, księgowym.
            Analizuj dokumenty: Data, Sprzedawca, Kwota Brutto.
            Na końcu napisz w nowej linii: "KWOTA: [liczba]".
            
            ZASADY:
            1. Wyciągnij: Datę, Sprzedawcę i Kwotę Brutto.
            2. Jeśli zdjęcie jest niewyraźne, pomarudź trochę.
            3. Na samym końcu odpowiedzi, w nowej linii napisz: "KWOTA: [liczba]".
               Format liczby: np. 123.45 (kropka jako separator).
            """
        )
        content = [user_input]
        if attachment:
            content.append(attachment)
        response = model.generate_content(content)
        return response.text
    except Exception as e:
        return f"Janusz ma przerwę na kawę (Błąd AI): {str(e)}"

# --- PANCERNA FUNKCJA LOGOWANIA ---
def get_google_creds():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    # OPCJA 1: Format TOML [gcp_service_account] (Ten, który Ci teraz działa)
    if "gcp_service_account" in st.secrets:
        try:
            creds_dict = dict(st.secrets["gcp_service_account"])
            # Zabezpieczenie na wszelki wypadek
            if "private_key" in creds_dict and "\\n" in creds_dict["private_key"]:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            return Credentials.from_service_account_info(creds_dict, scopes=scopes)
        except Exception:
            pass 

    # OPCJA 2: Stary format JSON string (Dla kompatybilności wstecznej)
    if "GOOGLE_CREDENTIALS" in st.secrets:
        try:
            secret_value = st.secrets["GOOGLE_CREDENTIALS"]
            if isinstance(secret_value, str):
                creds_dict = json.loads(secret_value)
            else:
                creds_dict = secret_value
            return Credentials.from_service_account_info(creds_dict, scopes=scopes)
        except Exception:
            pass

    # OPCJA 3: Plik lokalny (Komputer)
    if os.path.exists("credentials.json"):
        return Credentials.from_service_account_file("credentials.json", scopes=scopes)
    
    return None

def save_to_google_sheets(pytanie, odpowiedz, kwota_str):
    try:
        credentials = get_google_creds()
        
        if not credentials:
            st.error("❌ Błąd: Nie można połączyć się z Excelem (Brak kluczy).")
            return False

        client = gspread.authorize(credentials)
        sheet = client.open("Wydatki Janusza").sheet1
        
        data_teraz = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        sheet.append_row([data_teraz, pytanie, odpowiedz, kwota_str])
        return True

    except Exception as e:
        st.error(f"Nie udało się zapisać: {e}")
        return False

# ================= INTERFEJS =================

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2910/2910768.png", width=100)
    st.header("📂 Źródło danych")
    input_method = st.radio("Wybierz metodę:", ["Wgraj plik", "Aparat"])

uploaded_image = None

if input_method == "Wgraj plik":
    f = st.file_uploader("Wrzuć skan/zdjęcie", type=["jpg", "png", "pdf", "jpeg"])
    if f: uploaded_image = Image.open(f)
elif input_method == "Aparat":
    f = st.camera_input("Zrób zdjęcie")
    if f: uploaded_image = Image.open(f)

st.divider()
user_prompt = st.text_area("Polecenie dla księgowego:", value="Rozlicz to i wpisz w koszty." if uploaded_image else "")
run_btn = st.button("🚀 Wyślij do Janusza", type="primary")

if run_btn:
    if not uploaded_image and len(user_prompt) < 2:
        st.warning("Panie, ale co ja mam z tym zrobić? Daj jakieś zdjęcie albo wpisz coś.")
    else:
        with st.spinner("Janusz szuka okularów i liczy..."):
            # 1. AI
            gemini_att = uploaded_image if uploaded_image else None
            resp = get_janusz_response(user_prompt, gemini_att)
            
            st.success("💬 Janusz odpowiada:")
            st.write(resp)
            
            # 2. Wyciąganie kwoty
            kwota = "0.00"
            match = re.search(r"KWOTA:\s*([\d\.,]+)", resp)
            if match: kwota = match.group(1).replace(",", ".")
            
            # 3. Zapis
            if "Błąd AI" not in resp:
                if save_to_google_sheets(user_prompt, resp, kwota):
                    st.toast("✅ Zapisano w Arkuszu Google!", icon="📂")
                    st.balloons()


