import os

import streamlit as st
from dotenv import load_dotenv
from google import genai


@st.cache_resource
def get_gemini_client():
    api_key = None

    try:
        api_key = st.secrets.get("GEMINI_API_KEY", None)
    except Exception:
        api_key = None

    if not api_key:
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not found in st.secrets or .env")

    return genai.Client(api_key=api_key)
