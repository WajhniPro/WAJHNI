"""
وجّهني — طبقة API المتوافقة مع Vercel و index.html
"""

import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.rag_engine import WajhniRAGEngine
from core.ticket_generator import TicketGenerator

# تحميل المتغيرات
if os.path.exists("config.env"):
    load_dotenv("config.env")
else:
    load_dotenv()

LLAMA_MODEL   = os.getenv("LLAMA_MODEL", "llama-3.3-70b-versatile")
SERVICES_FILE = os.getenv("SERVICES_FILE", "data/services.json")
OUTPUT_FOLDER = "output"

app = FastAPI(title="Wajhni API — وجّهني")

# السماح للواجهة بالاتصال بالخادم بدون قيود CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine: Optional[WajhniRAGEngine] = None
ticket_gen: Optional[TicketGenerator] = None


@app.on_event("startup")
def startup():
    global engine, ticket_gen

    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key:
        groq_api_key = groq_api_key.strip().strip('"').strip("'")

    if not groq_api_key:
        raise RuntimeError("مفتاح GROQ_API_KEY غير موجود في متغيرات البيئة.")

    engine = WajhniRAGEngine(
        services_file=SERVICES_FILE,
        api_key=groq_api_key,
        model_name=LLAMA_MODEL,
    )
    engine.initialize()
    ticket_gen = TicketGenerator(output_folder=OUTPUT_FOLDER)


class RequestIn(BaseModel):
    query: Optional[str] = None
    text: Optional[str] = None
    gender: Optional[str] = None
    status: Optional[str] = None


class TicketIn(BaseModel):
    result: dict


# 1. مسار الفحص الرئيسي الجذر (Root) لرفع العلم الأخضر في الواجهة
@app.get("/")
@app.get("/api/health")
def health():
    return {"status": "ok", "message": "Wajhni API is running online!"}


@app.get("/api/services")
def list_services():
    if engine is None:
        raise HTTPException(503, "المحرك لم يُهيَّأ بعد")
    return engine.services_data


# 2. دعم كلا المسارين /chat و /api/request لضمان التوافق التام
@app.post("/chat")
@app.post("/api/request")
def process_request(payload: RequestIn):
    if engine is None:
        raise HTTPException(503, "المحرك لم يُهيَّأ بعد")
    
    # قبول النص سواء جاء في حقل query أو text
    user_text = payload.query or payload.text
    if not user_text or not user_text.strip():
        raise HTTPException(400, "النص فارغ")

    result = engine.process_request(user_text)
    result["gender"] = payload.gender
    result["status"] = payload.status
    return result


@app.post("/api/ticket")
def make_ticket(payload: TicketIn):
    if ticket_gen is None:
        raise HTTPException(503, "مولّد التذاكر لم يُهيَّأ بعد")
    ticket = ticket_gen.generate(payload.result)
    if ticket.get("error"):
        raise HTTPException(400, ticket.get("message", "تعذر توليد التذكرة"))
    return ticket
