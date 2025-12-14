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
st.set_page_config(page_title="Janusz Global", page_icon="🌍")
st.title("🌍 Janusz: Księgowość Globalna")

# 1. Konfiguracja GEMINI (AI)
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    API_KEY = "TU_WPISZ_KLUCZ_LOKALNY_JESLI_TRZEBA"

genai.configure(api_key=API_KEY)

# ================= FUNKCJE LOGICZNE =================

def get_janusz_response(user_input, attachment=None):
    model = genai.GenerativeModel(
        model_name="gemini-flash-latest",
        system_instruction="""
        Jesteś Januszem, starszym księgowym.
        1. Analizuj dokumenty i wyciągaj: Datę, Sprzedawcę, Kwotę Brutto.
        2. Bądź marudny, ale krótko i na temat.
        3. Na końcu ZAWSZE napisz w nowej linii: "KWOTA: [liczba]".
        """
    )
    content = [user_input]
    if attachment:
        content.append(attachment)
    response = model.generate_content(content)
    return response.text

# --- NOWA, PANCERNA FUNKCJA LOGOWANIA ---
def get_google_creds():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    # Sytuacja A: Jesteśmy w chmurze (Streamlit Cloud)
    if "GOOGLE_CREDENTIALS" in st.secrets:
        try:
            # Pobieramy treść z sekretów
            secret_value = st.secrets["GOOGLE_CREDENTIALS"]
            
            # Jeśli user wkleił to jako string (w cudzysłowach), parsujemy JSON
            if isinstance(secret_value, str):
                creds_dict = json.loads(secret_value)
            else:
                # Czasami Streamlit sam parsuje TOML na dict
                creds_dict = secret_value
                
            return Credentials.from_service_account_info(creds_dict, scopes=scopes)
        except Exception as e:
            st.error(f"Błąd parsowania sekretów w chmurze: {e}")
            return None
    
    # Sytuacja B: Jesteśmy na komputerze (Lokalnie)
    elif os.path.exists("credentials.json"):
        return Credentials.from_service_account_file("credentials.json", scopes=scopes)
    
    return None

def save_to_google_sheets(pytanie, odpowiedz, kwota_str):
    try:
        credentials = get_google_creds()
        
        if not credentials:
            st.error("❌ Błąd: Nie znaleziono kluczy do Google (ani w pliku, ani w sekretach).")
            return False

        client = gspread.authorize(credentials)
        
        # Otwieranie arkusza
        sheet = client.open("Wydatki Janusza").sheet1
        
        data_teraz = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        sheet.append_row([data_teraz, pytanie, odpowiedz, kwota_str])
        return True

    except Exception as e:
        st.error(f"Błąd zapisu do Google: {e}")
        return False

# ================= INTERFEJS =================

with st.sidebar:
    st.header("📂 Źródło danych")
    input_method = st.radio("Metoda:", ["Wgraj plik", "Aparat", "Mikrofon"])

uploaded_image = None
audio_data = None

if input_method == "Wgraj plik":
    f = st.file_uploader("Plik", type=["jpg", "png", "pdf"])
    if f: uploaded_image = Image.open(f)
    
elif input_method == "Aparat":
    f = st.camera_input("Foto")
    if f: uploaded_image = Image.open(f)
    
elif input_method == "Mikrofon":
    audio_data = st.audio_input("Głos")

st.divider()
user_prompt = st.text_area("Polecenie:", value="Rozlicz to." if (uploaded_image or audio_data) else "")
run_btn = st.button("🚀 Wyślij", type="primary")

if run_btn or (audio_data and not st.session_state.get('audio_processed')):
    if audio_data: st.session_state['audio_processed'] = True
    
    if user_prompt or uploaded_image or audio_data:
        with st.spinner("Janusz pracuje..."):
            gemini_att = uploaded_image if uploaded_image else ({"mime_type": "audio/wav", "data": audio_data.read()} if audio_data else None)
            
            try:
                # 1. Analiza AI
                resp = get_janusz_response(user_prompt, gemini_att)
                st.success("Janusz:")
                st.write(resp)
                
                # (Usunięto sekcję Audio/TTS)
                
                # 2. Wyciąganie Kwoty
                kwota = "0.00"
                match = re.search(r"KWOTA:\s*([\d\.,]+)", resp)
                if match: kwota = match.group(1).replace(",", ".")
                
                # 3. Zapis do Chmury
                if kwota != "0.00" or "zapisz" in user_prompt.lower():
                    if save_to_google_sheets(user_prompt, resp, kwota):
                        st.toast("✅ Zapisano w Arkuszu!", icon="☁️")
                        
            except Exception as e:
                st.error(f"Błąd aplikacji: {e}")

if not audio_data: st.session_state['audio_processed'] = False
