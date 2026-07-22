"""
وجّهني — طبقة API
=====================================================================
هذا الملف يفتح main.py كخادم HTTP حتى تقدر واجهة المتصفح (wajhni-kiosk-ui.html)
تتواصل مع نفس محرك RAG (core/rag_engine.py) ونفس مولّد التذاكر
(core/ticket_generator.py) بدون أي تغيير في منطقهما الأساسي.
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

# تحميل المتغيرات من config.env محلياً إن وجد، أو من النظام مباشرة على Render
if os.path.exists("config.env"):
    load_dotenv("config.env")
else:
    load_dotenv()

LLAMA_MODEL   = os.getenv("LLAMA_MODEL", "llama-3.3-70b-versatile")
SERVICES_FILE = os.getenv("SERVICES_FILE", "data/services.json")
OUTPUT_FOLDER = "output"

app = FastAPI(title="Wajhni API — وجّهني")

# السماح للواجهة بالاتصال بالخادم
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

    # قراءة مفتاح Groq وتنظيفه من أي مسافات أو علامات تنصيص زائدة
    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key:
        groq_api_key = groq_api_key.strip().strip('"').strip("'")

    # التحقق المرن من وجود المفتاح
    if not groq_api_key:
        raise RuntimeError(
            "مفتاح Groq API غير موجود. ضعه في متغير البيئة GROQ_API_KEY في Render."
        )

    engine = WajhniRAGEngine(
        services_file=SERVICES_FILE,
        api_key=groq_api_key,
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
    أمثلة/شرائح الاقتراح في الواجهة، وليس للمطابقة."""
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
