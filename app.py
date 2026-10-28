import csv
import os
from pathlib import Path

import streamlit as st

# Optional OpenAI integration
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Smart Travel Assistant - Karnataka",
    page_icon="🧭",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
CSV_FILE = BASE_DIR / "destinations.csv"
IMAGES_DIR = BASE_DIR / "images"

st.title("🧭 Smart Travel Assistant")
st.subheader("Explore the beautiful destinations of Karnataka")

st.write(
    "Discover destinations, explore Karnataka's heritage, "
    "find scenic getaways, and plan your next trip."
)


# --------------------------------------------------
# LOAD DESTINATIONS
# --------------------------------------------------

@st.cache_data
def load_destinations():
    if not CSV_FILE.exists():
        return []

    with CSV_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)
        destinations = []

        for row in reader:
            destinations.append({
                key: (value or "").strip()
                for key, value in row.items()
                if key is not None
            })

        return destinations


destinations = load_destinations()

if not destinations:
    st.error(
        "Could not load destinations.csv. "
        "Make sure it is in the same folder as app.py."
    )
    st.stop()


# --------------------------------------------------
# FIND IMAGES
# --------------------------------------------------

def find_image(image_file):
    """
    Find an image using its CSV path or filename.

    Supports:
      images/agumbe.jpg
      agumbe.jpg

    Searches the app folder and its images subfolder.
    """

    if not image_file:
        return None

    image_file = image_file.strip().replace("\\", "/")
    relative_path = Path(image_file)

    candidates = [
        BASE_DIR / relative_path,
        IMAGES_DIR / relative_path.name,
    ]

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    # Case-insensitive fallback for filename differences
    if IMAGES_DIR.is_dir():
        wanted_name = relative_path.name.lower()

        for candidate in IMAGES_DIR.iterdir():
            if (
                candidate.is_file()
                and candidate.name.lower() == wanted_name
            ):
                return candidate

    return None


# --------------------------------------------------
# SIDEBAR FILTERS
# --------------------------------------------------

st.sidebar.title("🧭 Explore Karnataka")
st.sidebar.write("Choose a category or search for destinations.")

categories = sorted({
    destination.get("category", "Other")
    for destination in destinations
})

selected_category = st.sidebar.selectbox(
    "Destination category",
    ["All"] + categories,
)

search_text = st.sidebar.text_input(
    "🔎 Search destinations",
    placeholder="e.g. Mysuru, waterfalls, temples",
)

st.sidebar.divider()

st.sidebar.subheader("About this project")
st.sidebar.write(
    "This application helps travelers discover destinations "
    "across Karnataka."
)


# --------------------------------------------------
# FILTER DESTINATIONS
# --------------------------------------------------

filtered_destinations = []

for destination in destinations:
    category = destination.get("category", "Other")

    searchable_text = " ".join([
        destination.get("name", ""),
        destination.get("category", ""),
        destination.get("interests", ""),
        destination.get("description", ""),
    ]).lower()

    category_matches = (
        selected_category == "All"
        or category == selected_category
    )

    search_matches = (
        not search_text.strip()
        or search_text.strip().lower() in searchable_text
    )

    if category_matches and search_matches:
        filtered_destinations.append(destination)


st.write(f"### Explore {len(filtered_destinations)} destinations")


# --------------------------------------------------
# DESTINATION CARDS
# --------------------------------------------------

if not filtered_destinations:
    st.info(
        "No destinations matched your search. "
        "Try another name, interest, or category."
    )

else:
    cards_per_row = 3

    for start in range(0, len(filtered_destinations), cards_per_row):
        row_destinations = filtered_destinations[
            start:start + cards_per_row
        ]

        columns = st.columns(cards_per_row)

        for column, destination in zip(columns, row_destinations):
            with column:
                name = destination.get("name", "Unknown destination")
                category = destination.get("category", "Other")
                description = destination.get("description", "")
                interests = destination.get("interests", "")
                source_url = destination.get("source_url", "")
                image_file = destination.get("image_file", "")

                with st.container(border=True):
                    st.markdown(f"### {name}")
                    st.caption(category)

                    image_path = find_image(image_file)

                    if image_path is not None:
                        try:
                            st.image(
                                str(image_path),
                                use_container_width=True,
                                caption=name,
                            )
                        except Exception:
                            st.info("📷 Could not display this image.")
                    else:
                        st.info("📷 Image not found in the images folder.")

                    st.write(description)

                    if interests:
                        st.caption(f"Interests: {interests}")

                    if source_url.startswith(("https://", "http://")):
                        st.link_button(
                            "Learn more",
                            source_url,
                            use_container_width=True,
                        )


# --------------------------------------------------
# IMAGE DIAGNOSTICS
# --------------------------------------------------

with st.expander("Image troubleshooting"):
    st.write("App directory:", str(BASE_DIR))
    st.write("Images directory:", str(IMAGES_DIR))
    st.write("Images directory exists:", IMAGES_DIR.is_dir())

    if IMAGES_DIR.is_dir():
        image_files = [
            file.name
            for file in IMAGES_DIR.iterdir()
            if file.is_file()
        ]

        st.write(f"Files found in images/: {len(image_files)}")
        st.write(image_files[:100])
    else:
        st.warning(
            "The images folder is missing from the deployed application."
        )

    missing_images = []

    for destination in destinations:
        image_path = find_image(destination.get("image_file", ""))

        if image_path is None:
            missing_images.append({
                "destination": destination.get("name", ""),
                "expected_path": destination.get("image_file", ""),
            })

    if missing_images:
        st.warning("Some destination images could not be found.")
        st.dataframe(missing_images, use_container_width=True)
    else:
        st.success("All destination image paths were found!")


# --------------------------------------------------
# AI TRAVEL CHATBOT
# --------------------------------------------------

st.divider()
st.header("💬 Smart Travel Chatbot")
st.write("Ask questions about traveling around Karnataka.")

api_key = None

try:
    api_key = st.secrets.get("OPENAI_API_KEY")
except Exception:
    api_key = os.getenv("OPENAI_API_KEY")


if OpenAI is None:
    st.info(
        "The OpenAI package is not installed. "
        "Add openai to requirements.txt to enable the chatbot."
    )

elif not api_key:
    st.info(
        "The travel chatbot is not configured yet. "
        "Add OPENAI_API_KEY to Streamlit Cloud Secrets to enable it."
    )

else:
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_prompt = st.chat_input(
        "Ask me about traveling in Karnataka..."
    )

    if user_prompt:
        st.session_state.chat_messages.append({
            "role": "user",
            "content": user_prompt,
        })

        with st.chat_message("user"):
            st.markdown(user_prompt)

        try:
            client = OpenAI(api_key=api_key)

            context = "\n".join(
                f"- {item.get('name', '')}: "
                f"{item.get('description', '')} "
                f"Category: {item.get('category', '')}."
                for item in destinations
            )

            instructions = (
                "You are a helpful travel assistant specializing in "
                "Karnataka, India. Give friendly, clear, practical "
                "travel suggestions. Do not invent current opening "
                "hours, prices, or transport schedules. Tell users "
                "to verify time-sensitive details with official sources. "
                "Use this destination information when relevant:\n"
                + context
            )

            with st.chat_message("assistant"):
                with st.spinner("Planning your answer..."):
                    response = client.responses.create(
                        model="gpt-4.1-mini",
                        instructions=instructions,
                        input=user_prompt,
                    )

                    answer = response.output_text

                    st.markdown(answer)

            st.session_state.chat_messages.append({
                "role": "assistant",
                "content": answer,
            })

        except Exception as error:
            st.error(
                "The chatbot could not respond. "
                "Check your OpenAI API key and app configuration."
            )
