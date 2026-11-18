# فاز ۱: محیط، git و آماده‌سازی داده

قبل از شروع، قواعد مشترک `phases/README.md` را بخوانید.

## هدف

محیط پایتون و مخزن git ساخته می‌شود. یک ماژول داده‌ی تست‌شده هم نوشته می‌شود که فازهای بعدی از آن استفاده می‌کنند.

## کارها

1. در `Seminar/` دستور `git init` را اجرا کنید. این تنها دستور git است که این فاز اجرا می‌کند. پوشه‌ی `fonts/` ignore نمی‌شود (Q40). `.gitignore` این موارد را شامل شود: `ids-fisel-pfi/data/`، `**/.venv/`، `node_modules/`، `main.pdf`، `second.pdf`، `.DS_Store`، `__pycache__/` و `.ipynb_checkpoints/`.
2. ساختار `ids-fisel-pfi/` را طبق Q14 بسازید.
3. با `~/.pyenv/versions/3.11.9/bin/python -m venv ids-fisel-pfi/.venv` محیط را بسازید. این بسته‌ها را نصب کنید: numpy، pandas، scikit-learn (نسخه‌ی پایدار فعلی)، matplotlib، imbalanced-learn، joblib، ipykernel و jupyter. سپس `pip freeze` را در `requirements.txt` بنویسید. اگر بسته‌ای در فاز بعد اضافه شد، این فایل دوباره ساخته شود.
4. یک kernel با نام `ids-fisel-pfi` برای Jupyter ثبت کنید.
5. فایل `src/config.py` را بسازید. این فایل مسیرها، `SEEDS = [42, 0, 1, 2, 3]`، `K_VALUES = [5, 6, 7, 8, 10, 15, 20]`، فهرست ۱۹ ستون حذفی و نگاشت نوع حمله به کلاس را نگه می‌دارد. مقادیر را از `reference-facts.md` بردارید.
6. فایل `src/data.py` را بسازید. این تابع‌ها لازم هستند:
   - `load_dataset(dedup=False)` فایل را می‌خواند، ستون‌ها را حذف می‌کند، `Attack_label` را کنار می‌گذارد و `X` و `y` (شش کلاس) را برمی‌گرداند. اگر `dedup=True` باشد، تکراری‌ها پس از حذف ستون‌ها و قبل از تقسیم حذف می‌شوند.
   - `split(X, y, seed)` تقسیم stratified را انجام می‌دهد. ۸۰ درصد آموزش و ۲۰ درصد آزمون است. سپس ۲۰ درصد از آموزش برای اعتبارسنجی جدا می‌شود. خروجی شامل `X_fit`، `X_val`، `X_train` (برابر fit به‌اضافه‌ی val)، `X_test` و yهای متناظر است.
   - MinMaxScaler بخشی از pipeline مدل است و نباید داخل `data.py` روی کل داده fit شود.
7. یک اسکریپت بررسی کوتاه بنویسید و اجرا کنید. این اسکریپت درستی این موارد را نشان می‌دهد: ۴۲ ستون ویژگی، تعداد هر کلاس برابر جدول `reference-facts.md`، نبودن `Attack_label` و `Attack_type` در X، و stratified بودن تقسیم‌ها. خروجی آن را در `results/tables/class_counts.csv` ذخیره کنید.
8. یک `README.md` اولیه طبق Q36 بنویسید (توضیح فارسی و دستور نصب انگلیسی).

## خروجی‌ها و شرط پایان

- `.venv` کار می‌کند و `import sklearn` بدون خطا اجرا می‌شود.
- اسکریپت بررسی بدون خطا اجرا می‌شود و `class_counts.csv` ساخته شده است.
- متن پیشنهادی commit در چت نوشته شده است. commit انجام نشده است.
