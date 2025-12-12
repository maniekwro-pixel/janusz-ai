import streamlit as st
import google.generativeai as genai
from PIL import Image
from gtts import gTTS
import io
import csv
import os
import re

# ================= KONFIGURACJA CHMUROWA =================
st.set_page_config(page_title="Janusz w Chmurze", page_icon="☁️")
st.title("☁️ Janusz: Globalny Maruda")

# Tutaj dzieje się magia bezpieczeństwa.
# Kod szuka klucza w "sejfu" serwera (st.secrets), a nie w pliku.
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except FileNotFoundError:
    st.warning("⚠️ Uruchamiasz to lokalnie i nie masz pliku .streamlit/secrets.toml? Spokojnie, w chmurze zadziała, jeśli wpiszesz klucz w ustawieniach.")
    st.stop()
except KeyError:
    st.error("❌ Błąd konfiguracji: Nie znaleziono klucza 'GEMINI_API_KEY' w sekretach.")
    st.stop()

genai.configure(api_key=API_KEY)
# =========================================================

def get_janusz_response(user_input, attachment=None):
    model = genai.GenerativeModel(
        model_name="gemini-flash-latest",
        system_instruction="""
        Jesteś Januszem. Działasz teraz w chmurze, więc czujesz się ważny, ale dalej marudzisz.
        1. Odpowiedzi mają być krótkie i konkretne (do czytania na telefonie).
        2. Jeśli dostaniesz zdjęcie dokumentu, wyciągnij kwotę i datę.
        3. Jeśli dostaniesz nagranie, streść polecenie.
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
    except Exception as e:
        return None

# --- INTERFEJS ---

with st.sidebar:
    st.header("⚙️ Narzędzia")
    input_method = st.radio("Tryb pracy:", ["Aparat (Zdjęcie)", "Mikrofon (Głos)"])

uploaded_image = None
audio_input = None
user_prompt = ""

# --- WEJŚCIE DANYCH ---

if input_method == "Aparat (Zdjęcie)":
    img_file = st.camera_input("Zrób zdjęcie")
    if img_file:
        uploaded_image = Image.open(img_file)

elif input_method == "Mikrofon (Głos)":
    audio_input = st.audio_input("Nagraj polecenie")

# --- URUCHOMIENIE ---

if uploaded_image:
    user_prompt = st.text_input("Co mam z tym zrobić?", value="Rozlicz to.")

if audio_input:
    user_prompt = "Odsłuchaj i wykonaj polecenie."

# Logika przycisku / startu
start_button = st.button("🚀 Wyślij do Janusza")

# Warunek startu: Kliknięto przycisk LUB nagrano audio (i jeszcze go nie przetworzono)
if start_button or (audio_input and not st.session_state.get('audio_processed')):
    
    if audio_input:
        st.session_state['audio_processed'] = True

    with st.spinner("Łączę z chmurą..."):
        try:
            gemini_attachment = None
            if uploaded_image:
                gemini_attachment = uploaded_image
            elif audio_input:
                gemini_attachment = {"mime_type": "audio/wav", "data": audio_input.read()}

            response_text = get_janusz_response(user_prompt, gemini_attachment)

            st.success("Janusz mówi:")
            st.write(response_text)

            audio_response = text_to_speech(response_text)
            if audio_response:
                st.audio(audio_response, format='audio/mp3', autoplay=True)

            # UWAGA: W chmurze pliki CSV są tymczasowe (znikają po restarcie apki)
            # Ale zostawiamy to, żebyś widział, że mechanizm działa.
            if "PLN" in response_text or "zł" in response_text:
                with open("wydatki_temp.csv", "a", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f, delimiter=';')
                    writer.writerow([user_prompt, response_text])
                st.info("ℹ️ Zapisano w pliku tymczasowym na serwerze.")

        except Exception as e:
            st.error(f"Błąd: {e}")

if not audio_input:
    st.session_state['audio_processed'] = False