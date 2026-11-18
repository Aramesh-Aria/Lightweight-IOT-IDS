# پیوست {#sec:appendix}

## ساختار کد و دستور اجرا {#sec:app-code}

کد بازپیاده‌سازی در پوشه‌ی `ids-fisel-pfi/` قرار دارد. @tbl:app-code نقش هر فایل را نشان می‌دهد. نتایج در `results/tables/` به شکل CSV و در `results/figures/` به شکل PNG ذخیره می‌شوند. خلاصه‌ی فارسی همه‌ی نتایج در `results/SUMMARY.md` آمده است.

| فایل | نقش |
|---|---|
| `src/config.py` | مسیرها، seedها، مقدارهای k، ستون‌های حذف‌شده و نگاشت کلاس‌ها |
| `src/data.py` | خواندن دیتاست، حذف ستون‌ها و ردیف‌های تکراری و تقسیم stratified |
| `src/check_data.py` | بررسی تعداد کلاس‌ها، ستون‌های ثابت و مقدارهای خالی |
| `src/selection.py` | رتبه‌بندی FI، PFI و MI |
| `src/models.py` | ساخت pipeline، SEL، مدل‌های تکی، نسخه‌ی دارای نشت، SEL همگن، PCA و SMOTE |
| `src/evaluate.py` | معیارها، زمان‌سنجی و اندازه‌گیری حجم pipeline |
| `src/ambiguity.py` | شناسایی بردارهای مبهم و محاسبه‌ی سقف recall |
| `src/tables.py` و `src/figures.py` | ساخت جدول‌ها و نمودارها از نتایج ذخیره‌شده |
| `src/summary.py` | ساخت `results/SUMMARY.md` از جدول‌ها |
| `run_experiments.py` | اجرای همه‌ی آزمایش‌ها با cache |
| `notebooks/demo.ipynb` | نمایش کوتاه مراحل برای seed=42 |

: فایل‌های کد بازپیاده‌سازی {#tbl:app-code}

دیتاست در مخزن نیست و باید از Kaggle دریافت و در `data/` قرار داده شود. دستورهای زیر از ریشه‌ی `ids-fisel-pfi/` محیط را می‌سازند و همه‌ی آزمایش‌ها را اجرا می‌کنند. اجرای کامل روی MacBook Air M4 حدود ۴۷ دقیقه طول می‌کشد.

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m src.check_data
.venv/bin/python run_experiments.py all
.venv/bin/python -m src.summary
```

## فهرست ویژگی‌ها {#sec:app-features}

@tbl:method-features ۴۲ ویژگی ورودی مدل را پس از حذف ۱۹ ستون بر حسب پروتکل نشان می‌دهد.

| پروتکل | تعداد | ویژگی‌ها |
|---|---|---|
| ARP | ۲ | `arp.opcode`، `arp.hw.size` |
| ICMP | ۴ | `icmp.checksum`، `icmp.seq_le`، `icmp.transmit_timestamp`، `icmp.unused` (ثابت) |
| HTTP | ۳ | `http.content_length`، `http.response`، `http.tls_port` (ثابت) |
| TCP | ۱۲ | `tcp.ack`، `tcp.ack_raw`، `tcp.checksum`، `tcp.connection.fin`، `tcp.connection.rst`، `tcp.connection.syn`، `tcp.connection.synack`، `tcp.dstport`، `tcp.flags`، `tcp.flags.ack`، `tcp.len`، `tcp.seq` |
| UDP | ۳ | `udp.port`، `udp.stream`، `udp.time_delta` |
| DNS | ۶ | `dns.qry.name`، `dns.qry.qu`، `dns.qry.type` (ثابت)، `dns.retransmission`، `dns.retransmit_request`، `dns.retransmit_request_in` (ثابت) |
| MQTT | ۹ | `mqtt.conflag.cleansess`، `mqtt.conflags`، `mqtt.hdrflags`، `mqtt.len`، `mqtt.msg_decoded_as` (ثابت)، `mqtt.msgtype`، `mqtt.proto_len`، `mqtt.topic_len`، `mqtt.ver` |
| Modbus/TCP | ۳ | `mbtcp.len` (ثابت)، `mbtcp.trans_id` (ثابت)، `mbtcp.unit_id` (ثابت) |

: ۴۲ ویژگی ورودی بر حسب پروتکل. ستون‌هایی که در کل فایل مقدار ثابت دارند با «ثابت» مشخص شده‌اند {#tbl:method-features}

## معیارهای weighted {#sec:app-weighted}

@tbl:app-weighted میانگین weighted معیارها را برای چند حالت اصلی نشان می‌دهد. در میانگین weighted وزن هر کلاس سهم آن از داده‌ی آزمون است. چون MITM کمتر از یک درصد داده است، ضعف این کلاس در این معیارها کم دیده می‌شود. recall weighted همیشه با accuracy برابر است.

| حالت | Accuracy | Precision (weighted) | Recall (weighted) | F1 (weighted) |
|---|---|---|---|---|
| FI-SEL، k=8 | ۸۷٫۷۲ ± ۰٫۱۱ | ۸۸٫۰۰ ± ۰٫۱۰ | ۸۷٫۷۲ ± ۰٫۱۱ | ۸۷٫۶۲ ± ۰٫۱۰ |
| PFI-SEL، k=8 | ۸۹٫۱۳ ± ۰٫۱۲ | ۸۹٫۴۱ ± ۰٫۱۲ | ۸۹٫۱۳ ± ۰٫۱۲ | ۸۸٫۹۶ ± ۰٫۱۲ |
| MI-SEL، k=8 | ۸۷٫۷۷ ± ۰٫۰۶ | ۸۸٫۰۶ ± ۰٫۰۶ | ۸۷٫۷۷ ± ۰٫۰۶ | ۸۷٫۶۷ ± ۰٫۰۶ |
| PCA-SEL، k=8 | ۷۲٫۹۸ ± ۰٫۱۴ | ۷۳٫۱۶ ± ۰٫۱۸ | ۷۲٫۹۸ ± ۰٫۱۴ | ۷۲٫۹۲ ± ۰٫۱۶ |
| SEL، همه‌ی ویژگی‌ها | ۸۹٫۲۵ ± ۰٫۰۷ | ۸۹٫۳۵ ± ۰٫۰۶ | ۸۹٫۲۵ ± ۰٫۰۷ | ۸۹٫۱۵ ± ۰٫۰۷ |

: میانگین weighted معیارها برای SEL بدون نشت (میانگین ± انحراف معیار پنج seed) {#tbl:app-weighted}

## فهرست فرض‌ها {#sec:app-assumptions}

@tbl:app-assumptions همه‌ی فرض‌های بازپیاده‌سازی را برای مواردی نشان می‌دهد که مقاله‌ی اصلی گزارش نکرده یا مبهم گذاشته است.

| موضوع | فرض ما | دلیل |
|---|---|---|
| ابرپارامترها | پیش‌فرض scikit-learn 1.9.1 | مقاله هیچ ابرپارامتری گزارش نکرده است |
| LR | `max_iter=1000` | تنها انحراف از پیش‌فرض، برای اطمینان از همگرایی |
| تقسیم داده | ۸۰ به ۲۰، stratified | stratified بودن در مقاله نیامده است |
| داده‌ی اعتبارسنجی | ۲۰ درصد داده‌ی آموزش | لازم برای PFI بدون استفاده از داده‌ی آزمون |
| داده‌ی رتبه‌بندی | بخش fit برای FI، PFI و MI | داده‌ی یکسان برای همه‌ی روش‌ها |
| PFI | ExtraTrees، `n_repeats=10`، macro-F1 روی داده‌ی اعتبارسنجی | مقاله‌ی پشتیبان این تنظیم‌ها را گزارش نکرده است |
| seed | ۴۲، ۰، ۱، ۲ و ۳ | مقاله seed را گزارش نکرده است |
| نگاشت کلاس‌ها | گروه‌بندی Ferrag و همکاران | تعداد کلاس‌ها با جدول ۳ مقاله یکی است |
| ستون‌های ثابت | نگه داشته می‌شوند | مقاله آن‌ها را حذف نکرده است |
| ردیف‌های تکراری | در اجرای اصلی نگه داشته می‌شوند | مقاله درباره‌ی آن‌ها چیزی نگفته است |
| ورودی مدل نهایی | برچسب پیش‌بینی‌شده (`stack_method="predict"`) | جدول ۱۰ مقاله |
| آموزش مدل نهایی | اعتبارسنجی متقابل ۵-fold روی داده‌ی آموزش | نسخه‌ی بدون نشت؛ برداشت الگوریتم ۱ جدا اجرا شد |
| نوع میانگین | macro | با جدول ۵ و ۶ مقاله می‌خواند |
| زمان‌سنجی | `n_jobs=1`، روی MacBook Air M4 | مقایسه با مقاله فقط روی نسبت‌ها |
| حجم | فایل joblib کل pipeline | مقاله حجم را اندازه نگرفته است |
| PCA | بعد از MinMax و به‌جای انتخاب ویژگی | همان پیش‌پردازش روش‌های دیگر |

: فرض‌های بازپیاده‌سازی {#tbl:app-assumptions}

## استفاده از دستیار هوش مصنوعی {#sec:app-ai}

در این سمینار از یک دستیار هوش مصنوعی برای کمک در کدنویسی و ویرایش متن استفاده شد. همه‌ی نتایج بازبینی شده‌اند.
