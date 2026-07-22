import json
import os
import re
import requests
import pandas as pd
from typing import Optional

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import FAISS


class DirectHFEmbeddings(Embeddings):
    def __init__(
        self,
        api_key: str,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        self.api_key = api_key
        self.api_url = f"https://router.huggingface.co/hf-inference/v1/pipeline/feature-extraction/{model_name}"
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        response = requests.post(
            self.api_url,
            headers=self.headers,
            json={"inputs": texts, "options": {"wait_for_model": True}},
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"HF API Error: {response.status_code} - {response.text}"
            )
        return response.json()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


class WajhniRAGEngine:

    def __init__(self, services_file: str, api_key: str, model_name: str):
        self.services_file = services_file
        self.api_key = api_key
        self.model_name = model_name
        self.services_data = []
        self.excel_data = None
        self.vectorstore = None
        self.llm = None
        self.rag_chain = None

    def load_excel_times(self):
        self.excel_data = pd.read_excel(
            "data/sedco_dashboard_full_3000_formatted.xlsx"
        )

    def load_services(self) -> list:
        with open(self.services_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.services_data = data["services"]
        documents = []

        for service in self.services_data:
            estimated_time = service["estimated_time_minutes"]

            match = self.excel_data[
                self.excel_data["اسم_الخدمة"] == service["service_name"]
            ]

            if not match.empty:
                estimated_time = int(match["مدة_الخدمة_دقيقة"].mean())

            content = f"""
الخدمة: {service['service_name']}
القسم: {service['department']}
رقم الشباك: {service['window_number']}
الوصف: {service['description']}
الكلمات المفتاحية: {', '.join(service['keywords'])}
المستندات المطلوبة: {', '.join(service['required_documents'])}
الوقت التقديري: {estimated_time} دقيقة
رقم الخدمة: {service['id']}
""".strip()
            doc = Document(
                page_content=content,
                metadata={
                    "service_id": service["id"],
                    "service_name": service["service_name"],
                    "department": service["department"],
                    "window_number": service["window_number"],
                    "estimated_time_minutes": estimated_time,
                },
            )
            documents.append(doc)

        print(f" تم تحميل {len(documents)} خدمة من الملف.")
        return documents

    def build_vectorstore(self, documents: list):
        # استخدام الاتصال المباشر لـ Hugging Face لمنع استهلاك RAM ومشاكل الـ DNS
        hf_token = os.getenv("HF_TOKEN")
        embeddings = DirectHFEmbeddings(api_key=hf_token)

        self.vectorstore = FAISS.from_documents(documents, embeddings)

    def setup_llm(self):
        self.llm = ChatGroq(
            groq_api_key=self.api_key,
            model_name=self.model_name,
            temperature=0.1,
            max_tokens=1000,
        )
        print(f" تم تهيئة النموذج: {self.model_name}")

    def build_chain(self):
        retriever = self.vectorstore.as_retriever(
            search_type="similarity", search_kwargs={"k": 3}
        )

        prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """أنت موجه ذكي في مركز الخدمة الحكومية الشامل بإمارة منطقة المدينة المنورة.
مهمتك الوحيدة هي تحديد الخدمة المناسبة للمستفيد بدقة تامة.

قواعد مهمة جداً:
1. اختر خدمة واحدة فقط — الأنسب لطلب المستفيد
2. استخدم فقط المعلومات الموجودة في السياق أدناه
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
  "clarification_question": "السؤال التوضيحي إذا احتجت توضيحاً وإلا اتركه فارغاً"
}}""",
                ),
                ("human", "طلب المستفيد: {question}"),
            ]
        )

        def format_docs(docs):
            return "\n\n---\n\n".join([doc.page_content for doc in docs])

        self.rag_chain = (
            {
                "context": retriever | format_docs,
                "question": RunnablePassthrough(),
            }
            | prompt_template
            | self.llm
            | StrOutputParser()
        )

        print("تم بناء سلسلة RAG بنجاح.")

    def process_request(self, user_input: str) -> dict:
        print(f"\n🔍 معالجة الطلب: {user_input}")

        try:
            raw_response = self.rag_chain.invoke(user_input)
            result = self._parse_llm_response(raw_response)
            return result
        except Exception as e:
            return {
                "error": True,
                "message": f"حدث خطأ أثناء معالجة الطلب: {str(e)}",
            }

    def _parse_llm_response(self, raw_response: str) -> dict:
        cleaned = raw_response.strip()

        json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            result = json.loads(json_str)
            result["error"] = False

            for service in self.services_data:
                if service["id"] == result.get("service_id"):
                    # تعديل اسم العمود المرجعي إلى "اسم_الخدمة" بدلاً من "service_name"
                    match = self.excel_data[
                        self.excel_data["اسم_الخدمة"] == service["service_name"]
                    ]

                    if not match.empty:
                        result["estimated_time_minutes"] = int(
                            match.iloc[0]["مدة_الخدمة_دقيقة"]
                        )
                    break

            return result

        return {
            "error": True,
            "message": "لم أتمكن من تحديد الخدمة المناسبة. يرجى توضيح طلبك.",
        }

    def initialize(self):
        print("\n بدء تهيئة نظام وجّهني...\n")
        self.load_excel_times()
        documents = self.load_services()
        self.build_vectorstore(documents)
        self.setup_llm()
        self.build_chain()
        print("\n النظام جاهز لاستقبال طلبات المستفيدين.\n")
