from pathlib import Path
import numpy as np
import pandas as pd


# ------------------------------ 
N_RECORDS = 3000
SEED = 20260719
OUTPUT_FILE = Path("sedco_dashboard_generated.xlsx")
rng = np.random.default_rng(SEED)

BRANCHES = {
    "BR-01": "الرئيسي - رجال",
    "BR-02": "الرئيسي - نساء",
    "BR-03": "الدائري",
    "BR-04": "ينبع",
}
BRANCH_WEIGHTS = [0.32, 0.27, 0.23, 0.18]

SERVICES = {
    "الأحوال المدنية": ["تجديد الهوية الوطنية", "إصدار هوية وطنية جديدة", "طباعة شهادة ميلاد", "حجز موعد الأحوال"],
    "الجوازات": ["تجديد إقامة", "إصدار إقامة جديدة", "إلغاء تأشيرة خروج وعودة", "تعديل بيانات جواز"],
    "المرور": ["الاستعلام عن المخالفات المرورية", "إسقاط مركبة", "بدل تالف رخصة قيادة", "تجديد رخصة قيادة"],
    "وزارة العدل": ["إصدار وكالة", "إثبات طلاق", "طلب إفراغ عقار", "حجز موعد كتابة عدل"],
    "مكتب العمل": ["تجديد رخصة عمل", "استعلام عن وافد", "استعلام عن معلومات منشأة"],
    "الضمان الاجتماعي": ["طباعة مشهد الضمان", "رفع مستندات الضمان"],
    "التأمينات الاجتماعية": ["استعلام المستحقات التأمينية", "تعريف بالخدمات والحسابات"],
    "شركة المياه": ["كشف تسربات", "طلب عداد مياه"],
}
SERVICE_PAIRS = [(agency, service) for agency, items in SERVICES.items() for service in items]
AGENCY_WEIGHTS = np.array([1.10 if s == "تجديد رخصة عمل" else 1.0 for _, s in SERVICE_PAIRS], dtype=float)
AGENCY_WEIGHTS /= AGENCY_WEIGHTS.sum()

AR_DAYS = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
NATIONALITIES = ["سعودي", "مصري", "سوري", "باكستاني", "بنغلاديشي", "أردني", "يمني", "هندي"]


def age_band(age: int) -> str:
    if age < 18:
        return "أقل من 18"
    if age <= 25:
        return "18-25"
    if age <= 35:
        return "26-35"
    if age <= 45:
        return "36-45"
    if age <= 55:
        return "46-55"
    return "56+"


def satisfaction_label(score: int) -> str:
    if score < 60:
        return "ضعيف"
    if score < 75:
        return "متوسط"
    if score < 85:
        return "جيد"
    if score < 95:
        return "جيد جدًا"
    return "ممتاز"


def make_raw_data(n: int = N_RECORDS) -> pd.DataFrame:
    """ينشئ بيانات أولية مقصود فيها بعض القيم الناقصة/المكررة لتوضيح التنظيف."""
    dates = pd.Timestamp("2026-01-01") + pd.to_timedelta(rng.integers(0, 181, n), unit="D")
    minutes = rng.integers(8 * 60, 18 * 60, n)
    branch_ids = rng.choice(list(BRANCHES), n, p=BRANCH_WEIGHTS)
    service_ix = rng.choice(len(SERVICE_PAIRS), n, p=AGENCY_WEIGHTS)
    agencies = [SERVICE_PAIRS[i][0] for i in service_ix]
    services = [SERVICE_PAIRS[i][1] for i in service_ix]
    genders = rng.choice(["ذكر", "أنثى"], n, p=[0.55, 0.45])
    beneficiary = rng.choice(["مواطن", "مقيم"], n, p=[0.62, 0.38])
    ages = rng.choice(np.arange(14, 70), n, p=np.linspace(0.3, 0.03, 56) / np.linspace(0.3, 0.03, 56).sum())
    channels = rng.choice(["إلكتروني", "حضوري في الفرع"], n, p=[0.56, 0.44])
    statuses = rng.choice(["مكتمل", "قيد المعالجة", "ملغي"], n, p=[0.88, 0.08, 0.04])
    priorities = rng.choice(["عادي", "متوسط", "عاجل"], n, p=[0.72, 0.20, 0.08])

    branch_delay = {"BR-01": 8, "BR-02": 1, "BR-03": 0, "BR-04": -3}
    wait = np.array([max(1, round(rng.gamma(3.0, 8) + branch_delay[b])) for b in branch_ids])
    service_time = np.clip(np.round(rng.gamma(3.2, 4.5), 0), 2, 55).astype(int)
    total_time = wait + service_time
    score = np.clip(np.rint(100 - total_time * 0.35 + rng.normal(0, 8, n)), 40, 100).astype(int)

    data = pd.DataFrame({
        "رقم_الطلب": [f"REQ-{d:%Y%m%d}-{i:05d}" for i, d in enumerate(dates, 1)],
        "TXID": [f"TX-{x:07d}" for x in rng.integers(1_000_000, 9_999_999, n)],
        "تاريخ_الزيارة": dates,
        "وقت_الحضور": [f"{m // 60:02d}:{m % 60:02d}" for m in minutes],
        "معرف_الفرع": branch_ids,
        "اسم_الفرع": [BRANCHES[b] for b in branch_ids],
        "معرف_الخدمة": [f"SVC-{x:04d}" for x in rng.integers(1000, 9999, n)],
        "اسم_الجهة": agencies,
        "اسم_الخدمة": services,
        "الجنس": genders,
        "نوع_المستفيد": beneficiary,
        "الجنسية": ["سعودي" if b == "مواطن" else rng.choice(NATIONALITIES[1:]) for b in beneficiary],
        "العمر": ages,
        "قناة_الطلب": channels,
        "حالة_الطلب": statuses,
        "الأولوية": priorities,
        "مدة_الانتظار_دقيقة": wait,
        "مدة_الخدمة_دقيقة": service_time,
        "مدة_الإنجاز_الكلية_دقيقة": total_time,
        "التقييم_%": score,
        "معرف_الموظف": [f"EMP-{x:03d}" for x in rng.integers(101, 141, n)],
        "معرف_الكاونتر": [f"C-{x}" for x in rng.integers(1, 19, n)],
    })
    # أمثلة على مشاكل واقعية يعالجها جزء التنظيف (أقل من 1% من الصفوف).
    data.loc[rng.choice(n, 8, replace=False), "الجنسية"] = " "
    return pd.concat([data, data.iloc[[0]]], ignore_index=True)  # صف مكرر واحد للتجربة


def clean_and_enrich(raw: pd.DataFrame) -> pd.DataFrame:
    """تنظيف: إزالة التكرار، معالجة النصوص الناقصة، تصحيح الأنواع، ثم أعمدة مشتقة."""
    df = raw.copy()
    df = df.drop_duplicates(subset="رقم_الطلب", keep="first")
    text_cols = df.select_dtypes(include=["object", "string"]).columns
    df[text_cols] = df[text_cols].apply(lambda c: c.str.strip())
    df["الجنسية"] = df["الجنسية"].replace("", np.nan).fillna("غير محدد")
    df["تاريخ_الزيارة"] = pd.to_datetime(df["تاريخ_الزيارة"], errors="coerce")
    df = df.dropna(subset=["تاريخ_الزيارة", "اسم_الفرع", "اسم_الخدمة"])
    df["اليوم"] = df["تاريخ_الزيارة"].dt.dayofweek.map(dict(enumerate(AR_DAYS)))
    df["الشهر"] = df["تاريخ_الزيارة"].dt.month
    df["السنة_الشهر"] = df["تاريخ_الزيارة"].dt.strftime("%Y-%m")
    df["الفئة_العمرية"] = df["العمر"].map(age_band)
    df["تصنيف_الرضا"] = df["التقييم_%"].map(satisfaction_label)
    df["تجاوز_هدف_الانتظار"] = np.where(df["مدة_الانتظار_دقيقة"] > 30, "نعم", "لا")
    df["تجاوز_هدف_الخدمة"] = np.where(df["مدة_الخدمة_دقيقة"] > 15, "نعم", "لا")
    df["مصدر_الصف"] = "بيانات مولدة ومحسنة"
    df["ملاحظة"] = "بيانات مولّدة لأغراض بناء الداشبورد مع مراعاة منطق الجهة والخدمة"

    order = ["رقم_الطلب", "TXID", "تاريخ_الزيارة", "وقت_الحضور", "اليوم", "الشهر", "السنة_الشهر",
             "معرف_الفرع", "اسم_الفرع", "معرف_الخدمة", "اسم_الجهة", "اسم_الخدمة", "الجنس",
             "نوع_المستفيد", "الجنسية", "العمر", "الفئة_العمرية", "قناة_الطلب", "حالة_الطلب",
             "الأولوية", "مدة_الانتظار_دقيقة", "مدة_الخدمة_دقيقة", "مدة_الإنجاز_الكلية_دقيقة",
             "التقييم_%", "تصنيف_الرضا", "معرف_الموظف", "معرف_الكاونتر", "تجاوز_هدف_الانتظار",
             "تجاوز_هدف_الخدمة", "مصدر_الصف", "ملاحظة"]
    return df[order].sort_values(["تاريخ_الزيارة", "رقم_الطلب"]).reset_index(drop=True)


def make_summaries(df: pd.DataFrame):
    agg = {"رقم_الطلب": "count", "مدة_الانتظار_دقيقة": "mean", "مدة_الخدمة_دقيقة": "mean",
           "مدة_الإنجاز_الكلية_دقيقة": "mean", "التقييم_%": "mean"}
    branches = df.groupby("اسم_الفرع", as_index=False).agg(agg).rename(columns={
        "رقم_الطلب": "عدد_المستفيدين", "مدة_الانتظار_دقيقة": "متوسط_الانتظار",
        "مدة_الخدمة_دقيقة": "متوسط_الخدمة", "مدة_الإنجاز_الكلية_دقيقة": "متوسط_الإنجاز",
        "التقييم_%": "متوسط_الرضا_%"})
    for col, name in [("تجاوز_هدف_الانتظار", "تجاوزات_الانتظار"), ("تجاوز_هدف_الخدمة", "تجاوزات_الخدمة")]:
        branches[name] = df[col].eq("نعم").groupby(df["اسم_الفرع"]).sum().reindex(branches["اسم_الفرع"]).to_numpy()
    branches = branches.sort_values("عدد_المستفيدين", ascending=False)

    services = df.groupby(["اسم_الجهة", "اسم_الخدمة"], as_index=False).agg(agg).rename(columns={
        "رقم_الطلب": "عدد_الطلبات", "مدة_الانتظار_دقيقة": "متوسط_الانتظار",
        "مدة_الخدمة_دقيقة": "متوسط_الخدمة", "مدة_الإنجاز_الكلية_دقيقة": "متوسط_الإنجاز",
        "التقييم_%": "متوسط_الرضا_%"})
    for col, name in [("تجاوز_هدف_الانتظار", "تجاوزات_الانتظار"), ("تجاوز_هدف_الخدمة", "تجاوزات_الخدمة")]:
        services[name] = df[col].eq("نعم").groupby([df["اسم_الجهة"], df["اسم_الخدمة"]]).sum().reindex(pd.MultiIndex.from_frame(services[["اسم_الجهة", "اسم_الخدمة"]])).to_numpy()
    services = services.sort_values("عدد_الطلبات", ascending=False)

    demo_parts = []
    for field, label in [("الجنس", "الجنس"), ("نوع_المستفيد", "نوع المستفيد"), ("الفئة_العمرية", "الفئة العمرية"), ("قناة_الطلب", "قناة الطلب")]:
        counts = df[field].value_counts().rename_axis("القيمة").reset_index(name="عدد_الطلبات")
        counts.insert(0, "المحور", label)
        counts["النسبة"] = counts["عدد_الطلبات"] / len(df)
        demo_parts.append(counts)
    demographics = pd.concat(demo_parts, ignore_index=True)
    return branches.round(2), services.round(2), demographics.round(4)


def write_excel(df, branches, services, demographics, filename=OUTPUT_FILE):
    """تصدير كل الأوراق والـ Dashboard بتنسيق قريب من الملف المرجعي."""
    with pd.ExcelWriter(filename, engine="xlsxwriter", datetime_format="yyyy-mm-dd") as writer:
        df.to_excel(writer, sheet_name="طلبات_محسنة", index=False)
        branches.to_excel(writer, sheet_name="ملخص_الفروع", index=False)
        services.to_excel(writer, sheet_name="ملخص_الخدمات", index=False)
        demographics.to_excel(writer, sheet_name="ملخص_الديموغرافيا", index=False)

        workbook = writer.book
        header = workbook.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": "#1F4E78", "align": "center", "valign": "vcenter", "border": 1})
        title = workbook.add_format({"bold": True, "font_size": 18, "font_color": "#FFFFFF", "bg_color": "#1F4E78", "align": "center", "valign": "vcenter"})
        kpi_label = workbook.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": "#5B9BD5", "align": "center", "border": 1})
        kpi_value = workbook.add_format({"bold": True, "font_size": 14, "bg_color": "#D9EAF7", "align": "center", "border": 1, "num_format": "#,##0.00"})
        percent = workbook.add_format({"num_format": "0.00%"})
        number = workbook.add_format({"num_format": "#,##0.00"})

        for name, frame in [("طلبات_محسنة", df), ("ملخص_الفروع", branches), ("ملخص_الخدمات", services), ("ملخص_الديموغرافيا", demographics)]:
            ws = writer.sheets[name]
            ws.right_to_left()
            ws.freeze_panes(1, 0)
            ws.autofilter(0, 0, len(frame), len(frame.columns) - 1)
            ws.set_row(0, 28, header)
            ws.set_column(0, len(frame.columns) - 1, 16)
            if name == "طلبات_محسنة":
                ws.set_column(0, 1, 20); ws.set_column(8, 11, 24); ws.set_column(29, 30, 42)
            if name == "ملخص_الخدمات": ws.set_column(0, 1, 30)
            if name == "ملخص_الديموغرافيا": ws.set_column(0, 1, 20); ws.set_column(3, 3, 12, percent)
            for col in [c for c in frame.columns if c.startswith("متوسط_") or c == "التقييم_%"]:
                ws.set_column(frame.columns.get_loc(col), frame.columns.get_loc(col), 15, number)

        dashboard = workbook.add_worksheet("Dashboard")
        dashboard.right_to_left(); dashboard.hide_gridlines(2)
        dashboard.set_column("A:H", 18); dashboard.set_column("J:L", 20)
        dashboard.merge_range("A1:L1", "لوحة متابعة طلبات مركز الخدمات الحكومية", title)
        total = len(df)
        kpis = [("إجمالي الطلبات", total), ("متوسط الانتظار", df["مدة_الانتظار_دقيقة"].mean()),
                ("متوسط الخدمة", df["مدة_الخدمة_دقيقة"].mean()), ("متوسط الإنجاز", df["مدة_الإنجاز_الكلية_دقيقة"].mean()),
                ("متوسط الرضا", df["التقييم_%"].mean()), ("عدد التجاوزات", int((df["تجاوز_هدف_الانتظار"].eq("نعم") | df["تجاوز_هدف_الخدمة"].eq("نعم")).sum()))]
        for i, (label, value) in enumerate(kpis):
            dashboard.write(2, i, label, kpi_label); dashboard.write(3, i, value, kpi_value)
        dashboard.write(2, 6, "أكثر خدمة طلبًا", kpi_label); dashboard.write(3, 6, services.iloc[0]["اسم_الخدمة"], kpi_value)
        dashboard.write(2, 7, "أعلى فرع ضغطًا", kpi_label); dashboard.write(3, 7, branches.iloc[0]["اسم_الفرع"], kpi_value)
        dashboard.write(6, 0, "ملخص الفروع", header)
        dashboard.write_row(7, 0, branches.columns.tolist(), header)
        for r, row in enumerate(branches.itertuples(index=False), 8): dashboard.write_row(r, 0, row)
        dashboard.write(6, 9, "أكثر الخدمات طلبًا", header)
        top_services = services.head(8)[["اسم_الخدمة", "اسم_الجهة", "عدد_الطلبات"]]
        dashboard.write_row(7, 9, top_services.columns.tolist(), header)
        for r, row in enumerate(top_services.itertuples(index=False), 8): dashboard.write_row(r, 9, row)

        chart = workbook.add_chart({"type": "column"})
        chart.add_series({"name": "عدد الطلبات", "categories": "=Dashboard!$J$9:$J$16", "values": "=Dashboard!$L$9:$L$16", "fill": {"color": "#5B9BD5"}})
        chart.set_title({"name": "الخدمات الأعلى طلبًا"}); chart.set_legend({"none": True}); chart.set_size({"width": 640, "height": 300})
        dashboard.insert_chart("A15", chart)

        # قاموس بيانات مختصر مطابق للغرض من الملف المرجعي.
        dictionary = pd.DataFrame({"العمود": df.columns, "الوصف": ["حقل بيانات طلب/زيارة يُستخدم في التحليل والفلترة." for _ in df.columns], "طريقة الاستخدام في الداشبورد": ["فلترة / تجميع / مقارنة حسب المؤشر" for _ in df.columns]})
        dictionary.to_excel(writer, sheet_name="قاموس_البيانات", index=False)
        ws = writer.sheets["قاموس_البيانات"]; ws.right_to_left(); ws.set_row(0, 28, header); ws.set_column("A:A", 28); ws.set_column("B:C", 48)

        approved_lists = pd.DataFrame({
            "الفئة": ["الفروع", "قناة الطلب", "الجنس", "نوع المستفيد", "حالة الطلب", "الأولوية", "تصنيف الرضا"],
            "القيم_المعتمدة": [" / ".join(BRANCHES.values()), "إلكتروني / حضوري في الفرع", "ذكر / أنثى",
                                "مواطن / مقيم", "مكتمل / قيد المعالجة / ملغي", "عادي / متوسط / عاجل",
                                "ضعيف / متوسط / جيد / جيد جدًا / ممتاز"]
        })
        approved_lists.to_excel(writer, sheet_name="القوائم", index=False)
        ws = writer.sheets["القوائم"]; ws.right_to_left(); ws.set_row(0, 28, header); ws.set_column("A:A", 22); ws.set_column("B:B", 95)


if __name__ == "__main__":
    raw_data = make_raw_data()
    clean_data = clean_and_enrich(raw_data)
    branch_summary, service_summary, demographic_summary = make_summaries(clean_data)
    write_excel(clean_data, branch_summary, service_summary, demographic_summary)
    print(f"تم إنشاء: {OUTPUT_FILE.resolve()}")
    print(f"عدد الطلبات بعد التنظيف: {len(clean_data):,}")