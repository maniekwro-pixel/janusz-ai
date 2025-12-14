import streamlit as st
import google.generativeai as genai
from PIL import Image
import os
import datetime
import gspread
from google.oauth2.service_account import Credentials
import re
import json

st.set_page_config(page_title="Janusz Detektyw", page_icon="🕵️‍♂️")
st.title("🕵️‍♂️ Janusz: Tryb Diagnostyczny")

# ================= SEKJA SZPIEGOWSKA (DIAGNOSTYKA) =================
st.info("🔍 ROZPOCZYNAM ANALIZĘ SEKRETÓW...")

# 1. Sprawdzamy co w ogóle jest w sekretach (tylko nazwy kluczy, bez haseł)
dostepne_klucze = list(st.secrets.keys())
st.write(f"📂 Dostępne sekcje w st.secrets: `{dostepne_klucze}`")

# 2. Szukamy klucza Gemini
if "GEMINI_API_KEY" in st.secrets:
    st.write("✅ GEMINI_API_KEY: Znaleziony")
    API_KEY = st.secrets["GEMINI_API_KEY"]
elif "gcp_service_account" in st.secrets and "GEMINI_API_KEY" in st.secrets["gcp_service_account"]:
    st.write("⚠️ GEMINI_API_KEY: Znaleziony, ale ukryty wewnątrz sekcji gcp (przesuń go wyżej!)")
    API_KEY = st.secrets["gcp_service_account"]["GEMINI_API_KEY"]
else:
    st.error("❌ GEMINI_API_KEY: BRAK! (Janusz jest ślepy)")
    API_KEY = None

if API_KEY: genai.configure(api_key=API_KEY)

# 3. Szukamy kluczy Google (Szczegółowo)
st.write("---")
st.write("🔑 Analiza kluczy Google:")

found_creds = None
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# Test formatu TOML [gcp_service_account]
if "gcp_service_account" in st.secrets:
    st.write("Found section '[gcp_service_account]' - Sprawdzam wnętrze...")
    sekcja = st.secrets["gcp_service_account"]
    st.write(f"Klucze w środku: `{list(sekcja.keys())}`")
    
    if "private_key" in sekcja:
        pk = sekcja["private_key"]
        st.write(f"Private Key start: `{pk[:15]}...`")
        if "\\n" in pk:
            st.warning("⚠️ Wykryto 'sztywne' znaki \\n w kluczu. Próbuję naprawić...")
            pk_fixed = pk.replace("\\n", "\n")
            sekcja_fixed = dict(sekcja)
            sekcja_fixed["private_key"] = pk_fixed
            try:
                found_creds = Credentials.from_service_account_info(sekcja_fixed, scopes=scopes)
                st.success("✅ Udało się utworzyć poświadczenia z TOML!")
            except Exception as e:
                st.error(f"❌ Błąd tworzenia poświadczeń: {e}")
        else:
            # Próba bez naprawiania
            try:
                found_creds = Credentials.from_service_account_info(sekcja, scopes=scopes)
                st.success("✅ Udało się utworzyć poświadczenia z TOML (bez zmian)!")
            except Exception as e:
                st.error(f"❌ Błąd: {e}")
    else:
        st.error("❌ Sekcja gcp_service_account istnieje, ale brakuje w niej 'private_key'!")

# ================= KONIEC DIAGNOSTYKI =================

def get_janusz_response(user_input, attachment=None):
    try:
        model = genai.GenerativeModel("gemini-flash-latest")
        content = [user_input]
        if attachment: content.append(attachment)
        response = model.generate_content(content)
        return response.text
    except Exception as e:
        return f"Błąd AI: {e}"

def save_to_google_sheets(pytanie, odpowiedz, kwota_str):
    if not found_creds:
        st.error("⛔ Nie mogę zapisać - brak poświadczeń (patrz raport wyżej).")
        return False
    try:
        client = gspread.authorize(found_creds)
        sheet = client.open("Wydatki Janusza").sheet1
        data_teraz = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        sheet.append_row([data_teraz, pytanie, odpowiedz, kwota_str])
        return True
    except Exception as e:
        st.error(f"Błąd zapisu: {e}")
        return False

# INTERFEJS
st.divider()
with st.sidebar:
    input_method = st.radio("Metoda:", ["Wgraj plik", "Aparat"])

uploaded_image = None
if input_method == "Wgraj plik":
    f = st.file_uploader("Plik", type=["jpg", "png", "pdf"])
    if f: uploaded_image = Image.open(f)
elif input_method == "Aparat":
    f = st.camera_input("Foto")
    if f: uploaded_image = Image.open(f)

user_prompt = st.text_area("Polecenie:", value="Rozlicz to.")
if st.button("🚀 Wyślij"):
    if uploaded_image or user_prompt:
        resp = get_janusz_response(user_prompt, uploaded_image)
        st.write(resp)
        if "KWOTA:" in resp:
            match = re.search(r"KWOTA:\s*([\d\.,]+)", resp)
            kwota = match.group(1).replace(",", ".") if match else "0.00"
            if save_to_google_sheets(user_prompt, resp, kwota):
                st.toast("Zapisano!", icon="✅")
