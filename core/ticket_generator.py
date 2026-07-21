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
import json
from datetime import datetime
import collections


class TicketGenerator:
    """
    مولّد تذاكر الانتظار بالعربية الكاملة مع تتبع حقيقي لصفوف الانتظار لكل قسم.
    """

    def __init__(self, output_folder: str = "output"):
        self.output_folder = output_folder
        os.makedirs(output_folder, exist_ok=True)
        self.counter_path = os.path.join(output_folder, "counter.json")
        self.ledger_path = os.path.join(output_folder, "tickets_log.json")
        self._ticket_counter = self._load_counter()

        # 🟢 تخزين عدد المنتظرين في الذاكرة RAM لكل قسم (يعود للصفر تلقائياً عند إعادة تشغيل السيرفر)
        self.department_queues = collections.defaultdict(int)

    # تحميل آخر رقم عداد محفوظ (يبقى مستمراً بعد إعادة تشغيل الجهاز)
    def _load_counter(self) -> int:
        if os.path.exists(self.counter_path):
            try:
                with open(self.counter_path, "r", encoding="utf-8") as f:
                    return json.load(f).get("last_counter", random.randint(10, 40))
            except (json.JSONDecodeError, OSError):
                pass
        return random.randint(10, 40)

    def _save_counter(self):
        with open(self.counter_path, "w", encoding="utf-8") as f:
            json.dump({"last_counter": self._ticket_counter}, f, ensure_ascii=False)

    # إضافة سجل التذكرة إلى الملف الخارجي المستمر (لا يُستبدل، فقط يُضاف إليه)
    def _append_ledger(self, record: dict):
        ledger = []
        if os.path.exists(self.ledger_path):
            try:
                with open(self.ledger_path, "r", encoding="utf-8") as f:
                    ledger = json.load(f)
            except (json.JSONDecodeError, OSError):
                ledger = []
        ledger.append(record)
        with open(self.ledger_path, "w", encoding="utf-8") as f:
            json.dump(ledger, f, ensure_ascii=False, indent=2)


    # توليد رقم الانتظار

    def _generate_waiting_number(self, window_number: int) -> str:
        self._ticket_counter += 1
        prefix_map = {1: "أ", 2: "ب", 3: "ج", 4: "د", 5: "هـ", 6: "و"}
        prefix = prefix_map.get(window_number, "م")
        return f"{prefix}-{self._ticket_counter:03d}"

    # حساب وقت الانتظار التقديري بناءً على العدد الفعلي المنتظر في القسم

    def _calculate_wait_time(self, department: str, estimated_time: int) -> dict:
        # زيادة عدد المنتظرين في صف هذا القسم بواقع شخص جديد أخذ تذكرة
        self.department_queues[department] += 1
        people_waiting = self.department_queues[department]

        total_minutes = people_waiting * estimated_time

        hours   = total_minutes // 60
        minutes = total_minutes % 60

        if hours > 0 and minutes > 0:
            wait_str = f"{hours} ساعة و{minutes} دقيقة"
        elif hours > 0:
            wait_str = f"{hours} ساعة"
        elif minutes > 0:
            wait_str = f"{minutes} دقيقة تقريباً"
        else:
            wait_str = "دورك الان"

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

        ticket = f"""
╔══════════════════════════════════════════════════╗
║         مركز الخدمة الشامل                       ║
║      إمارة منطقة المدينة المنورة                 ║
╠══════════════════════════════════════════════════╣
║                                                  ║
║   رقم التذكرة:  {ticket_data['waiting_number']:<33}║
║   التاريخ:      {date_str:<33}║
║   الوقت:        {time_str:<33}║
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
            doc_text = doc[:40] if len(doc) > 40 else doc
            lines += f"║   {i}. {doc_text:<43}║\n"
        return lines

    # حفظ التذكرة في ملف

    def _save_ticket(self, ticket_text: str, waiting_number: str) -> str:
        filename = f"ticket_{waiting_number.replace('-', '_')}_{datetime.now().strftime('%H%M%S')}.txt"
        filepath = os.path.join(self.output_folder, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(ticket_text)

        return filepath


    # الدالة الرئيسية — توليد وطباعة التذكرة

    def generate(self, service_result: dict) -> dict:
        if service_result.get("error"):
            return {"error": True, "message": service_result.get("message")}

        window_number  = service_result.get("window_number", 1)
        department     = service_result.get("department", "عام")
        waiting_number = self._generate_waiting_number(window_number)

        # حساب وقت الانتظار بناءً على القسم الفعلي
        wait_info      = self._calculate_wait_time(
            department,
            service_result.get("estimated_time_minutes", 15)
        )

        ticket_data = {
            "waiting_number": waiting_number,
            "wait_info":      wait_info,
        }

        ticket_text = self._format_ticket(service_result, ticket_data)
        saved_path  = self._save_ticket(ticket_text, waiting_number)

        self._save_counter()
        self._append_ledger({
            "waiting_number":  waiting_number,
            "timestamp":       datetime.now().isoformat(),
            "service_id":      service_result.get("service_id"),
            "service_name":    service_result.get("service_name"),
            "department":      department,
            "window_number":   window_number,
            "estimated_time_minutes": service_result.get("estimated_time_minutes"),
            "people_waiting":  wait_info["people_waiting"],
        })

        print("\n" + ticket_text + "\n")
        print(f"💾 تم حفظ التذكرة في: {saved_path}")
        print(f"📒 تم تسجيلها في السجل المستمر: {self.ledger_path}")

        return {
            "waiting_number": waiting_number,
            "wait_info":      wait_info,
            "ticket_text":    ticket_text,
            "saved_path":     saved_path,
            "ledger_path":    self.ledger_path,
            "service_name":   service_result.get("service_name"),
            "department":     department,
            "window_number":  window_number,
        }
