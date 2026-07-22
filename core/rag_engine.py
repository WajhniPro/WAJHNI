import json
import os
import re
from typing import Optional
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

class WajhniRAGEngine:

    def __init__(self, services_file: str, api_key: str, model_name: str):
        self.services_file = services_file
        self.api_key = api_key
        self.model_name = model_name
        self.services_data = []
        self.formatted_context = ""
        self.llm = None
        self.rag_chain = None

    def load_services(self):
        """تحميل الخدمات وقراءتها مباشرة بدون الحاجة لـ Pandas"""
        with open(self.services_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.services_data = data.get("services", [])
        
        # تجهيز سياق النص بالكامل لـ Groq
        docs_summary = []
        for service in self.services_data:
            content = f"""
- خدمة ({service['id']}): {service['service_name']}
  القسم: {service['department']} | شباك: {service['window_number']}
  الوصف: {service['description']}
  الكلمات المفتاحية: {', '.join(service.get('keywords', []))}
  المستندات المطلوب: {', '.join(service.get('required_documents', []))}
  الوقت التقديري: {service.get('estimated_time_minutes', 10)} دقيقة
"""
            docs_summary.append(content)

        self.formatted_context = "\n".join(docs_summary)
        print(f"تم تحميل {len(self.services_data)} خدمة من الملف.")

    def setup_llm(self):
        self.llm = ChatGroq(
            groq_api_key=self.api_key,
            model_name=self.model_name,
            temperature=0.1,
            max_tokens=1000,
        )

    def build_chain(self):
        prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """أنت موجه ذكي في مركز الخدمة الحكومية الشامل بإمارة منطقة المدينة المنورة.
مهمتك الوحيدة هي تحديد الخدمة المناسبة للمستفيد بدقة تامة.

قواعد مهمة جداً:
1. اختر خدمة واحدة فقط — الأنسب لطلب المستفيد
2. استخدم فقط المعلومات الموجودة في قائمة الخدمات المتاحة
3. إذا لم تجد خدمة مناسبة، قل ذلك بوضوح
4. ردك يجب أن يكون JSON فقط بدون أي نص إضافي
5. جميع القيم في JSON يجب أن تكون باللغة العربية

الخدمات المتاحة في النظام:
{context}

أعد JSON بهذا الشكل بالضبط:
{{
  "service_id": "رقم الخدمة مثل S001",
  "service_name": "اسم الخدمة",
  "department": "اسم القسم",
  "window_number": رقم الشباك كرقم,
  "required_documents": ["المستند 1", "المستند 2"],
  "estimated_time_minutes": الوقت كرقم,
  "confidence": "عالية أو متوسطة أو منخفضة",
  "clarification_needed": true أو false,
  "clarification_question": "السؤال التوضيحي إن وجد"
}}""",
                ),
                ("human", "طلب المستفيد: {question}"),
            ]
        )

        self.rag_chain = prompt_template | self.llm | StrOutputParser()

    def process_request(self, user_input: str) -> dict:
        try:
            raw_response = self.rag_chain.invoke({
                "context": self.formatted_context,
                "question": user_input
            })
            return self._parse_llm_response(raw_response)
        except Exception as e:
            return {
                "error": True,
                "message": f"حدث خطأ أثناء معالجة الطلب: {str(e)}",
            }

    def _parse_llm_response(self, raw_response: str) -> dict:
        cleaned = raw_response.strip()
        json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        
        if json_match:
            try:
                result = json.loads(json_match.group())
                result["error"] = False
                return result
            except json.JSONDecodeError:
                pass

        return {
            "error": True,
            "message": "لم أتمكن من تحديد الخدمة المناسبة. يرجى توضيح طلبك.",
        }

    def initialize(self):
        print("\nبدء تهيئة نظام وجّهني السريع...")
        self.load_services()
        self.setup_llm()
        self.build_chain()
        print("النظام جاهز على Vercel بدون ثقل الذاكرة! 🚀")
