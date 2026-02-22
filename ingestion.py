import os
import shutil
import tempfile
from pypdf import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.schema import Document

# Raw string for Windows path validity
PDF_PATH = r"C:\Users\LENOVO\qa-support-chatbot\tmp_copy.pdf\AI_Chatbot_Support_Knowledge_Base.pdf"

def load_content_safe(file_path: str) -> str:
    """
    Safely load content from a file, handling:
    1. File locks (by copying to temp)
    2. Format mismatch (trying PDF first, falling back to Text)
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # 1. Handle File Locks: Copy to a temporary location
    tmpdir = tempfile.mkdtemp()
    temp_path = os.path.join(tmpdir, "safe_copy.file")
    
    try:
        shutil.copy2(file_path, temp_path)
    except OSError as e:
        # If even copy fails, we can't proceed
        raise PermissionError(f"Critical: Could not copy file. Ensure it is not exclusively locked. Details: {e}")

    # 2. Try Reading as PDF
    try:
        reader = PdfReader(temp_path)
        # Check if it actually has pages and content
        text_content = []
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text_content.append(extracted)
        
        if text_content:
            print("✅ Successfully read as PDF.")
            return "\n".join(text_content)
            
    except Exception as e:
        print(f"⚠️ PDF reading failed ({e}). Attempting fallback to text...")

    # 3. Fallback: Read as Plain Text (UTF-8)
    try:
        with open(temp_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            if content.strip():
                print("✅ Successfully read as Plain Text.")
                return content
    except Exception as e:
        raise ValueError(f"Failed to read file as both PDF and Text. Last error: {e}")
    
    return ""

# ---- Main Execution ----

print(f"DTO: {PDF_PATH}")

# 1. Load Content
full_text = load_content_safe(PDF_PATH)

if not full_text:
    raise ValueError("No text could be extracted from the file.")

# 2. Create Document
docs = [Document(page_content=full_text, metadata={"source": PDF_PATH})]

# 3. Split Text
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_documents(docs)

# 4. Generate Embeddings & Vector Store
print("Generating embeddings...")
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectorstore = FAISS.from_documents(chunks, embeddings)
vectorstore.save_local("vectorstore")

print("✅ Ingestion Process Complete!")
