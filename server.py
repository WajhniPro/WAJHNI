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

# ── تحديد المسار المطلق لملف الخدمات لمنع أخطاء المسارات على Vercel ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SERVICES_PATH = os.path.join(BASE_DIR, "data", "services.json")
# إذا لم يجد الملف في مجلد data يبحث عنه في الجذر تلقائياً
if not os.path.exists(DEFAULT_SERVICES_PATH):
    DEFAULT_SERVICES_PATH = os.path.join(BASE_DIR, "services.json")

SERVICES_FILE = os.getenv("SERVICES_FILE", DEFAULT_SERVICES_PATH)
FORMATTED_CONTEXT = ""

def load_services_context():
    global FORMATTED_CONTEXT
    if not os.path.exists(SERVICES_FILE):
        print(f"تحذير: لم يتم العثور على ملف الخدمات في المسار {SERVICES_FILE}")
        FORMATTED_CONTEXT = "لا توجد قائمة خدمات محددة حالياً."
        return

    try:
        with open(SERVICES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # يدعم الكود سواء كانت البيانات مصفوفة مباشرة [ ] أو داخل كائن {"services": [ ]}
        services = data.get("services", data) if isinstance(data, dict) else data
        
        parts = []
        for s in services:
            parts.append(
                f"- خدمة ({s.get('id', 'N/A')}): {s.get('service_name', '')}\n"
                f"  القسم: {s.get('department', '')} | شباك: {s.get('window_number', 1)}\n"
                f"  الوصف: {s.get('description', '')}\n"
                f"  الكلمات المفتاحية: {', '.join(s.get('keywords', []))}\n"
                f"  المستندات المطلوبة: {', '.join(s.get('required_documents', []))}\n"
                f"  الوقت التقديري: {s.get('estimated_time_minutes', 10)} دقيقة\n"
            )
        FORMATTED_CONTEXT = "\n".join(parts)
        print(f"تم تحميل {len(services)} خدمة بنجاح.")
    except Exception as e:
        print(f"خطأ أثناء قراءة ملف الخدمات: {str(e)}")
        FORMATTED_CONTEXT = ""

# تحميل الخدمات عند التشغيل
load_services_context()

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Wajhni API is running online!"}

@app.post("/chat")
def process_chat(req: ChatRequest):
    # استخدام متغير البيئة من Vercel أو المفتاح الاحتياطي المباشر
    api_key = os.getenv("GROQ_API_KEY") or "ضع_مفتاح_Groq_هنا_إن_أردت"
    
    if not api_key or "ضع_مفتاح" in api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY غير مضبوط بـ Vercel.")

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
                        "أنت نظام الذكاء الاصطناعي لمشروع 'وجّهني' في إمارة منطقة المدينة المنورة.\n"
                        "مهمتك تحديد الخدمة المناسبة من القائمة أدناه فقط — لا تخترع خدمات غير موجودة فيها.\n\n"
                        "الخدمات المتاحة في النظام:\n"
                        f"{FORMATTED_CONTEXT}\n\n"
                        "قواعد:\n"
                        "1. اختر خدمة واحدة فقط من القائمة أعلاه إن وُجدت مطابقة واضحة.\n"
                        "2. لا تطلب توضيحاً إلا إذا كان الطلب غامضاً فعلاً ولا يمكن مطابقته مع أي خدمة.\n"
                        "3. أرجع JSON فقط بدون أي نص إضافي أو تنسيق markdown بالصيغة التالية:\n"
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
        cleaned_content = re.sub(r"^```json\s*|\s*```$", "", raw_content.strip(), flags=re.MULTILINE)

        return json.loads(cleaned_content)
    except Exception as e:
        print("Groq Error:", str(e))
        raise HTTPException(status_code=500, detail=f"خطأ في الاتصال بالذكاء الاصطناعي: {str(e)}")
