from fastapi.testclient import TestClient
from app import app
from unittest.mock import patch, MagicMock

client = TestClient(app)

def test_voice_endpoint():
    response = client.post("/voice")
    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    assert "<Gather input=\"speech\" action=\"/voice/process\" method=\"POST\">" in response.text
    assert "<Say>Hello, I am your support assistant. Ask me anything.</Say>" in response.text
    print("✅ /voice endpoint passed")

@patch("app.get_llm_response")
def test_voice_process_endpoint(mock_get_llm):
    mock_get_llm.return_value = "This is a test response."
    
    # Simulate Form data sent by Twilio
    response = client.post("/voice/process", data={"SpeechResult": "Hello"})
    
    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    assert "<Say>This is a test response.</Say>" in response.text
    assert "<Redirect>/voice</Redirect>" in response.text
    print("✅ /voice/process endpoint passed")

if __name__ == "__main__":
    try:
        test_voice_endpoint()
        test_voice_process_endpoint()
        print("All tests passed!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
