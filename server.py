import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq

app = FastAPI()

# تفعيل CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    query: str = ""
    text: str = ""
    gender: str = None
    status: str = None

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Wajhni API is running online!"}

@app.post("/chat")
def process_chat(req: ChatRequest):
    # جلب المفتاح داخل الطلب لمنع انهيار السيرفر عند الإقلاع
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured in Vercel Environment Variables.")
    
    try:
        client = Groq(api_key=api_key)
        user_text = req.query or req.text
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "أنت مساعد ذكي لنظام وجّهني لإمارة منطقة المدينة المنورة. قم بتحليل طلب المستخدم وإرجاع JSON يحتوي على: service_name, department, window_number, required_documents, estimated_time_minutes, confidence"},
                {"role": "user", "content": user_text}
            ],
            response_format={"type": "json_object"}
        )
        return completion.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
