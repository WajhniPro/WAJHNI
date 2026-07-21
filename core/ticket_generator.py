"""

 وجّهني — مولّد التذاكر
 ملف: core/ticket_generator.py

 المهمة:
   - توليد رقم انتظار فريد
   - تنسيق التذكرة بالعربية كاملاً
   - طباعة التذكرة في الطرفية
   - حفظ التذكرة في ملف نصي (بديل الطابعة)

"""

import random
import os
from datetime import datetime


class TicketGenerator:
    """
    مولّد تذاكر الانتظار بالعربية الكاملة.
    """

    def __init__(self, output_folder: str = "output"):
        self.output_folder = output_folder
        os.makedirs(output_folder, exist_ok=True)
        self._ticket_counter = random.randint(10, 40)

  
    # توليد رقم الانتظار
  
    def _generate_waiting_number(self, window_number: int) -> str:
        
        self._ticket_counter += 1
        prefix_map = {1: "أ", 2: "ب", 3: "ج", 4: "د", 5: "هـ", 6: "و"}
        prefix = prefix_map.get(window_number, "م")
        return f"{prefix}-{self._ticket_counter:03d}"

    # حساب وقت الانتظار التقديري
  
    def _calculate_wait_time(self, estimated_time: int) -> dict:
        people_waiting = random.randint(2, 8)
        total_minutes  = people_waiting * estimated_time

        hours   = total_minutes // 60
        minutes = total_minutes % 60

        if hours > 0:
            wait_str = f"{hours} ساعة و{minutes} دقيقة"
        else:
            wait_str = f"{minutes} دقيقة تقريباً"

        return {
            "people_waiting": people_waiting,
            "total_minutes":  total_minutes,
            "wait_string":    wait_str
        }

    # تنسيق التذكرة النصية بالعربية
    
    def _format_ticket(self, service_result: dict, ticket_data: dict) -> str:
        
        now      = datetime.now()
        date_str = now.strftime("%Y/%m/%d")
        time_str = now.strftime("%H:%M")
     
      # بيانات المستفيد 
        gender = service_result.get("gender", "") or "غير محدد"
        status = service_result.get("status", "") or "غير محدد"
        category_str = f"{status} - {gender}"

        docs_list = "\n".join([
            f"   {i+1}. {doc}"
            for i, doc in enumerate(service_result.get("required_documents", []))
        ])

        ticket = f"""
╔══════════════════════════════════════════════════╗
║         مركز الخدمة الشامل                       ║
║      إمارة منطقة المدينة المنورة                 ║
╠══════════════════════════════════════════════════╣
║                                                  ║
║   رقم التذكرة:  {ticket_data['waiting_number']:<33}║
║   التاريخ:      {date_str:<33}║
║   الوقت:        {time_str:<33}║
║   الفئة:        {category_str:<33}║
║                                                  ║
╠══════════════════════════════════════════════════╣
║   القسم المعني:                                  ║
║   {service_result.get('department', ''):<48}║
║                                                  ║
║   رقم الشباك:   {str(service_result.get('window_number', '')):<33}║
║   الخدمة:       {service_result.get('service_name', '')[:32]:<32} ║
║                                                  ║
╠══════════════════════════════════════════════════╣
║   وقت الانتظار التقديري:                         ║
║   {ticket_data['wait_info']['wait_string']:<48}║
║   (يوجد {ticket_data['wait_info']['people_waiting']} أشخاص قبلك)                          ║
║                                                  ║
╠══════════════════════════════════════════════════╣
║   المستندات المطلوبة:                            ║
{self._format_docs_for_ticket(service_result.get('required_documents', []))}║                                                  ║
╠══════════════════════════════════════════════════╣
║   يرجى الاحتفاظ بهذه التذكرة ومتابعة            ║
║   الشاشات الإلكترونية لمعرفة دورك               ║
╚══════════════════════════════════════════════════╝
        """.strip()

        return ticket

    def _format_docs_for_ticket(self, documents: list) -> str:
        
        lines = ""
        for i, doc in enumerate(documents, 1):
            # اقتصاص النص إذا كان طويلاً
            doc_text = doc[:40] if len(doc) > 40 else doc
            lines += f"║   {i}. {doc_text:<43}║\n"
        return lines

    # حفظ التذكرة في ملف
 
    def _save_ticket(self, ticket_text: str, waiting_number: str) -> str:
        """حفظ التذكرة في ملف نصي داخل مجلد output."""
        filename = f"ticket_{waiting_number.replace('-', '_')}_{datetime.now().strftime('%H%M%S')}.txt"
        filepath = os.path.join(self.output_folder, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(ticket_text)

        return filepath

  
    # الدالة الرئيسية — توليد وطباعة التذكرة

    def generate(self, service_result: dict) -> dict:
        """
        توليد وطباعة التذكرة.
        """
        if service_result.get("error"):
            return {"error": True, "message": service_result.get("message")}

        window_number  = service_result.get("window_number", 1)
        waiting_number = self._generate_waiting_number(window_number)
        wait_info      = self._calculate_wait_time(
            service_result.get("estimated_time_minutes", 15)
        )

        ticket_data = {
            "waiting_number": waiting_number,
            "wait_info":      wait_info,
        }

        ticket_text = self._format_ticket(service_result, ticket_data)
        saved_path  = self._save_ticket(ticket_text, waiting_number)

        # طباعة التذكرة في الطرفية
        print("\n" + ticket_text + "\n")
        print(f"💾 تم حفظ التذكرة في: {saved_path}")

        return {
            "waiting_number": waiting_number,
            "wait_info":      wait_info,
            "ticket_text":    ticket_text,
            "saved_path":     saved_path,
            "service_name":   service_result.get("service_name"),
            "department":     service_result.get("department"),
            "window_number":  window_number,
            "gender":         service_result.get("gender"),
            "status":         service_result.get("status")
        }
