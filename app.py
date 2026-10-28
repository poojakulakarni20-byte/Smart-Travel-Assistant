```python
import csv
import os
import re
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

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

# Initialize the database if database.py provides this function.
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

client = OpenAI(api_key=API_KEY, timeout=25.0) if API_KEY else None


# --------------------------------------------------
# 3. LOAD KNOWLEDGE FILE
# --------------------------------------------------

def load_knowledge():
    if not KNOWLEDGE_FILE.is_file():
        return ""

    return KNOWLEDGE_FILE.read_text(encoding="utf-8").strip()


KNOWLEDGE = load_knowledge()


# --------------------------------------------------
# 4. NORMALIZE DESTINATION CATEGORIES
# --------------------------------------------------

def canonical_category(value):
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
        "wildlife": "Wildlife",
        "adventure": "Adventure",
        "city": "City",
        "cities": "City",
        "religious": "Religious",
        "spiritual": "Religious",
    }

    return aliases.get(value, value.title() if value else "Other")


# --------------------------------------------------
# 5. LOAD DESTINATIONS FROM CSV
# --------------------------------------------------

def load_destinations():
    if not DESTINATIONS_FILE.is_file():
        st.error(
            f"Could not find {DESTINATIONS_FILE.name}. "
            "Place it in the same folder as app.py."
        )
        return []

    try:
        with DESTINATIONS_FILE.open(
            "r", encoding="utf-8-sig", newline=""
        ) as file:
            reader = csv.DictReader(file)
            destinations = []

            for row in reader:
                row = {
                    str(key).strip(): str(value or "").strip()
                    for key, value in row.items()
                    if key is not None
                }

                if not row.get("name"):
                    continue

                row["category"] = canonical_category(
                    row.get("category", "")
                )

                destinations.append(row)

            return destinations

    except (OSError, csv.Error) as error:
        st.error(f"Could not read destinations.csv: {error}")
        return []


DESTINATIONS = load_destinations()


# --------------------------------------------------
# 6. PAGE HEADER
# --------------------------------------------------

st.title("🌿 Smart Travel Assistant for Karnataka")

st.write(
    "Discover Karnataka's beautiful nature spots, historic places, "
    "beaches, wildlife destinations, and more."
)


# --------------------------------------------------
# 7. SIDEBAR CATEGORY FILTER
# --------------------------------------------------

st.sidebar.header("Explore Karnataka")

categories = sorted(
    {
        destination["category"]
        for destination in DESTINATIONS
        if destination.get("category")
    }
)

category_options = ["All"] + categories

selected_category = st.sidebar.selectbox(
    "Choose a category",
    category_options,
)

search_text = st.sidebar.text_input(
    "Search destinations",
    placeholder="For example, Mysuru",
)


# --------------------------------------------------
# 8. FILTER DESTINATIONS
# --------------------------------------------------

filtered_destinations = DESTINATIONS

if selected_category != "All":
    filtered_destinations = [
        destination
        for destination in filtered_destinations
        if destination.get("category") == selected_category
    ]

if search_text.strip():
    query = search_text.strip().casefold()

    filtered_destinations = [
        destination
        for destination in filtered_destinations
        if query in destination.get("name", "").casefold()
        or query in destination.get("description", "").casefold()
        or query in destination.get("interests", "").casefold()
    ]


# --------------------------------------------------
# 9. DISPLAY DESTINATIONS AND IMAGES
# --------------------------------------------------

st.subheader(f"{selected_category} Destinations")

if not filtered_destinations:
    st.info(
        "No destinations found. Try another category or search term."
    )

else:
    columns_per_row = 3

    for start in range(0, len(filtered_destinations), columns_per_row):
        row_destinations = filtered_destinations[
            start:start + columns_per_row
        ]

        columns = st.columns(columns_per_row)

        for column, destination in zip(columns, row_destinations):
            with column:
                st.markdown(f"### {destination.get('name', 'Destination')}")

                image_name = destination.get("image_file", "")
                image_path = (BASE_DIR / image_name).resolve()

                # Prevent paths from pointing outside the project folder.
                try:
                    image_path.relative_to(BASE_DIR.resolve())
                    safe_path = True
                except ValueError:
                    safe_path = False

                if (
                    safe_path
                    and image_name
                    and image_path.is_file()
                ):
                    st.image(
                        str(image_path),
                        use_container_width=True,
                    )
                else:
                    st.caption("📷 Image not available for this destination.")

                st.write(
                    destination.get(
                        "description",
                        "Explore this destination in Karnataka.",
                    )
                )

                if destination.get("interests"):
                    st.caption(
                        f"Interests: {destination['interests']}"
                    )

                source_url = destination.get("source_url", "")

                if source_url.startswith(("https://", "http://")):
                    st.markdown(f"[Learn more]({source_url})")


# --------------------------------------------------
# 10. TRAVEL CHATBOT
# --------------------------------------------------

st.divider()
st.header("💬 Ask the Karnataka Travel Assistant")

st.write(
    "Ask questions about destinations, travel interests, or places "
    "to explore in Karnataka."
)

if "travel_messages" not in st.session_state:
    st.session_state.travel_messages = []

for message in st.session_state.travel_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Where would you like to explore in Karnataka?")

if prompt:
    st.session_state.travel_messages.append(
        {"role": "user", "content": prompt}
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    if client is None:
        answer = (
            "The travel chatbot needs an OpenAI API key. "
            "Configure OPENAI_API_KEY in your local .env file or "
            "in Streamlit Community Cloud Secrets. "
            "You can still browse the destination cards above."
        )

    else:
        destination_context = "\n".join(
            f"- {item.get('name', '')} "
            f"({item.get('category', '')}): "
            f"{item.get('description', '')}"
            for item in DESTINATIONS
        )

        system_prompt = f"""
You are a helpful travel assistant focused on Karnataka, India.

Answer clearly and politely. Recommend destinations based on the
traveller's interests. Do not invent opening hours, ticket prices,
transport schedules, or current conditions. Explain when information
needs to be verified.

Destination information:
{destination_context}

Additional knowledge:
{KNOWLEDGE}
"""

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *st.session_state.travel_messages[-10:],
                ],
            )

            answer = response.choices[0].message.content or (
                "Sorry, I couldn't generate an answer. Please try again."
            )

        except Exception as error:
            # Show a simple message to the user and log details in the terminal.
            print(f"OpenAI request failed: {error}")
            answer = (
                "Sorry, I couldn't connect to the travel chatbot. "
                "Please check your API key, internet connection, "
                "and OpenAI account settings."
            )

    st.session_state.travel_messages.append(
        {"role": "assistant", "content": answer}
    )

    with st.chat_message("assistant"):
        st.markdown(answer)
```
