# QA Support Chatbot

This repository contains a small QA-support chatbot project that ingests PDF documents, builds a vector store, and runs a Streamlit UI for question answering.

Getting started
- Install dependencies:

```bash
pip install -r requirements.txt
```

- Ingest PDFs (if needed):

```bash
python ingestion.py
```

- Run the Streamlit app:

```bash
streamlit run streamlit_app.py
```

Notes
- The FAISS index and uploaded PDFs are excluded from the repo via `.gitignore`.
- Configure any API keys or credentials as environment variables before running.

Contact
- For repository issues or questions, open an issue on GitHub.
