
import os
from dotenv import load_dotenv
from core.rag_engine import WajhniRAGEngine
from core.ticket_generator import TicketGenerator



# تحميل الإعدادات

load_dotenv("config.env")

GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
LLAMA_MODEL    = os.getenv("LLAMA_MODEL",    "llama-3.3-70b-versatile")
SERVICES_FILE  = os.getenv("SERVICES_FILE",  "data/services.json")
OUTPUT_FOLDER  = "output"



# التحقق من وجود مفتاح API

def validate_config():
    if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
        print(" خطأ: مفتاح Groq API غير موجود!")
        print("   افتح ملف config.env وضع مفتاحك في GROQ_API_KEY")
        print("   احصل على مفتاح مجاني من: https://console.groq.com")
        return False

    if not os.path.exists(SERVICES_FILE):
        print(f" خطأ: ملف الخدمات غير موجود في المسار: {SERVICES_FILE}")
        return False

    return True



# الحلقة الرئيسية للتفاعل مع المستفيد

def run_kiosk(engine: WajhniRAGEngine, ticket_gen: TicketGenerator):
    """
    الحلقة الرئيسية — تستقبل طلبات المستفيدين حتى يطلبوا الخروج.
    """
    print("\n" + "="*52)
    print("   مرحباً بك في المركز الخدمي الشامل")
    print("   إمارة منطقة المدينة المنورة")
    print("="*52)
    print("   اكتب طلبك بالعربية وسنوجهك فوراً")
    print("   اكتب 'خروج' للإنهاء")
    print("="*52 + "\n")

     while True:
        gender = input(" هل أنت (ذكر / أنثى)؟: ").strip()
        if gender in ["ذكر", "أنثى", "انثى"]:
            if gender == "انثى":
                gender = "أنثى"
            break
        print(" الرجاء اكتب ذكر أو أنثى.")
 
    # ── التحقق من إدخال الحالة 
    while True:
        status = input(" هل أنت (مواطن / مقيم)؟: ").strip()
        if status in ["مواطن", "مقيم"]:
            break
        print(" الرجاء اكتب مواطن أو مقيم.")
 
    print(f"\n أهلاً بك.. تم تسجيل البيانات كـ ({gender} - {status}) وجاري خدمتك.\n")
          
    while True:
        # ── استقبال طلب المستفيد 
        print("─" * 52)
        user_input = input(" اكتب طلبك هنا: ").strip()

        if not user_input:
            print("  الرجاء كتابة طلبك.")
            continue

        if user_input in ["خروج", "exit", "quit", "q"]:
            print("\nشكراً لزيارتك. إلى اللقاء! \n")
            break

        # ── معالجة الطلب عبر RAG
        result = engine.process_request(user_input)

        # ── التعامل مع حالة الالتباس 
        if result.get("clarification_needed") and result.get("clarification_question"):
            print(f"\n {result['clarification_question']}")
            clarification = input(" إجابتك: ").strip()

            # إعادة المعالجة مع التوضيح
            combined_input = f"{user_input} - {clarification}"
            result = engine.process_request(combined_input)

        # ── توليد وطباعة التذكرة 
        if not result.get("error"):
            # حفظ بيانات المستفيد (الجنس والحالة) لتُطبع لاحقاً في التذكرة
            result["gender"] = gender
            result["status"] = status
            
            confidence = result.get("confidence", "")
            if confidence == "منخفضة":
                print("\n  النظام غير متأكد تماماً من طلبك.")
                print(f"   الخدمة المقترحة: {result.get('service_name')}")
                confirm = input("   هل هذا ما تحتاجه؟ (نعم/لا): ").strip()
                if confirm != "نعم":
                    print("   يرجى توضيح طلبك بشكل أكثر تفصيلاً.")
                    continue

            ticket_gen.generate(result)
        else:
            print(f"\n {result.get('message', 'حدث خطأ غير متوقع.')}\n")





def main():
    if not validate_config():
        return

    # تهيئة محرك RAG
    engine = WajhniRAGEngine(
        services_file=SERVICES_FILE,
        api_key=GROQ_API_KEY,
        model_name=LLAMA_MODEL,
    )
    engine.initialize()

    # تهيئة مولّد التذاكر
    ticket_gen = TicketGenerator(output_folder=OUTPUT_FOLDER)

    # تشغيل الكيوسك
    run_kiosk(engine, ticket_gen)


if __name__ == "__main__":
    main()
