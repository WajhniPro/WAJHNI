FROM python:3.10-slim

WORKDIR /code

# نسخ ملف المتطلبات وتثبيت الحزم
COPY requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# نسخ باقي ملفات المشروع
COPY . /code

# إنشاء مجلد Output مع إعطاء صلاحيات الكتابة
RUN mkdir -p /code/output && chmod 777 /code/output

# Hugging Face Spaces يفرض استخدام البورت 7860
EXPOSE 7860

# تشغيل خادم Uvicorn على البورت 7860
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]
