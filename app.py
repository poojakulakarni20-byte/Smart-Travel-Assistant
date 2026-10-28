import csv
import os
import re
import time
import uuid
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from openai import (
    OpenAI,
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)

import database


# --------------------------------------------------
# 1. PROJECT PATHS AND PAGE SETTINGS
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_FILE = BASE_DIR / "knowledge.txt"
DESTINATIONS_FILE = BASE_DIR / "destinations.csv"

st.set_page_config(
    page_title="Smart Travel Assistant Karnataka",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_dotenv(BASE_DIR / ".env")
database.initialize_database()


# --------------------------------------------------
# 2. LOAD API SETTINGS
# --------------------------------------------------

def get_setting(name, default=""):
    value = os.getenv(name)
    if value:
        return value

    try:
        secret_value = st.secrets.get(name, default)
        return str(secret_value) if secret_value is not None else default
    except Exception:
        return default


API_KEY = get_setting("OPENAI_API_KEY")
MODEL = get_setting("OPENAI_MODEL", "gpt-4o-mini")

client = None
if API_KEY:
    client = OpenAI(api_key=API_KEY, timeout=25.0, max_retries=0)


# --------------------------------------------------
# 3. LOAD CUSTOM KNOWLEDGE
# --------------------------------------------------

def load_knowledge():
    if not KNOWLEDGE_FILE.is_file():
        return ""
    return KNOWLEDGE_FILE.read_text(encoding="utf-8").strip()


KNOWLEDGE = load_knowledge()


# --------------------------------------------------
# 4. LOAD AND NORMALIZE DESTINATION DATA
# --------------------------------------------------

def canonical_category(value):
    """Convert common category spellings to consistent app categories."""
    value = str(value or "").strip().casefold()
    value = re.sub(r"\s+", " ", value)

    aliases = {
        "nature": "Nature",
        "natural": "Nature",
        "heritage": "Heritage",
        "historical": "Heritage",
        "history": "Heritage",
        "beach": "Beach",
        "beaches": "Beach",
        "coastal": "Coastal",
        "coast": "Coastal",
