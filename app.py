import os
import sqlite3
import hashlib

import streamlit as st
from dotenv import load_dotenv

# LangChain + Gemini
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

DB_PATH = "users.db"

# ---------------------------------------------------------------------------
# Tiny DB helpers (SQLite) — users + per-user chat history
# ---------------------------------------------------------------------------
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            prompt TEXT NOT NULL,
            answer TEXT NOT NULL
        )
    """)
    return conn


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def create_user(username: str, password: str) -> bool:
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, hash_password(password)),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # username already exists
    finally:
        conn.close()


def verify_user(username: str, password: str) -> bool:
    conn = get_conn()
    row = conn.execute(
        "SELECT password_hash FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    return bool(row) and row[0] == hash_password(password)


def save_message(username: str, prompt: str, answer: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO chat_history (username, prompt, answer) VALUES (?, ?, ?)",
        (username, prompt, answer),
    )
    conn.commit()
    conn.close()


def load_history(username: str):
    conn = get_conn()
    rows = conn.execute(
        "SELECT prompt, answer FROM chat_history WHERE username = ? ORDER BY id",
        (username,),
    ).fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# LangChain + Gemini — this is the "dynamic answer generation" part.
# Any prompt typed by the user is passed through this chain and invoked.
# ---------------------------------------------------------------------------
@st.cache_resource
def get_chain():
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.6-flash",
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=0.7,
    )
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful, concise assistant."),
        ("human", "{question}"),
    ])
    return prompt_template | llm | StrOutputParser()


def get_ai_answer(user_prompt: str) -> str:
    chain = get_chain()
    return chain.invoke({"question": user_prompt})


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------
st.set_page_config(page_title="LangChain + Gemini Assistant", page_icon="🤖")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None


def login_register_screen():
    st.title("🤖 LangChain + Gemini Assistant")
    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pass")
            submitted = st.form_submit_button("Log In")
            if submitted:
                if verify_user(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

    with tab_register:
        with st.form("register_form"):
            new_username = st.text_input("Choose a username", key="reg_user")
            new_password = st.text_input("Choose a password", type="password", key="reg_pass")
            submitted = st.form_submit_button("Register")
            if submitted:
                if not new_username or not new_password:
                    st.error("Username and password are required.")
                elif create_user(new_username, new_password):
                    st.success("Account created! Go to the Login tab.")
                else:
                    st.error("That username is already taken.")


def chat_screen():
    st.title("🤖 LangChain + Gemini Assistant")
    st.caption(f"Logged in as **{st.session_state.username}**")

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun()

    # Show past history for this user
    for prompt, answer in load_history(st.session_state.username):
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            st.markdown(answer)

    # New prompt input — dynamically generates an answer via LangChain + Gemini
    user_prompt = st.chat_input("Type any prompt...")
    if user_prompt:
        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    answer = get_ai_answer(user_prompt)
                except Exception as exc:
                    answer = f"⚠️ Gemini/LangChain error: {exc}"
            st.markdown(answer)

        save_message(st.session_state.username, user_prompt, answer)


if st.session_state.logged_in:
    chat_screen()
else:
    login_register_screen()
