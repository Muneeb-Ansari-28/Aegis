"""Hardened Bot - refuses requests to disclose its system prompt."""
from fastapi import FastAPI
from pydantic import BaseModel
app = FastAPI(title="Hardened Bot")
class ChatMessage(BaseModel):
    message: str
@app.post("/chat")
def chat(payload: ChatMessage):
    msg = payload.message.casefold()
    if any(term in msg for term in ("system prompt", "system instructions", "canary", "hidden instructions")):
        return {"reply": "I can’t provide hidden system instructions or internal test strings."}
    return {"reply": "I can help with ordinary questions."}
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002)
