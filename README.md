# LangChain + Gemini Assistant (Streamlit)

A single-file Streamlit app: register/login, then type any prompt and get a
dynamically generated answer from **Gemini**, invoked through a **LangChain**
chain (`prompt | llm | output_parser`, called via `.invoke()`).

## How the LangChain part works
```python
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=...)
prompt_template = ChatPromptTemplate.from_messages([...])
chain = prompt_template | llm | StrOutputParser()

answer = chain.invoke({"question": user_prompt})
```
Every prompt from `st.chat_input` is passed to `chain.invoke(...)`, and the
returned answer is shown live and saved to that user's history.

## Login
- Simple username/password auth stored in a local SQLite file (`users.db`)
- Passwords are hashed (SHA-256) before storage
- Session state (`st.session_state`) tracks who's logged in
- Each user's chat history is saved and reloaded on their next visit

## Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Get a free Gemini API key**
   - https://aistudio.google.com/app/apikey

3. **Configure your key**
   - Copy `.env.example` to `.env`
   - Paste your key into `GOOGLE_API_KEY`

4. **Run the app**
   ```bash
   streamlit run app.py
   ```
   It opens automatically at http://localhost:8501

5. **Register a user in the Register tab, then log in and start chatting.**

## Project structure
```
streamlit-gemini-chat/
├── app.py            # everything: auth, DB, LangChain chain, UI
├── requirements.txt
└── .env.example
```

## Ideas to extend
- Add conversation memory (`ConversationBufferMemory`) so the model
  remembers earlier turns, not just answers each prompt in isolation
- Swap SHA-256 for `bcrypt`/`werkzeug.security` if you want stronger hashing
- Add a model/temperature picker in the sidebar
- Deploy free on Streamlit Community Cloud (just point it at this repo)
