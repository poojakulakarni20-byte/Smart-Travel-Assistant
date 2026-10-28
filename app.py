import os
import re
import csv
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

import database


# =========================================================
# 1. PROJECT SETTINGS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
DESTINATIONS_FILE = BASE_DIR / "destinations.csv"
KNOWLEDGE_FILE = BASE_DIR / "knowledge.txt"

st.set_page_config(
    page_title="Smart Travel Assistant Karnataka",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_dotenv(BASE_DIR / ".env")


# =========================================================
# 2. API CONFIGURATION
# =========================================================

def get_setting(name, default=""):
    value = os.getenv(name)

    if value:
        return value

    try:
        value = st.secrets.get(name, default)
        return str(value) if value else default
    except Exception:
        return default


API_KEY = get_setting("OPENAI_API_KEY")
MODEL = get_setting("OPENAI_MODEL", "gpt-4o-mini")

client = None

if API_KEY and OpenAI is not None:
    try:
        client = OpenAI(api_key=API_KEY, timeout=30.0)
    except Exception:
        client = None


# =========================================================
# 3. DATABASE INITIALIZATION
# =========================================================

try:
    database.initialize_database()
except Exception as exc:
    st.warning(f"Database initialization notice: {exc}")


# =========================================================
# 4. IMAGE PATH HANDLING
# =========================================================

def find_image(image_file):
    """
    Search for an image in the project root and images folder.

    Examples:
        agumbe.jpg
        images/agumbe.jpg
    """

    if not image_file:
        return None

    filename = str(image_file).strip().replace("\\", "/")

    if not filename:
        return None

    relative_path = Path(filename)

    # Only allow paths within the project directory.
    if relative_path.is_absolute() or ".." in relative_path.parts:
        return None

    candidates = [
        BASE_DIR / relative_path,
        BASE_DIR / "images" / relative_path.name,
    ]

    for path in candidates:
        try:
            if path.is_file():
                return str(path)
        except OSError:
            continue

    return None


# =========================================================
# 5. LOAD DESTINATIONS
# =========================================================

def normalize_category(value):
    value = re.sub(r"\s+", " ", str(value or "").strip()).casefold()

    categories = {
        "nature": "Nature",
        "natural": "Nature",
        "wildlife": "Nature",
        "heritage": "Heritage",
        "historical": "Heritage",
        "history": "Heritage",
        "beach": "Beach",
        "beaches": "Beach",
        "coastal": "Coastal",
        "coast": "Coastal",
        "city": "City",
        "cities": "City",
        "hill station": "Hill Station",
        "hill stations": "Hill Station",
        "hills": "Hill Station",
        "adventure": "Adventure",
        "religious": "Spiritual",
        "spiritual": "Spiritual",
        "temple": "Spiritual",
        "temples": "Spiritual",
    }

    return categories.get(value, value.title() if value else "Other")


def load_destinations():
    if not DESTINATIONS_FILE.is_file():
        st.error(
            "destinations.csv was not found. "
            "Place it in the same folder as app.py."
        )
        return []

    destinations = []

    try:
        with DESTINATIONS_FILE.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            if not reader.fieldnames:
                st.error("destinations.csv is empty or has no header.")
                return []

            for row in reader:
                if not row:
                    continue

                # Normalize column names.
                cleaned = {
                    str(key or "").strip().lower(): str(value or "").strip()
                    for key, value in row.items()
                }

                name = cleaned.get("name", "")

                if not name:
                    continue

                destinations.append({
                    "name": name,
                    "category": normalize_category(
                        cleaned.get("category", "Other")
                    ),
                    "interests": cleaned.get("interests", ""),
                    "description": cleaned.get("description", ""),
                    "image_file": cleaned.get("image_file", ""),
                    "source_url": cleaned.get("source_url", ""),
                })

    except Exception as exc:
        st.error(f"Could not read destinations.csv: {exc}")
        return []

    return destinations


@st.cache_data
def cached_destinations():
    return load_destinations()


destinations = cached_destinations()


# =========================================================
# 6. LOAD KNOWLEDGE FILE
# =========================================================

def load_knowledge():
    if not KNOWLEDGE_FILE.is_file():
        return ""

    try:
        return KNOWLEDGE_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


KNOWLEDGE = load_knowledge()


# =========================================================
# 7. PAGE HEADER
# =========================================================

st.title("🌿 Smart Travel Assistant – Karnataka")

st.write(
    "Discover Karnataka's beautiful destinations, "
    "historic places, beaches, wildlife, and hill stations."
)

st.divider()


# =========================================================
# 8. SIDEBAR FILTERS
# =========================================================

with st.sidebar:
    st.header("🧭 Explore Karnataka")

    st.write("Choose a category to discover destinations.")

    categories = sorted({
        destination["category"]
        for destination in destinations
    })

    selected_category = st.selectbox(
        "Destination category",
        ["All"] + categories,
    )

    search_query = st.text_input(
        "🔍 Search destinations",
        placeholder="e.g. Mysuru, waterfalls, temples",
    )

    st.divider()

    st.subheader("About this project")
    st.write(
        "This application helps travelers explore destinations "
        "across Karnataka."
    )


# =========================================================
# 9. FILTER DESTINATIONS
# =========================================================

filtered_destinations = destinations.copy()

if selected_category != "All":
    filtered_destinations = [
        destination
        for destination in filtered_destinations
        if destination["category"] == selected_category
    ]

if search_query.strip():
    query = search_query.casefold()

    filtered_destinations = [
        destination
        for destination in filtered_destinations
        if query in destination["name"].casefold()
        or query in destination["description"].casefold()
        or query in destination["category"].casefold()
        or query in destination["interests"].casefold()
    ]


# =========================================================
# 10. DISPLAY DESTINATION CARDS AND IMAGES
# =========================================================

st.subheader("📍 Explore Destinations")

if not filtered_destinations:
    st.info(
        "No destinations matched your search. "
        "Try another keyword or select All."
    )

else:
    st.write(f"Found {len(filtered_destinations)} destination(s).")

    number_of_columns = 3

    for start in range(0, len(filtered_destinations), number_of_columns):
        group = filtered_destinations[
            start:start + number_of_columns
        ]

        columns = st.columns(number_of_columns)

        for column, destination in zip(columns, group):
            with column:
                with st.container(border=True):
                    st.markdown(f"### {destination['name']}")

                    st.caption(destination["category"])

                    image_path = find_image(
                        destination["image_file"]
                    )

                    if image_path:
                        st.image(
                            image_path,
                            use_container_width=True,
                        )
                    else:
                        st.info(
                            "📷 Image not available yet."
                        )

                    description = destination["description"]

                    if description:
                        st.write(description)
                    else:
                        st.write(
                            "Discover this destination in Karnataka."
                        )

                    if destination["interests"]:
                        st.caption(
                            f"Interests: {destination['interests']}"
                        )

                    if destination["source_url"]:
                        st.link_button(
                            "Learn more",
                            destination["source_url"],
                            use_container_width=True,
                        )


# =========================================================
# 11. AI TRAVEL CHATBOT
# =========================================================

st.divider()
st.header("💬 Ask the Karnataka Travel Assistant")

st.write(
    "Ask about destinations, attractions, travel ideas, "
    "or places to visit in Karnataka."
)

if "travel_messages" not in st.session_state:
    st.session_state.travel_messages = [
        {
            "role": "assistant",
            "content": (
                "Hello! 🌿 I can help you explore Karnataka. "
                "Ask me about nature, heritage, beaches, "
                "hill stations, or travel planning."
            ),
        }
    ]


for message in st.session_state.travel_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


user_question = st.chat_input(
    "Ask me about traveling in Karnataka..."
)

if user_question:
    st.session_state.travel_messages.append({
        "role": "user",
        "content": user_question,
    })

    with st.chat_message("user"):
        st.markdown(user_question)

    with st.chat_message("assistant"):
        if client is None:
            answer = (
                "The AI assistant needs an OpenAI API key to answer "
                "questions. You can still browse and search the "
                "destinations above. Configure OPENAI_API_KEY in "
                "Streamlit Secrets to enable the chatbot."
            )

            st.info(answer)

        else:
            try:
                destination_context = "\n".join(
                    f"- {item['name']} ({item['category']}): "
                    f"{item['description']}"
                    for item in destinations
                )

                system_prompt = f"""
You are a helpful travel assistant specializing in Karnataka, India.

Give friendly, clear, practical travel suggestions.
Use the destination information below when relevant.
Do not invent exact prices, opening hours, or transport schedules.
If you are unsure about current information, say that it should
be checked before traveling.

Available destinations:
{destination_context}

Additional project knowledge:
{KNOWLEDGE[:12000]}
"""

                recent_messages = [
                    {
                        "role": message["role"],
                        "content": message["content"],
                    }
                    for message in st.session_state.travel_messages[-10:]
                ]

                response = client.chat.completions.create(
                    model=MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt,
                        },
                        *recent_messages,
                    ],
                    max_tokens=700,
                )

                answer = response.choices[0].message.content

                if not answer:
                    answer = (
                        "I couldn't generate an answer. "
                        "Please try asking another question."
                    )

                st.markdown(answer)

            except Exception as exc:
                answer = (
                    "Sorry, the AI assistant could not answer right now. "
                    "Please check your API key and internet connection, "
                    "then try again."
                )

                st.error(answer)

                # Show a simple diagnostic without exposing secrets.
                st.caption(f"Technical detail: {type(exc).__name__}")

    st.session_state.travel_messages.append({
        "role": "assistant",
        "content": answer,
    })


# =========================================================
# 12. FOOTER
# =========================================================

st.divider()

st.caption(
    "🌿 Smart Travel Assistant for Exploring Karnataka | "
    "Built with Python and Streamlit"
)
