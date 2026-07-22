import os
import json
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq

app = FastAPI(title="Wajhni API")

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
    gender: str | None = None
    status: str | None = None

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Wajhni API is running online!"}

@app.post("/chat")
def process_chat(req: ChatRequest):
    # محاولة قراءة المفتاح من Vercel، وفي حال عدم وجوده يتم استخدام المفتاح المباشر
    api_key = os.getenv("GROQ_API_KEY") or "gsk_ضع_مفتاحك_الحقيقي_هنا_مباشرة"
    
    if not api_key or api_key == "gsk_ضع_مفتاحك_الحقيقي_هنا_مباشرة":
        raise HTTPException(
            status_code=500, 
            detail="يرجى استبدال gsk_ضع_مفتاحك_الحقيقي_هنا_مباشرة بمفتاح Groq الخاص بك."
        )
    
    user_text = (req.query or req.text or "").strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="الطلب فارغ.")

    try:
        client = Groq(api_key=api_key)
        prompt = f"طلب المستخدم: {user_text}\nالجنس: {req.gender or 'غير محدد'}\nالحالة: {req.status or 'غير محدد'}"
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "أنت نظام الذكاء الاصطناعي لمشروع 'وجّهني' في إمارة منطقة المدينة المنورة. "
                        "حلل الطلب وأرجع JSON فقط بدون أي نص إضافي أو تنسيق markdown بالصيغة التالية:\n"
                        "{\n"
                        '  "service_id": "S001",\n'
                        '  "service_name": "اسم الخدمة",\n'
                        '  "department": "اسم القسم",\n'
                        '  "window_number": 1,\n'
                        '  "required_documents": ["مستند 1", "مستند 2"],\n'
                        '  "estimated_time_minutes": 15,\n'
                        '  "confidence": "عالية",\n'
                        '  "clarification_needed": false,\n'
                        '  "clarification_question": ""\n'
                        "}"
                    )
                },
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        raw_content = completion.choices[0].message.content
        
        # تنظيف النص من أي علامات markdown إذا وجدت
        cleaned_content = re.sub(r"^```json\s*|\s*```$", "", raw_content.strip(), flags=re.MULTILINE)
        
        return json.loads(cleaned_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
