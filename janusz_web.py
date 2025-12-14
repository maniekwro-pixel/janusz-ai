import streamlit as st
import google.generativeai as genai
import os

st.set_page_config(page_title="Janusz Diagnosta", page_icon="🧬")
st.title("🧬 Lista Dostępnych Modeli")

# 1. Konfiguracja Klucza (Twoja sprawdzona metoda)
try:
    API_KEY = st.secrets.get("GEMINI_API_KEY", None)
    if not API_KEY and "gcp_service_account" in st.secrets:
        API_KEY = st.secrets["gcp_service_account"].get("GEMINI_API_KEY")
    
    if not API_KEY:
        st.error("❌ Brak klucza API w sekretach!")
        st.stop()
        
    genai.configure(api_key=API_KEY)
except Exception as e:
    st.error(f"Błąd klucza: {e}")
    st.stop()

# 2. Sprawdzenie wersji biblioteki
import google.generativeai
st.info(f"📦 Wersja biblioteki google-generativeai: **{google.generativeai.__version__}**")
st.caption("Jeśli wersja jest niższa niż 0.7.0, to nie zobaczymy modelu Flash.")

# 3. Pytamy Google: "Co masz na stanie?"
st.write("---")
st.write("📋 **Lista modeli dostępnych dla Twojego klucza:**")

try:
    dostepne = []
    for m in genai.list_models():
        # Szukamy tylko modeli, które potrafią pisać (generateContent)
        if 'generateContent' in m.supported_generation_methods:
            st.code(m.name)
            dostepne.append(m.name)
            
    st.write("---")
    
    # 4. Automatyczna sugestia
    if "models/gemini-1.5-flash" in dostepne:
        st.success("✅ Widzę model 'models/gemini-1.5-flash'! Użyj nazwy: `gemini-1.5-flash`")
    elif "models/gemini-pro" in dostepne:
        st.warning("⚠️ Flasha brak, ale jest 'gemini-pro'. To starszy, ale solidny model.")
    else:
        st.error("❌ Nie widzę żadnych standardowych modeli tekstowych.")

except Exception as e:
    st.error(f"Błąd podczas pobierania listy: {e}")
