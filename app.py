from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request, Form, Response
from pydantic import BaseModel
from twilio.twiml.voice_response import VoiceResponse
from langchain.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.llms import Ollama
from langchain.chains import RetrievalQA
import requests

app = FastAPI(title="Q&A Support Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
qa_chain = None

@app.get("/")
@app.post("/")
async def root():
    return {"message": "Q&A Support Chatbot is running! 🚀", "docs_url": "/docs", "voice_url": "/voice"}

# ---- Startup Check ----
def is_ollama_shutdown():
    try:
        response = requests.get("http://localhost:11434")
        return response.status_code != 200
    except requests.exceptions.ConnectionError:
        return True

print("Initializing Local Resources...")
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectorstore = FAISS.load_local(
    "vectorstore",
    embeddings,
    allow_dangerous_deserialization=True
)

if is_ollama_shutdown():
    print("⚠️ WARNING: Ollama is not running on port 11434!")
    print("   Please start Ollama and pull the mistral model: `ollama pull mistral`")
    llm = None
else:
    print("✅ Ollama is running. Initializing Model...")
    llm = Ollama(model="phi")
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
    )

class Question(BaseModel):
    query: str

def get_llm_response(query: str):
    global qa_chain, llm
    
    # Lazy Re-check if NULL
    if not qa_chain:
        if is_ollama_shutdown():
             raise Exception("Ollama service is not reachable at localhost:11434. Please ensure Ollama is installed and running.")
        
        # Try to initialize again just in case it started late
        try:
            llm = Ollama(model="phi")
            qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
            )
        except Exception as e:
             raise Exception(f"Failed to initialize Ollama: {e}")

    try:
        answer = qa_chain.invoke(query)
        # Handle dict or string return depending on chain version
        if isinstance(answer, dict) and "result" in answer:
             return answer["result"]
        return answer
    except Exception as e:
         raise Exception(f"Error generating answer: {e}")

@app.post("/chat")
def chat(question: Question):
    try:
        answer = get_llm_response(question.query)
        return {"answer": answer}
    except Exception as e:
        if "Ollama service is not reachable" in str(e):
             raise HTTPException(status_code=503, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/voice")
async def voice(request: Request):
    """
    Initial endpoint for incoming calls. 
    Responds with TwiML to gather speech input.
    """
    resp = VoiceResponse()
    gather = resp.gather(input="speech", action="/voice/process", method="POST")
    gather.say("Hello, I am your support assistant. Ask me anything.")
    resp.redirect("/voice") # Loop back if no input
    return Response(content=str(resp), media_type="application/xml")

from fastapi import BackgroundTasks

# In-memory storage for call states (CallSid -> State)
call_states = {}

def process_llm_background(call_sid: str, query: str):
    """Background task to query LLM and store result."""
    print(f"DEBUG: Starting background LLM processing for {call_sid}...")
    try:
        response = get_llm_response(query)
        call_states[call_sid] = {"status": "ready", "response": response}
        print(f"DEBUG: LLM processing complete for {call_sid}.")
    except Exception as e:
        print(f"ERROR: LLM processing failed: {e}")
        call_states[call_sid] = {"status": "error", "response": "I encountered an internal error."}

@app.post("/voice/process")
async def process_voice(background_tasks: BackgroundTasks, SpeechResult: str = Form(...), CallSid: str = Form(...)):
    """
    Receives speech, starts background processing, and puts caller on hold.
    """
    print(f"DEBUG: Received voice input: {SpeechResult}")
    
    # Initialize state
    call_states[CallSid] = {"status": "processing"}
    
    # Start background task
    background_tasks.add_task(process_llm_background, CallSid, SpeechResult)
    
    resp = VoiceResponse()
    resp.say("One moment, let me think about that.")
    resp.redirect("/voice/poll")
    return Response(content=str(resp), media_type="application/xml")

@app.post("/voice/poll")
async def poll_voice(CallSid: str = Form(...)):
    """
    Polls for the LLM result. If not ready, loops with a pause.
    """
    state = call_states.get(CallSid)
    resp = VoiceResponse()
    
    if not state or state["status"] == "processing":
        # Still processing, wait 2 seconds and check again
        # Use simple silence or "play" a music file if available. Pause is simplest.
        resp.pause(length=2)
        resp.redirect("/voice/poll")
        return Response(content=str(resp), media_type="application/xml")
        
    elif state["status"] == "ready":
        # Result is ready
        resp.say(state["response"])
        # Cleanup
        if CallSid in call_states:
            del call_states[CallSid]
            
        # Redirect back to main menu/listening
        resp.redirect("/voice")
        return Response(content=str(resp), media_type="application/xml")
        
    else:
        # Error state
        resp.say("I'm sorry, I couldn't generate a response.")
        if CallSid in call_states:
            del call_states[CallSid]
        resp.redirect("/voice")
        return Response(content=str(resp), media_type="application/xml")
