import streamlit as st
import google.generativeai as genai
from PIL import Image
from gtts import gTTS
import io
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
    API_KEY = "TU_WPISZ_KLUCZ_JEŚLI_TESTUJESZ_LOKALNIE_BEZ_SEKRETOW"

genai.configure(api_key=API_KEY)

# ================= FUNKCJE LOGICZNE =================

def get_janusz_response(user_input, attachment=None):
    model = genai.GenerativeModel(
        model_name="gemini-flash-latest",
        system_instruction="""
        Jesteś Januszem, starszym księgowym.
        1. Analizuj dokumenty i wyciągaj: Datę, Sprzedawcę, Kwotę Brutto.
        2. Bądź marudny.
        3. Na końcu ZAWSZE napisz w nowej linii: "KWOTA: [liczba]".
        """
    )
    content = [user_input]
    if attachment:
        content.append(attachment)
    response = model.generate_content(content)
    return response.text

def text_to_speech(text):
    try:
        tts = gTTS(text=text, lang='pl')
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        audio_fp.seek(0)
        return audio_fp
    except:
        return None

# --- HYBRYDOWA FUNKCJA LOGOWANIA DO GOOGLE ---
def get_google_creds():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    # Opcja 1: Chmura (Sekrety)
    if "GOOGLE_CREDENTIALS" in st.secrets:
        secret_json = st.secrets["GOOGLE_CREDENTIALS"]
        # Parsujemy string z sekretów z powrotem na słownik (JSON object)
        creds_dict = json.loads(secret_json)
        return Credentials.from_service_account_info(creds_dict, scopes=scopes)
    
    # Opcja 2: Lokalny plik (Komputer Mariusza)
    elif os.path.exists("credentials.json"):
        return Credentials.from_service_account_file("credentials.json", scopes=scopes)
    
    return None

def save_to_google_sheets(pytanie, odpowiedz, kwota_str):
    try:
        credentials = get_google_creds()
        
        if not credentials:
            st.error("❌ Brak kluczy do Google (nie znaleziono ani sekretów, ani pliku json).")
            return False

        client = gspread.authorize(credentials)
        
        # Pamiętaj o wielkości liter w nazwie arkusza! ;)
        sheet = client.open("Wydatki Janusza").sheet1
        
        data_teraz = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        sheet.append_row([data_teraz, pytanie, odpowiedz, kwota_str])
        return True

    except Exception as e:
        st.error(f"Błąd zapisu: {e}")
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
        with st.spinner("Przetwarzanie..."):
            gemini_att = uploaded_image if uploaded_image else ({"mime_type": "audio/wav", "data": audio_data.read()} if audio_data else None)
            
            try:
                # AI
                resp = get_janusz_response(user_prompt, gemini_att)
                st.success("Janusz:")
                st.write(resp)
                
                # Audio
                audio = text_to_speech(resp)
                if audio: st.audio(audio, format='audio/mp3', autoplay=True)
                
                # Zapis
                kwota = "0.00"
                match = re.search(r"KWOTA:\s*([\d\.,]+)", resp)
                if match: kwota = match.group(1).replace(",", ".")
                
                if kwota != "0.00" or "zapisz" in user_prompt.lower():
                    if save_to_google_sheets(user_prompt, resp, kwota):
                        st.toast("✅ Zapisano w Chmurze!", icon="🌍")
                        
            except Exception as e:
                st.error(f"Błąd: {e}")

if not audio_data: st.session_state['audio_processed'] = False