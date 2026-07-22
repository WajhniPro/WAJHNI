"""
وجّهني — طبقة API
=====================================================================
هذا الملف يفتح main.py (الذي كان مبنياً على واجهة سطر الأوامر فقط)
كخادم HTTP حتى تقدر واجهة المتصفح (wajhni-kiosk-ui.html) تتواصل مع
نفس محرك RAG (core/rag_engine.py) ونفس مولّد التذاكر
(core/ticket_generator.py) بدون أي تغيير في منطقهما الأساسي.

التشغيل محلياً:
    pip install -r requirements.txt
    uvicorn server:app --host 0.0.0.0 --port 8000 --reload

ثم افتح wajhni-kiosk-ui.html وغيّر API_BASE فيه إلى عنوان هذا الخادم.
=====================================================================
"""

import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.rag_engine import WajhniRAGEngine
from core.ticket_generator import TicketGenerator

load_dotenv("config.env")

GROQ_API_KEY  = os.getenv("GROQ_API_KEY")
LLAMA_MODEL   = os.getenv("LLAMA_MODEL", "llama-3.3-70b-versatile")
SERVICES_FILE = os.getenv("SERVICES_FILE", "data/services.json")
OUTPUT_FOLDER = "output"

app = FastAPI(title="Wajhni API — وجّهني")

# يسمح لملف HTML بالاتصال بالخادم من أي أصل أثناء التطوير.
# عند النشر الفعلي، يفضّل تحديد allow_origins بعنوان موقعك بدل "*"
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

engine: Optional[WajhniRAGEngine] = None
ticket_gen: Optional[TicketGenerator] = None


@app.on_event("startup")
def startup():
    global engine, ticket_gen

    if not GROQ_API_KEY or GROQ_API_KEY == "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":
        raise RuntimeError(
            "مفتاح Groq API غير موجود. ضعه في متغير البيئة GROQ_API_KEY "
            "أو في ملف config.env قبل التشغيل."
        )

    engine = WajhniRAGEngine(
        services_file=SERVICES_FILE,
        api_key=GROQ_API_KEY,
        model_name=LLAMA_MODEL,
    )
    engine.initialize()

    ticket_gen = TicketGenerator(output_folder=OUTPUT_FOLDER)


class RequestIn(BaseModel):
    text: str
    gender: Optional[str] = None
    status: Optional[str] = None


class TicketIn(BaseModel):
    result: dict


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/services")
def list_services():
    """يعيد قائمة الخدمات كما هي في data/services.json — تُستخدم لعرض
    أمثلة/شرائح الاقتراح في الواجهة، وليس للمطابقة (المطابقة تتم عبر
    محرك RAG نفسه)."""
    if engine is None:
        raise HTTPException(503, "المحرك لم يُهيَّأ بعد")
    return engine.services_data


@app.post("/api/request")
def process_request(payload: RequestIn):
    if engine is None:
        raise HTTPException(503, "المحرك لم يُهيَّأ بعد")
    if not payload.text.strip():
        raise HTTPException(400, "النص فارغ")

    result = engine.process_request(payload.text)
    # نحتفظ بالجنس/الحالة مع النتيجة لأغراض التذكرة فقط (لا تؤثر على المطابقة،
    # تماماً كما في main.py الأصلي)
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
