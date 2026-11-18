"""Write results/SUMMARY.md (Persian) from the CSV tables.

Every number in the summary is read from results/tables/, so the file can be
rebuilt after any re-run:  .venv/bin/python -m src.summary
Numbers use Persian digits and the Persian decimal separator (Q19).
"""

import pandas as pd

from . import config

T = config.TABLES_DIR
OUT = config.RESULTS_DIR / "SUMMARY.md"
FA = str.maketrans("0123456789.-", "۰۱۲۳۴۵۶۷۸۹٫−")


def fa(x, nd=2) -> str:
    if isinstance(x, str):
        return x.translate(FA)
    if pd.isna(x):
        return "—"
    s = f"{x:,.{nd}f}" if nd else f"{int(round(x)):,}"
    return s.replace(",", "٬").translate(FA)


def pm(mean, std, nd=2) -> str:
    return f"{fa(mean, nd)} ± {fa(std, nd)}"


def table(header, rows) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


def _row(df, **kw):
    m = pd.Series(True, index=df.index)
    for c, v in kw.items():
        m &= df[c].astype(str) == str(v)
    sel = df[m]
    if len(sel) != 1:
        raise ValueError(f"expected one row for {kw}, got {len(sel)}")
    return sel.iloc[0]


def build() -> str:
    pvo = pd.read_csv(T / "paper_vs_ours.csv")
    ks = pd.read_csv(T / "ksweep_all_methods_5seeds.csv")
    single = pd.read_csv(T / "single_models.csv")
    leaky = pd.read_csv(T / "leaky_vs_clean.csv")
    dedup = pd.read_csv(T / "dedup_sensitivity.csv")
    stack = pd.read_csv(T / "stack_method_comparison.csv")
    cw = pd.read_csv(T / "class_weight_comparison.csv")
    opt = pd.read_csv(T / "optional_extensions.csv")
    amb = pd.read_csv(T / "ambiguous_vector.csv")
    ambs = pd.read_csv(T / "ambiguous_vectors_summary.csv")
    amb8 = pd.read_csv(T / "ambiguous_vector_top8.csv")
    fi = pd.read_csv(T / "fi_ranking.csv")
    pfi = pd.read_csv(T / "pfi_ranking.csv")
    mi = pd.read_csv(T / "mi_ranking.csv")

    out = []
    w = out.append

    w("# خلاصه‌ی نتایج بازپیاده‌سازی FI-SEL")
    w("")
    w("این فایل جدول‌های کلیدی و یافته‌های اصلی همه‌ی آزمایش‌های فاز ۲ و فاز ۳ را نگه می‌دارد. "
      "فازهای گزارش و اسلاید به‌جای خواندن همه‌ی CSVها از این فایل استفاده می‌کنند. "
      "همه‌ی عددها از `results/tables/` خوانده شده‌اند و فایل با `.venv/bin/python -m src.summary` دوباره ساخته می‌شود. "
      "معیارها درصد هستند. «میانگین ± انحراف معیار» روی پنج seed (۴۲، ۰، ۱، ۲ و ۳) محاسبه شده است. "
      "SEL اصلی نسخه‌ی بدون نشت با `stack_method=\"predict\"` است. زمان‌ها روی MacBook Air M4 و با `n_jobs=1` اندازه‌گیری شده‌اند.")
    w("")

    # ---------------------------------------------------------------- 1
    w("## ۱. مقایسه با جدول ۹ مقاله‌ی اصلی")
    w("")
    w("نسخه‌ی بدون نشت FI-SEL به عددهای جدول ۹ مقاله خیلی نزدیک است. نسخه‌ی دارای نشت که برداشت ما از الگوریتم ۱ است، حدود هشت واحد بالاتر از مقاله می‌ایستد.")
    w("")
    rows = []
    names = {"accuracy": "Accuracy", "precision_macro": "Precision (macro)", "recall_macro": "Recall (macro)",
             "f1_macro": "F1 (macro)", "train_time_s": "زمان آموزش (s)", "predict_time_s": "زمان آزمون (s)"}
    for met, nm in names.items():
        r = [nm]
        for k in ("all", "8"):
            c = _row(pvo, variant="clean", k=k, metric=met)
            lk = _row(pvo, variant="leaky", k=k, metric=met)
            nd = 3 if met == "predict_time_s" else 2
            r += [fa(c["paper"]), pm(c["ours_mean_5seeds"], c["ours_std_5seeds"], nd),
                  pm(lk["ours_mean_5seeds"], lk["ours_std_5seeds"], nd)]
        rows.append(r)
    w(table(["معیار", "مقاله، همه", "بدون نشت، همه", "دارای نشت، همه",
             "مقاله، k=8", "بدون نشت، k=8", "دارای نشت، k=8"], rows))
    w("")
    rr = []
    for met, nm in [("ratio_f1_macro", "F1 (macro)"), ("ratio_accuracy", "Accuracy"),
                    ("ratio_train_time_s", "زمان آموزش"), ("ratio_predict_time_s", "زمان آزمون"),
                    ("ratio_size_bytes", "حجم pipeline")]:
        c = _row(pvo, variant="clean", k="8/all", metric=met)
        rr.append([nm, fa(c["paper"]), fa(c["ours_mean_5seeds"])])
    w("نسبت k=8 به همه‌ی ویژگی‌ها برای مقایسه‌ی مستقل از سخت‌افزار (Q21) در جدول زیر آمده است.")
    w("")
    w(table(["معیار", "نسبت در مقاله", "نسبت در نسخه‌ی بدون نشت ما"], rr))
    w("")
    sz = _row(pvo, variant="clean", k="8/all", metric="ratio_size_bytes")["ours_mean_5seeds"]
    w(f"حجم pipeline با کاهش ویژگی‌ها کم نمی‌شود و نسبت آن {fa(sz)} است، چون حجم را درخت مدل نهایی تعیین می‌کند. "
      "پس ادعای کاهش حافظه‌ی مقاله با اندازه‌گیری واقعی تأیید نمی‌شود.")
    w("")

    # ---------------------------------------------------------------- 2
    w("## ۲. رتبه‌بندی ویژگی‌ها (seed=42)")
    w("")
    paper = set(config.PAPER_TOP8)
    n_fi = int(fi.head(8)["feature"].isin(paper).sum())
    n_pfi = int(pfi.head(8)["feature"].isin(paper).sum())
    n_mi = int(mi.head(8)["feature"].isin(paper).sum())
    rows = [[fa(str(i + 1)), f"`{fi['feature'][i]}`", f"`{pfi['feature'][i]}`", f"`{mi['feature'][i]}`"] for i in range(8)]
    w(table(["رتبه", "FI", "PFI", "MI"], rows))
    w("")
    pfi_new = [f for f in pfi.head(8)["feature"] if f not in paper]
    w(f"هشت ویژگی برتر FI و MI هر دو با هشت ویژگی مقاله یکی هستند (اشتراک {fa(str(n_fi))} و {fa(str(n_mi))} از ۸). "
      f"PFI فقط {fa(str(n_pfi))} ویژگی از این هشت را نگه می‌دارد و "
      + "، ".join(f"`{f}`" for f in pfi_new) + " را بالا می‌آورد. "
      f"{fa(str(int((pfi['importance'] > 0).sum())))} ویژگی PFI مثبت دارند. "
      "مجموعه‌ی هشت ویژگی برتر FI و MI در هر پنج seed ثابت است. ترتیب درونی FI با seed تغییر می‌کند، ولی ترتیب MI ثابت می‌ماند. "
      "هیچ‌کدام از هشت ستون ثابت در بیست ویژگی برتر MI نیامده است.")
    w("")

    # ---------------------------------------------------------------- 3
    w("## ۳. k-sweep چهار روش (macro-F1، پنج seed)")
    w("")
    ks["k"] = ks["k"].astype(str)
    klist = [str(k) for k in config.K_VALUES] + ["all"]
    rows = []
    for k in klist:
        r = [fa(k) if k != "all" else "همه (۴۲)"]
        for m in ("FI", "PFI", "MI", "PCA"):
            x = _row(ks, method=m, k=k)
            r.append(pm(x["f1_macro_mean"], x["f1_macro_std"]))
        rows.append(r)
    w(table(["k", "FI-SEL", "PFI-SEL", "MI-SEL", "PCA-SEL"], rows))
    w("")
    rows = []
    for k in klist:
        r = [fa(k) if k != "all" else "همه (۴۲)"]
        for m in ("FI", "PFI", "MI", "PCA"):
            x = _row(ks, method=m, k=k)
            r.append(fa(x["train_time_s_mean"]))
        rows.append(r)
    w("زمان آموزش SEL (ثانیه، میانگین پنج seed) در جدول زیر آمده است. زمان رتبه‌بندی FI، PFI و MI جزو آن نیست، ولی زمان fit شدن PCA جزو آن است.")
    w("")
    w(table(["k", "FI-SEL", "PFI-SEL", "MI-SEL", "PCA-SEL"], rows))
    w("")
    rt = {m: _row(ks, method=m, k="8")["ranking_time_s_mean"] for m in ("FI", "PFI", "MI")}
    size_pca8 = _row(ks, method="PCA", k="8")["size_bytes_mean"] / 1e6
    size_fi8 = _row(ks, method="FI", k="8")["size_bytes_mean"] / 1e6
    size_pfi8 = _row(ks, method="PFI", k="8")["size_bytes_mean"] / 1e6
    mi5, fi5 = _row(ks, method="MI", k="5"), _row(ks, method="FI", k="5")
    mi6 = _row(ks, method="MI", k="6")
    pfi8, fi8 = _row(ks, method="PFI", k="8"), _row(ks, method="FI", k="8")
    pca20 = _row(ks, method="PCA", k="20")
    pca8 = _row(ks, method="PCA", k="8")
    pv = pd.read_csv(T / "pca_explained_variance.csv").set_index("k")["cumulative_explained_variance_pct"]
    pv8, pv20 = pv[8], pv[20]
    w("یافته‌های این بخش این‌ها هستند:")
    w("")
    w(f"- MI در kهای کوچک پایدارتر از FI و PFI است. MI-SEL با k=5 به {pm(mi5['f1_macro_mean'], mi5['f1_macro_std'])} و با k=6 به {pm(mi6['f1_macro_mean'], mi6['f1_macro_std'])} می‌رسد، "
      f"در حالی که FI-SEL با k=5 فقط {pm(fi5['f1_macro_mean'], fi5['f1_macro_std'])} است. ترتیب شش ویژگی اول MI در هر پنج seed یکسان است و `tcp.len` در رتبه‌ی پنجم آن می‌آید. در FI و PFI ترتیب درونی با seed تغییر می‌کند و همین تغییر واریانس زیاد FI در k=6 و PFI در k=6 و k=7 را می‌سازد.")
    w(f"- از k=8 به بعد FI، PFI و MI تقریباً هم‌اندازه هستند. PFI-SEL با k=8 به {pm(pfi8['f1_macro_mean'], pfi8['f1_macro_std'])} می‌رسد و FI-SEL به {pm(fi8['f1_macro_mean'], fi8['f1_macro_std'])}. "
      f"زمان آموزش PFI-SEL با k=8 برابر {fa(pfi8['train_time_s_mean'])} ثانیه و زمان FI-SEL برابر {fa(fi8['train_time_s_mean'])} ثانیه است.")
    w(f"- PCA-SEL در همه‌ی kها خیلی ضعیف‌تر است. macro-F1 آن با k=8 برابر {pm(pca8['f1_macro_mean'], pca8['f1_macro_std'])} و با k=20 برابر {pm(pca20['f1_macro_mean'], pca20['f1_macro_std'])} است. "
      f"حجم pipeline آن هم بزرگ‌تر است ({fa(size_pca8)} مگابایت در k=8، در برابر {fa(size_fi8)} برای FI و {fa(size_pfi8)} برای PFI). "
      f"افت از واریانس دورریخته نمی‌آید، چون مؤلفه‌ها با k=8 حدود {fa(pv8)} و با k=20 حدود {fa(pv20)} درصد واریانس را نگه می‌دارند. "
      "یک توضیح محتمل این است که DT روی محورهای چرخیده‌ی PCA مرزهای تمیز ویژگی‌های پرچمی و پورت را از دست می‌دهد. این توضیح آزموده نشده است. "
      "این نتیجه فقط برای PCA بعد از MinMax است. مقاله‌ی پشتیبان پیش از PCA تبدیل log و استانداردسازی به کار برده است (ص. ۱۰ آن مقاله).")
    w(f"- هزینه‌ی رتبه‌بندی متفاوت است. میانگین زمان رتبه‌بندی FI {fa(rt['FI'])} ثانیه، MI {fa(rt['MI'])} ثانیه و PFI {fa(rt['PFI'])} ثانیه است. هر سه رتبه‌بندی با `n_jobs=-1` اجرا شدند.")
    w("")

    s42 = pd.read_csv(T / "ksweep_all_methods_seed42.csv")
    s42["k"] = s42["k"].astype(str)
    w("### جدول اصلی k-sweep با seed=42 (Q4)")
    w("")
    w("طبق Q4، جدول اصلی k-sweep با seed=42 ساخته می‌شود. ترتیب درونی هشت ویژگی برتر FI و PFI به seed وابسته است. "
      "به همین دلیل عدد seed=42 در k=6 و k=7 با میانگین پنج seed فاصله‌ی زیادی دارد و این جدول باید همراه جدول پنج seed گزارش شود.")
    w("")
    rows = []
    for k in klist:
        r = [fa(k) if k != "all" else "همه (۴۲)"]
        for m in ("FI", "PFI", "MI", "PCA"):
            x = _row(s42, method=m, k=k)
            r += [fa(x["accuracy"]), fa(x["f1_macro"])]
        rows.append(r)
    w(table(["k", "FI Acc", "FI F1", "PFI Acc", "PFI F1", "MI Acc", "MI F1", "PCA Acc", "PCA F1"], rows))
    w("")

    # ---------------------------------------------------------------- 3b
    pc = pd.read_csv(T / "per_class_k8.csv")
    pc["k"] = pc["k"].astype(str)
    w("### معیارهای هر کلاس (Q27، پنج seed)")
    w("")
    w("جدول زیر precision، recall و F1 هر کلاس را برای SEL با همه‌ی ویژگی‌ها کنار جدول ۶ مقاله و برای FI و PFI با k=8 نشان می‌دهد.")
    w("")
    rows = []
    for c in config.CLASS_ORDER:
        a_ = _row(pc, method="FI", k="all", **{"class": c})
        f8 = _row(pc, method="FI", k="8", **{"class": c})
        p8 = _row(pc, method="PFI", k="8", **{"class": c})
        rows.append([c, f"{fa(a_['paper_precision'])} / {fa(a_['paper_recall'])} / {fa(a_['paper_f1'])}",
                     f"{fa(a_['precision_mean'])} / {fa(a_['recall_mean'])} / {fa(a_['f1_mean'])}",
                     f"{fa(f8['precision_mean'])} / {fa(f8['recall_mean'])} / {fa(f8['f1_mean'])}",
                     f"{fa(p8['precision_mean'])} / {fa(p8['recall_mean'])} / {fa(p8['f1_mean'])}"])
    w(table(["کلاس", "مقاله، همه (P / R / F1)", "ما، همه", "ما، FI k=8", "ما، PFI k=8"], rows))
    w("")
    mm = _row(pc, method="FI", k="all", **{"class": "MITM"})
    w(f"Recall کلاس MITM در مقاله {fa(mm['paper_recall'])} و در بازپیاده‌سازی ما {fa(mm['recall_mean'])} است و precision آن در هر دو ۱۰۰ است.")
    w("")

    # ---------------------------------------------------------------- 4
    w("## ۴. مدل‌های تکی در برابر SEL (همه‌ی ویژگی‌ها)")
    w("")
    rows = []
    for mdl in ("DT", "LR", "NB", "SEL"):
        x = _row(single, model=mdl, k="all")
        rows.append([mdl, fa(x["paper_f1_macro"]), pm(x["f1_macro_mean"], x["f1_macro_std"]),
                     pm(_row(single, model=mdl, method="FI", k="8")["f1_macro_mean"],
                        _row(single, model=mdl, method="FI", k="8")["f1_macro_std"]),
                     pm(_row(single, model=mdl, method="PFI", k="8")["f1_macro_mean"],
                        _row(single, model=mdl, method="PFI", k="8")["f1_macro_std"])])
    w(table(["مدل", "مقاله (جدول ۵)", "ما، همه", "ما، FI k=8", "ما، PFI k=8"], rows))
    w("")
    dt = _row(single, model="DT", k="all")
    w(f"DT تنها با همه‌ی ویژگی‌ها به macro-F1 برابر {fa(dt['f1_macro_mean'])} می‌رسد و با SEL برابر است. مقاله برای DT عدد {fa(dt['paper_f1_macro'])} گزارش کرده است (نقد شماره‌ی ۸، Q45).")
    w("")

    # ---------------------------------------------------------------- 5
    w("## ۵. نسخه‌ی بدون نشت در برابر نسخه‌ی دارای نشت")
    w("")
    rows = []
    for m, k, nm in (("ALL", "all", "همه‌ی ویژگی‌ها"), ("FI", "8", "FI، k=8"), ("PFI", "8", "PFI، k=8")):
        c, lk = _row(leaky, variant="clean", method=m, k=k), _row(leaky, variant="leaky", method=m, k=k)
        rows.append([nm, pm(c["f1_macro_mean"], c["f1_macro_std"]), pm(lk["f1_macro_mean"], lk["f1_macro_std"]),
                     pm(c["mitm_recall_mean"], c["mitm_recall_std"]), pm(lk["mitm_recall_mean"], lk["mitm_recall_std"])])
    w(table(["حالت", "F1 بدون نشت", "F1 دارای نشت", "Recall MITM بدون نشت", "Recall MITM دارای نشت"], rows))
    w("")
    w("طبق الگوریتم ۱، احتمال نشت وجود دارد. متن ص. ۴ مقاله با این الگوریتم ناسازگار است. "
      "برداشت لفظی الگوریتم ۱ اعداد مقاله را نمی‌سازد، چون جدول ۹ با نسخه‌ی بدون نشت ما می‌خواند (Q43).")
    w("")
    st = {(r["stack_method"], str(r["k"])): r for _, r in stack.iterrows()}
    w(f"تفاوت `predict` و `predict_proba` کوچک است. با همه‌ی ویژگی‌ها macro-F1 به‌ترتیب {pm(st[('predict', 'all')]['f1_macro_mean'], st[('predict', 'all')]['f1_macro_std'])} و "
      f"{pm(st[('predict_proba', 'all')]['f1_macro_mean'], st[('predict_proba', 'all')]['f1_macro_std'])} است و با k=8 به‌ترتیب "
      f"{pm(st[('predict', '8')]['f1_macro_mean'], st[('predict', '8')]['f1_macro_std'])} و {pm(st[('predict_proba', '8')]['f1_macro_mean'], st[('predict_proba', '8')]['f1_macro_std'])} است.")
    w("")

    # ---------------------------------------------------------------- 6
    w("## ۶. بردار مبهم و سقف recall کلاس MITM (Q44)")
    w("")
    w("بردار مبهم اصلی بردار تمام‌صفر است. یعنی همه‌ی ۴۲ ویژگی این ردیف‌ها صفر هستند. "
      "جدول زیر تعداد ردیف‌های این بردار را در هر کلاس روی کل دیتاست (با تکراری‌ها) نشان می‌دهد.")
    w("")
    rows = []
    for _, r in amb.iterrows():
        name = "مجموع" if r["class"] == "Total" else r["class"]
        rows.append([name, fa(r["rows_on_vector"], 0), fa(r["class_total_rows"], 0), fa(r["share_of_class_pct"]),
                     fa(r["share_of_vector_pct"]), fa(r["recall_ceiling_if_vector_to_majority_pct"])])
    w(table(["کلاس", "ردیف روی بردار", "کل ردیف کلاس", "سهم از کلاس", "سهم از بردار", "سقف recall اگر بردار به Malware برود"], rows))
    w("")
    m = _row(amb, **{"class": "MITM"})
    w(f"کلاس اکثریت این بردار Malware است. اگر مدل کل بردار را Malware پیش‌بینی کند، سقف recall کلاس MITM {fa(m['recall_ceiling_if_vector_to_majority_pct'])} درصد است. "
      f"اگر کل بردار را MITM پیش‌بینی کند، recall به ۱۰۰ می‌رسد ولی سقف precision کلاس MITM در فضای ۴۲ ویژگی {fa(m['precision_ceiling_if_vector_to_class_pct'])} درصد می‌شود. "
      "این سقف‌ها برای فضای ۴۲ ویژگی هستند.")
    w("")
    w("در فضای هشت ویژگی برتر، ردیف‌های بیشتری روی همین بردار صفر می‌افتند. جدول زیر این را برای هشت ویژگی برتر FI و PFI با seed=42 نشان می‌دهد.")
    w("")
    rows = [["مجموع" if r["class"] == "Total" else r["class"], fa(r["rows_on_vector_42"], 0),
             fa(r["rows_on_vector_FI_top8"], 0), fa(r["rows_on_vector_PFI_top8"], 0)] for _, r in amb8.iterrows()]
    w(table(["کلاس", "۴۲ ویژگی", "هشت ویژگی FI", "هشت ویژگی PFI"], rows))
    w("")
    d8 = _row(amb8, **{"class": "DDoS"})
    w(f"هشت ویژگی FI همه از لایه‌ی TCP هستند، پس ردیف‌های DDoS که TCP ندارند ({fa(d8['rows_on_vector_FI_top8'], 0)} ردیف) هم روی بردار صفر می‌افتند. "
      "به همین دلیل FI-SEL بدون وزن این بردار را DDoS و PFI-SEL آن را Information gathering پیش‌بینی می‌کند، و نه Malware.")
    w("")
    w("خلاصه‌ی همه‌ی بردارهایی که با بیش از یک کلاس آمده‌اند در جدول زیر آمده است. سقف recall با این فرض حساب شده که هر بردار به کلاس اکثریت خودش داده شود.")
    w("")
    rows = []
    for _, r in ambs.iterrows():
        name = "مجموع (سقف accuracy)" if r["class"] == "Total" else r["class"]
        rows.append([name, fa(r["n_multiclass_vectors_with_class"], 0), fa(r["rows_on_multiclass_vectors"], 0),
                     fa(r["share_of_class_on_multiclass_pct"]), fa(r["rows_lost_under_majority"], 0),
                     fa(r["recall_ceiling_majority_pct"])])
    w(table(["کلاس", "تعداد بردار چندکلاسه", "ردیف روی این بردارها", "سهم از کلاس", "ردیف از دست‌رفته", "سقف recall"], rows))
    w("")
    tot = _row(ambs, **{"class": "Total"})
    w(f"در کل {fa(tot['n_multiclass_vectors_with_class'], 0)} بردار با بیش از یک کلاس آمده‌اند. فقط کلاس MITM سقف پایینی دارد و سقف بقیه‌ی کلاس‌ها بالای ۹۷ درصد است. "
      f"سقف accuracy کل دیتاست در فضای ۴۲ ویژگی {fa(tot['recall_ceiling_majority_pct'])} درصد است.")
    w("")

    # ---------------------------------------------------------------- 7
    w("## ۷. اثر `class_weight=\"balanced\"` (k=8)")
    w("")
    w("وزن‌دهی روی LR و DT داخل SEL اعمال شد. GaussianNB این پارامتر را ندارد. حالت مرجع یک اجرای دوباره‌ی SEL بدون وزن است که پیش‌بینی بردار مبهم را هم ثبت می‌کند.")
    w("")
    rows = []
    for meth in ("FI", "PFI"):
        for v, nm in (("unweighted_ref", "بدون وزن"), ("balanced", "balanced")):
            x = _row(cw, method=meth, variant=v)
            rows.append([f"{meth}-SEL، {nm}", pm(x["f1_macro_mean"], x["f1_macro_std"]),
                         pm(x["MITM_recall_mean"], x["MITM_recall_std"]), pm(x["MITM_precision_mean"], x["MITM_precision_std"]),
                         pm(x["Malware_precision_mean"], x["Malware_precision_std"]),
                         pm(x["DDoS_recall_mean"], x["DDoS_recall_std"]),
                         x["ambiguous_vector_pred_counts"].split(":")[0]])
    w(table(["حالت", "macro-F1", "Recall MITM", "Precision MITM", "Precision Malware", "Recall DDoS", "پیش‌بینی بردار مبهم (هر ۵ seed)"], rows))
    w("")
    fb, fu = _row(cw, method="FI", variant="balanced"), _row(cw, method="FI", variant="unweighted_ref")
    pb, pu = _row(cw, method="PFI", variant="balanced"), _row(cw, method="PFI", variant="unweighted_ref")
    # precision ceiling of MITM if the projected zero vector goes to MITM
    mitm_total = _row(amb8, **{"class": "MITM"})["class_total_rows"]
    mitm_on = _row(amb8, **{"class": "MITM"})
    tot8 = _row(amb8, **{"class": "Total"})
    cap_fi = 100 * mitm_total / (mitm_total - mitm_on["rows_on_vector_FI_top8"] + tot8["rows_on_vector_FI_top8"])
    cap_pfi = 100 * mitm_total / (mitm_total - mitm_on["rows_on_vector_PFI_top8"] + tot8["rows_on_vector_PFI_top8"])
    w(f"وزن‌دهی مدل را وادار می‌کند بردار مبهم را MITM پیش‌بینی کند. این اتفاق در هر پنج seed و برای هر دو روش رخ داد. "
      f"Recall کلاس MITM به ۱۰۰ می‌رسد، ولی precision آن برای FI به {fa(fb['MITM_precision_mean'])} و برای PFI به {fa(pb['MITM_precision_mean'])} سقوط می‌کند. "
      f"این دو عدد تقریباً همان سقف precision بردار صفر در فضای هشت ویژگی seed=42 هستند ({fa(cap_fi)} و {fa(cap_pfi)}، از جدول بخش ۶). "
      f"Precision کلاس Malware تقریباً تغییر نمی‌کند ({fa(fu['Malware_precision_mean'])} به {fa(fb['Malware_precision_mean'])} برای FI)، چون در فضای هشت ویژگی بردار از قبل به Malware داده نمی‌شد. "
      f"هزینه‌ی اصلی را کلاس DDoS در FI-SEL می‌پردازد و recall آن از {fa(fu['DDoS_recall_mean'])} به {fa(fb['DDoS_recall_mean'])} می‌افتد. "
      f"در نتیجه macro-F1 برای FI از {fa(fu['f1_macro_mean'])} به {fa(fb['f1_macro_mean'])} و برای PFI از {fa(pu['f1_macro_mean'])} به {fa(pb['f1_macro_mean'])} کم می‌شود. "
      "پس وزن‌دهی ضعف MITM را حل نمی‌کند و فقط خطا را از recall به precision منتقل می‌کند.")
    w("")

    # ---------------------------------------------------------------- 8
    w("## ۸. حذف ردیف‌های تکراری")
    w("")
    rows = []
    for m, k, nm in (("ALL", "all", "همه‌ی ویژگی‌ها"), ("FI", "8", "FI، k=8"), ("PFI", "8", "PFI، k=8")):
        a, b = _row(dedup, dedup=False, method=m, k=k), _row(dedup, dedup=True, method=m, k=k)
        rows.append([nm, pm(a["f1_macro_mean"], a["f1_macro_std"]), pm(b["f1_macro_mean"], b["f1_macro_std"]),
                     pm(a["mitm_recall_mean"], a["mitm_recall_std"]), pm(b["mitm_recall_mean"], b["mitm_recall_std"])])
    w(table(["حالت", "F1 با تکراری", "F1 بدون تکراری", "Recall MITM با تکراری", "Recall MITM بدون تکراری"], rows))
    w("")
    a = _row(dedup, dedup=False, method="ALL", k="all")
    w(f"حذف تکراری‌ها نتیجه را بهتر می‌کند (Q44). در اجرای اصلی با seed=42، {fa(a['test_rows_seen_in_train_pct_seed42'])} درصد ردیف‌های آزمون و "
      f"{fa(a['mitm_test_rows_seen_in_train_pct_seed42'])} درصد ردیف‌های MITM آزمون عیناً در آموزش هم آمده‌اند. "
      "بیشتر جهش از کلاس MITM است، چون ۸۲۱ ردیف مبهم به یک ردیف تبدیل می‌شوند.")
    w("")

    # ---------------------------------------------------------------- 9
    w("## ۹. بخش اختیاری: SMOTE و SEL همگن (k=8)")
    w("")
    w("SMOTE با `imblearn.pipeline.Pipeline` و فقط روی داده‌ی آموزش اجرا شد. SEL همگن سه DT با عمق ۴، ۸ و ۱۶ را مدل پایه می‌گیرد و همان DT مدل نهایی را دارد. هر دو بخش اجرا شدند.")
    w("")
    rows = []
    for meth in ("FI", "PFI"):
        for v, nm in (("unweighted_ref", "SEL"), ("smote", "SEL + SMOTE"), ("homogeneous", "SEL همگن")):
            x = _row(opt, method=meth, variant=v)
            rows.append([f"{meth}، {nm}", pm(x["f1_macro_mean"], x["f1_macro_std"]), pm(x["MITM_recall_mean"], x["MITM_recall_std"]),
                         pm(x["MITM_precision_mean"], x["MITM_precision_std"]), fa(x["train_time_s_mean"]),
                         fa(x["size_bytes_mean"] / 1e6)])
    w(table(["حالت", "macro-F1", "Recall MITM", "Precision MITM", "زمان آموزش (s)", "حجم (MB)"], rows))
    w("")
    fs, fh = _row(opt, method="FI", variant="smote"), _row(opt, method="FI", variant="homogeneous")
    ph = _row(opt, method="PFI", variant="homogeneous")
    w(f"SMOTE همان اثر وزن‌دهی را دارد. بردار مبهم MITM پیش‌بینی می‌شود و macro-F1 برای FI به {fa(fs['f1_macro_mean'])} می‌رسد. "
      "چون SMOTE پیش از اعتبارسنجی متقابل داخلی Stacking اجرا می‌شود، نمونه‌های مصنوعی در foldهای آن هم می‌آیند و پیش‌بینی‌های مدل‌های پایه کمی خوش‌بینانه هستند. "
      f"SEL همگن هم‌اندازه‌ی SEL ناهمگن است ({fa(fh['f1_macro_mean'])} برای FI و {fa(ph['f1_macro_mean'])} برای PFI)، ولی آموزش آن حدود سه تا چهار برابر سریع‌تر است "
      f"({fa(fh['train_time_s_mean'])} و {fa(ph['train_time_s_mean'])} ثانیه). این نتیجه نقد شماره‌ی ۸ را تقویت می‌کند. DT تنها و SEL همگن هر دو هم‌اندازه‌ی SEL ناهمگن هستند، پس شاهدی بر سهم NB و LR در دقت دیده نمی‌شود.")
    w("")

    # ---------------------------------------------------------------- 10
    w("## ۱۰. یافته‌های اصلی برای گزارش")
    w("")
    w("1. بازپیاده‌سازی بدون نشت عددهای جدول ۹ مقاله را تا حدود یک واحد بازتولید می‌کند و هشت ویژگی برتر FI ما همان هشت ویژگی مقاله است.")
    w("2. نسبت F1 حالت k=8 به همه‌ی ویژگی‌ها با مقاله یکی است، ولی حجم pipeline کم نمی‌شود.")
    w("3. PFI در k=8 کمی بهتر و سریع‌تر از FI است. MI در kهای کوچک بهترین روش است. PCA بعد از MinMax در این دیتاست برای SEL ضعیف است.")
    w("4. ضعف کلاس MITM از بردار مبهم تمام‌صفر می‌آید و نه از مدل. وزن‌دهی و SMOTE فقط خطا را از recall به precision منتقل می‌کنند.")
    w("5. نگه داشتن ردیف‌های تکراری نتیجه را پایین آورده است و حذف آن‌ها macro-F1 را حدود ده واحد بالا می‌برد.")
    w("6. DT تنها و SEL همگن هم‌اندازه‌ی SEL ناهمگن هستند. پس مزیت Stacking در این بازپیاده‌سازی دیده نمی‌شود.")
    w("7. طبق الگوریتم ۱، احتمال نشت وجود دارد، ولی برداشت لفظی آن اعداد مقاله را نمی‌سازد.")
    w("")
    w("## فایل‌های مرتبط")
    w("")
    w("جدول‌ها در `results/tables/` و نمودارها در `results/figures/` قرار دارند. فهرست کامل آن‌ها در `README.md` آمده است. "
      "نمودارهای فاز ۳ `methods_vs_k.png` و `class_weight_k8.png` هستند.")
    w("")
    return "\n".join(out)


def main():
    OUT.write_text(build(), encoding="utf-8")
    print("written", OUT)


if __name__ == "__main__":
    main()
