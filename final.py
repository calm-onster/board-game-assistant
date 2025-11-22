import os
import streamlit as st

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None


# Session keys
GEMINI_KEY = "messages_history_gemini"
PDF_KEY = "messages_history_pdf"


def setup_page():
    st.set_page_config(page_title="⚡ Board Game Assistant", layout="centered")
    st.sidebar.header("Options")
    st.markdown("""
        <style>
        #MainMenu {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)


def get_choice():
    return st.sidebar.radio("Choose:", ["Chat with Gemini 2.0", "Chat with a PDF"])


def get_response_text(response):
    return getattr(response, "content", None) or getattr(response, "text", "") or str(response)


def display_history(key: str):
    for m in st.session_state.get(key, []):
        if isinstance(m, SystemMessage):
            continue
        role = "user" if isinstance(m, HumanMessage) else "assistant"
        with st.chat_message(role):
            st.markdown(m.content)


def send_and_append(key: str, prompt: str):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.setdefault(key, []).append(HumanMessage(prompt))
    try:
        response = llm.invoke(st.session_state[key])
        content = get_response_text(response)
        st.session_state[key].append(SystemMessage(content))
        with st.chat_message("assistant"):
            st.markdown(content)
    except Exception as e:
        st.error(f"LLM error: {e}")


def ensure_pdf_ready() -> bool:
    # Return True if text already stored or successfully uploaded now.
    if st.session_state.get("boardgame_rules"):
        return True

    uploaded_pdf = st.file_uploader("Upload PDF (rules)", type=["pdf"])
    if not uploaded_pdf:
        return False

    if fitz is None:
        st.error("PyMuPDF (fitz) is required to read PDFs. Install with `pip install pymupdf`.")
        return False

    pdf_bytes = uploaded_pdf.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = "\n".join(page.get_text() for page in doc)
    st.session_state["boardgame_rules"] = text
    st.session_state.setdefault(PDF_KEY, []).append(
        SystemMessage(f"You are a board game rules reviewer. This is the rules to consider:\n\n{text}")
    )
    st.rerun()


def main():
    choice = get_choice()

    if choice == "Chat with Gemini 2.0":
        display_history(GEMINI_KEY)
        prompt = st.chat_input("Enter your question here")
        if prompt:
            send_and_append(GEMINI_KEY, prompt)

    else:  # Chat with a PDF
        st.subheader("Chat with your board game with PDF rules")
        if not ensure_pdf_ready():
            st.stop()

        # Ensure system message with rules is present when history is empty
        if not st.session_state.get(PDF_KEY):
            rules = st.session_state.get("boardgame_rules", "")
            st.session_state[PDF_KEY] = [
                SystemMessage(f"You are a board game rules reviewer. This is the rules to consider:\n\n{rules}")
            ]

        display_history(PDF_KEY)
        prompt = st.chat_input("Enter your question about the PDF")
        if prompt:
            send_and_append(PDF_KEY, prompt)


def get_clear():
    return st.sidebar.button("Start new session", key="clear")


setup_page()

st.title("Your Board Game Assistant")

# clear both histories and uploaded PDF when requested
if get_clear():
    for k in (GEMINI_KEY, PDF_KEY, "boardgame_rules"):
        if k in st.session_state:
            del st.session_state[k]
    st.rerun()

if "GOOGLE_API_KEY" not in os.environ:
    google_api_key = st.text_input("Google API Key", type="password")
    start_button = st.button("Start")
    if start_button:
        os.environ["GOOGLE_API_KEY"] = google_api_key
        st.rerun()
    st.stop()

llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")

# Initialize default histories
st.session_state.setdefault(GEMINI_KEY, [
    SystemMessage(
        "You are a guide for a board game cafe."
        "Help the players understand the rules."
        "Help them know the winning conditions."
        "Always answer in english."
        "Be friendly."
    )
])

st.session_state.setdefault(PDF_KEY, [])

main()