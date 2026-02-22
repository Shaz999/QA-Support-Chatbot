import streamlit as st
import requests

# Page Config
st.set_page_config(
    page_title="Q&A Support Chatbot",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 Q&A Support Chatbot")
st.caption("Ask me anything about your documents!")

# Backend URL
BACKEND_URL = "http://127.0.0.1:8000/chat"

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle User Input
if prompt := st.chat_input("How can I help you?"):
    # Display User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get Bot Response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            response = requests.post(BACKEND_URL, json={"query": prompt})
            if response.status_code == 200:
                data = response.json()
                full_response = data.get("answer", "No answer found.")
            else:
                full_response = f"⚠️ Error {response.status_code}: {response.text}"
        except requests.exceptions.ConnectionError:
            full_response = "⚠️ Connection Error: Is the backend running?"
        
        message_placeholder.markdown(full_response)
        
    st.session_state.messages.append({"role": "assistant", "content": full_response})
