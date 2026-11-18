# اطلاعات مرجع برای کد و گزارش

این فایل اطلاعاتی را نگه می‌دارد که در `seminar-plan.md` نیامده‌اند و کد و گزارش به آن‌ها نیاز دارند. این اطلاعات از جلسه‌ی قبلی با هوش مصنوعی (handoff) و از بررسی دیتاست در ۱۸ نوامبر ۲۰۲۶ گرفته شده‌اند.

## فایل‌ها

- مقاله‌ی اصلی فایل `main.pdf` است. Abdulkareem et al. 2024, JNCA 230:103980, https://doi.org/10.1016/j.jnca.2024.103980. این مقاله دسترسی آزاد با مجوز CC BY دارد.
- مقاله‌ی پشتیبان فایل `second.pdf` است. García-Merino et al. 2026, PeerJ CS 12:e3553, https://doi.org/10.7717/peerj-cs.3553. کد آن در https://github.com/uned-cibergid-projects/Study-of-DR-for-IoT-Intrusion-Detection است.
- دیتاست فایل `ids-fisel-pfi/data/ML-EdgeIIoT-dataset.csv` است. منبع آن https://www.kaggle.com/datasets/mohamedamineferrag/edgeiiotset-cyber-security-dataset-of-iot-iiot است. مرجع گروه‌بندی کلاس‌ها مقاله‌ی Ferrag et al. 2022, IEEE Access 10:40281 است.

## پیش‌پردازش مقاله (بخش ۴٫۱)

۱۹ ستون حذف می‌شوند:
`frame.time, ip.src_host, ip.dst_host, arp.dst.proto_ipv4, arp.src.proto_ipv4, http.file_data, http.request.uri.query, http.request.method, http.referer, http.request.full_uri, http.request.version, tcp.options, tcp.payload, tcp.srcport, dns.qry.name.len, mqtt.conack.flags, mqtt.msg, mqtt.protoname, mqtt.topic`

ستون `Attack_label` هم باید از ورودی حذف شود، چون برچسب دودویی است. پس از حذف این ستون‌ها، ۴۲ ویژگی عددی می‌ماند. داده با MinMax به بازه‌ی [0,1] نرمال می‌شود. scaler فقط روی داده‌ی آموزش fit می‌شود.

## نگاشت نوع حمله به کلاس

| کلاس | نوع حمله‌ها | تعداد |
|---|---|---|
| Normal | Normal | 24,301 |
| DDoS | DDoS_UDP, DDoS_ICMP, DDoS_HTTP, DDoS_TCP | 49,396 |
| Information gathering | Vulnerability_scanner, Port_Scanning, Fingerprinting | 21,148 |
| MITM | MITM | 1,214 |
| Injection | SQL_injection, Uploading, XSS | 30,632 |
| Malware | Ransomware, Backdoor, Password | 31,109 |

این تعدادها دقیقاً با جدول ۳ مقاله یکی هستند.

## روش مقاله

- FI با `ExtraTreesClassifier(criterion="entropy")` و `feature_importances_` محاسبه می‌شود.
- مقادیر k این‌ها هستند: {5, 6, 7, 8, 10, 15, 20} و حالت همه‌ی ویژگی‌ها.
- مقاله k=8 را انتخاب کرده است. هشت ویژگی برتر مقاله این‌ها هستند: tcp.dstport، tcp.ack، tcp.seq، tcp.len، tcp.checksum، tcp.ack_raw، tcp.flags و tcp.flags.ack.
- SEL معادل `StackingClassifier(estimators=[GaussianNB, LogisticRegression], final_estimator=DecisionTreeClassifier, passthrough=True, stack_method="predict")` است.
- طبق الگوریتم ۱ (ص. ۵)، مدل نهایی روی پیش‌بینی‌های مدل‌های پایه روی داده‌ی آزمون آموزش می‌بیند. اما متن ص. ۴ می‌گوید پیش‌بینی‌ها به داده‌ی آموزش اضافه می‌شوند و متن ص. ۱۱ هم مبهم است. پس نشت در مقاله احتمالی است و قطعی نیست. در گزارش بنویسید «طبق الگوریتم ۱، احتمال نشت وجود دارد» و ناسازگاری ص. ۴ را هم ذکر کنید. نسخه‌ی دارای نشت ما همین برداشت از الگوریتم ۱ را پیاده می‌کند. نتیجه‌ی فاز ۲ نشان داد برداشت لفظی الگوریتم ۱ اعداد مقاله را نمی‌سازد. نسخه‌ی دارای نشت به macro-F1 حدود ۹۰٫۴ می‌رسد، ولی جدول ۹ (۸۲٫۰۰) با نسخه‌ی بدون نشت ما (۸۲٫۵۷) می‌خواند (Q43). این شاهد کنار لحن «احتمال نشت» می‌آید.
- طبق جدول ۱۰ (ص. ۱۰)، مدل نهایی برچسب پیش‌بینی‌شده‌ی NB و LR را می‌گیرد (دو ستون `predictionNB` و `predictionLR`) و احتمال‌ها را نمی‌گیرد. به همین دلیل SEL ما با `stack_method="predict"` ساخته می‌شود (Q42).

## عددهای مقاله برای مقایسه

جدول ۹ مقاله:

| حالت | Acc | Pre | Rec | F1 | زمان آموزش (s) | زمان آزمون (s) |
|---|---|---|---|---|---|---|
| همه‌ی ویژگی‌ها | 89.05 | 90.94 | 79.53 | 82.00 | 37.23 | 0.28 |
| ۸ ویژگی | 87.37 | 90.65 | 77.73 | 80.88 | 16.18 | 0.10 |

در جدول ۶، Recall کلاس MITM برای SEL برابر ۲۹٫۲۲ درصد است. عدد ۹۹٫۹۶ درصد را مقاله‌ی دیگری به اشتباه به این کار نسبت داده و در این مقاله وجود ندارد.

## یافته‌های بررسی دیتاست

- هشت ستون مقدار ثابت دارند: `icmp.unused`، `http.tls_port`، `dns.qry.type`، `dns.retransmit_request_in`، `mqtt.msg_decoded_as`، `mbtcp.len`، `mbtcp.trans_id` و `mbtcp.unit_id`.
- فایل خام ۸۱۴ ردیف کاملاً تکراری دارد. پس از حذف ۱۹ ستون، ۵٬۵۵۵ ردیف تکراری می‌شوند.
- هیچ مقدار خالی وجود ندارد.
- یک بردار ویژگی (بردار مبهم) ۸۲۱ بار با برچسب MITM، ۹۴۱ بار با Malware، ۴۵۹ بار با Information gathering، ۴۵۴ بار با Injection، ۷۰ بار با Normal و ۲ بار با DDoS آمده است. یعنی حدود ۶۸ درصد ردیف‌های MITM از ردیف‌های کلاس‌های دیگر قابل تمایز نیستند. این بردار بردار تمام‌صفر است، یعنی همه‌ی ۴۲ ویژگی آن صفر است. تا وقتی مدل این بردار را به کلاسی غیر از MITM بدهد، recall کلاس MITM حدود ۳۲ درصد می‌ماند. این توضیح اصلی ضعف MITM است (Q44). در k=8، FI-SEL این بردار را DDoS و PFI-SEL آن را Information gathering پیش‌بینی می‌کند. `class_weight="balanced"` و SMOTE بردار را به MITM می‌دهند. در این حالت recall کلاس MITM به ۱۰۰ می‌رسد، ولی precision آن به ۳٫۵۸ (FI) و ۲۳٫۶۱ (PFI) می‌افتد و macro-F1 کم می‌شود (Q47).
- حذف تکراری‌ها macro-F1 را از حدود ۸۲٫۶ به حدود ۹۲ و recall کلاس MITM را از ۳۱٫۶ به ۹۹٫۷ می‌رساند (Q44).
- در بازپیاده‌سازی ما DT تنها با همه‌ی ویژگی‌ها به macro-F1 برابر ۸۲٫۶۱ می‌رسد، یعنی هم‌اندازه‌ی SEL (۸۲٫۵۷). مقاله برای DT عدد ۶۰٫۳۸ گزارش کرده است (Q45). SEL همگن با سه DT هم به ۸۱٫۵۰ (FI) و ۸۲٫۳۲ (PFI) در k=8 می‌رسد و آموزش آن سه تا چهار برابر سریع‌تر است (Q49).
- PCA-SEL بعد از MinMax ضعیف است. macro-F1 آن با k=8 برابر ۶۸٫۴۲ و با k=20 برابر ۷۰٫۶۷ است، در حالی که مؤلفه‌ها با k=20 حدود ۹۹٫۸ درصد واریانس را نگه می‌دارند. توضیح این افت احتمالی و آزموده‌نشده است (Q48).

## محیط سیستم

- سیستم MacBook Air M4 با macOS است و Python 3.11.9 از طریق pyenv نصب است.
- scikit-learn سراسری خراب است. فقط از `.venv` پروژه استفاده کنید.
- Node در `/opt/homebrew/bin/node` نصب است. Google Chrome برای ساخت PDF وجود دارد.
- Word، LibreOffice، LaTeX و pandoc نصب نیستند.
- فونت‌ها در `Seminar/fonts/` قرار دارند. این‌ها شامل `IRNazanin/`، `Vazirmatn/` و `latin/` (Instrument Sans، Crimson Pro و JetBrains Mono) هستند و همه مجوز OFL دارند. جزئیات در `design-reference.md` آمده است.

## سبک نوشتن کاربر

- متن به فارسی و راست‌به‌چپ است. جمله‌ها کامل و دارای فعل هستند.
- عبارت‌های بدون فعل و الگوی «برچسب: توضیح» استفاده نمی‌شود.
- نثر ساده و نزدیک به منبع است.
- پاسخ‌های چت کوتاه، صریح، بدون حاشیه و بدون ایموجی هستند.
- متادیتای فایل‌های خروجی پاک می‌شود.
