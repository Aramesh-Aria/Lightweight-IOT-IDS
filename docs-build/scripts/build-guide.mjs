// Builds the question-based study guide.
//   node scripts/build-guide.mjs          -> deliverables/study-guide.pdf
//   node scripts/build-guide.mjs --png    -> also writes one PNG per page to build/guide-png/ for review
// Source: guide/guide.md. Checks: 30-40 questions, 3-6 sentences per answer, 8-12 pages, numbers found in
// the report sources, results/SUMMARY.md or reference-facts.md, the internal question reference, TOC pages stable across passes.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import puppeteer from 'puppeteer-core';
import { cleanPdfMetadata, destinationPages } from './build-pdf.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const guideDir = path.join(root, 'guide');
const buildDir = path.join(root, 'build');
const outDir = path.resolve(root, '..', 'deliverables');
const CHROME = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const Q_RANGE = [30, 40];
const SENT_RANGE = [3, 6];
const PAGE_RANGE = [8, 12];
const wantPng = process.argv.includes('--png');

const cfg = JSON.parse(fs.readFileSync(path.join(root, 'config', 'report.json'), 'utf8'));
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const FA = '۰۱۲۳۴۵۶۷۸۹';
const fa = (s) => String(s).replace(/[0-9]/g, (d) => FA[d]);
const two = (n) => String(n).padStart(2, '0');
const toLatin = (s) => s.replace(/[۰-۹]/g, (d) => String(FA.indexOf(d))).replace(/٫/g, '.').replace(/٬/g, '');

// ---------- parse ----------
function parse(src) {
  const chapters = [];
  let ch = null, sec = null, qa = null, block = null;
  const flushPara = (buf) => {
    const text = buf.join(' ').trim();
    if (!text) return;
    if (qa) { if (qa.answer) throw new Error(`question "${qa.q}" has more than one paragraph`); qa.answer = text; }
    else if (sec) throw new Error(`text outside a question in section "${sec.title}"`);
    else ch.intro.push(text);
  };
  let buf = [];
  for (const raw of src.split('\n')) {
    const line = raw.trimEnd();
    if (block) {
      if (line === ':::') { pushBlock(block); block = null; continue; }
      if (line.trim()) block.lines.push(line);
      continue;
    }
    if (line.startsWith('::: ')) { flushPara(buf); buf = []; block = { kind: line.slice(4).trim(), lines: [] }; continue; }
    let m;
    if ((m = /^# (\d+) \| (.+?) \| (.+)$/.exec(line))) {
      flushPara(buf); buf = [];
      ch = { num: Number(m[1]), title: m[2], lat: m[3], intro: [], items: [], secs: [] };
      chapters.push(ch); sec = null; qa = null; continue;
    }
    if ((m = /^## (.+?) \| (.+?)(?: \| (warn))?$/.exec(line))) {
      flushPara(buf); buf = [];
      sec = { title: m[1], lat: m[2], warn: !!m[3], qas: [], num: ch.secs.length + 1 };
      ch.secs.push(sec); ch.items.push({ type: 'sec', sec }); qa = null; continue;
    }
    if ((m = /^### (.+)$/.exec(line))) {
      flushPara(buf); buf = [];
      qa = { q: m[1].trim(), answer: '', warn: sec.warn };
      sec.qas.push(qa); ch.items.push({ type: 'qa', qa, sec }); continue;
    }
    if (!line.trim()) { flushPara(buf); buf = []; continue; }
    buf.push(line.trim());
  }
  flushPara(buf);
  function pushBlock(b) {
    // Blocks attach to the chapter flow at the current position.
    ch.items.push({ type: 'block', block: b, afterSec: !!sec });
    if (b.kind === 'summary') { qa = null; sec = null; }
  }
  return chapters;
}

// ---------- inline ----------
// A Persian comma between two Latin words joins them into one LTR run; an RLM after the comma breaks it.
function fixLatinLists(html) {
  return html.split(/(<span class="en">[^<]*<\/span>|<code>[^<]*<\/code>)/).map((part, i) => (i % 2
    ? part
    : part.replace(/(^|[A-Za-z0-9²)>])، (?=[A-Za-z<])/g, '$1،‏ '))).join('');
}
function inline(s) {
  const codes = [];
  let t = s.replace(/`([^`]+)`/g, (m, c) => { codes.push(c); return `\u0000${codes.length - 1}\u0000`; });
  t = esc(t)
    .replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')
    // English gloss in parentheses after a Persian term: gray, as in the reference.
    .replace(/\(([A-Za-z][A-Za-z0-9 \-–،,·.]*)\)/g, '<span class="en">($1)</span>')
    .replace(/(?<![\w.-])([A-Za-z]+(?:-[A-Za-z0-9]+)+)(?![\w])/g, '<span class="nw">$1</span>');
  t = fixLatinLists(t);
  return t.replace(/\u0000(\d+)\u0000/g, (m, i) => `<code>${esc(codes[Number(i)])}</code>`);
}

// ---------- checks ----------
function sentences(text) {
  const t = text.replace(/`[^`]*`/g, 'X').replace(/ص\. /g, 'ص ').replace(/\d\.\d/g, '0');
  return (t.match(/[.؟!](?=\s|$)/g) || []).length;
}
function knownNumbers() {
  const files = fs.readdirSync(path.join(root, 'report')).filter((f) => f.endsWith('.md')).map((f) => path.join(root, 'report', f));
  files.push(path.resolve(root, '..', 'ids-fisel-pfi', 'results', 'SUMMARY.md'), path.resolve(root, '..', 'reference-facts.md'));
  const text = files.map((f) => fs.readFileSync(f, 'utf8')).join('\n') + JSON.stringify(cfg);
  return new Set(toLatin(text).match(/\d+(?:\.\d+)?/g) || []);
}
function checkNumbers(label, text, known, warnings) {
  const nums = toLatin(text.replace(/`[^`]*`/g, '')).match(/\d+(?:\.\d+)?/g) || [];
  const bad = [...new Set(nums.filter((x) => (x.includes('.') || Number(x) > 20) && !known.has(x)))];
  if (bad.length) warnings.push(`${label}: numbers not in report sources or SUMMARY.md: ${bad.join(', ')}`);
}

// ---------- render ----------
function topFeatures() {
  const csv = fs.readFileSync(path.resolve(root, cfg.featureSource), 'utf8').trim().split('\n');
  const cols = csv[0].split(',');
  const fi = cols.indexOf('feature'), ii = cols.indexOf('importance');
  return csv.slice(1, 9).map((l) => { const c = l.split(','); return { name: c[fi], imp: Number(c[ii]) }; });
}
function coverArt(feats) {
  // Same line art as the report cover and title slide: FI ranking bars feeding a two-level stacking diagram.
  const max = feats[0].imp;
  const bars = feats.map((f, i) => {
    const y = 18 + i * 21;
    const w = Math.round((f.imp / max) * 230);
    return `<g><text x="0" y="${y + 10}" class="ca-mono">${f.name}</text><rect x="110" y="${y}" width="${w}" height="12" rx="2" class="ca-bar${i < 3 ? ' hi' : ''}"/><text x="${116 + w}" y="${y + 10}" class="ca-val">${f.imp.toFixed(3)}</text></g>`;
  }).join('');
  return `<svg class="cv-art" viewBox="0 0 640 200" xmlns="http://www.w3.org/2000/svg">
  <g>${bars}</g>
  <g transform="translate(400,10)">
    <path d="M0 60 C 40 60, 40 30, 80 30 M0 110 C 40 110, 40 150, 80 150" class="ca-link"/>
    <path d="M0 85 C 60 85, 120 95, 170 95" class="ca-link dashed"/>
    <rect x="80" y="12" width="70" height="36" rx="6" class="ca-box"/><text x="115" y="35" class="ca-lbl">NB</text>
    <rect x="80" y="132" width="70" height="36" rx="6" class="ca-box"/><text x="115" y="155" class="ca-lbl">LR</text>
    <path d="M150 30 C 175 30, 175 80, 190 80 M150 150 C 175 150, 175 110, 190 110" class="ca-link"/>
    <rect x="190" y="68" width="50" height="54" rx="8" class="ca-box meta"/><text x="215" y="92" class="ca-lbl meta">DT</text><text x="215" y="108" class="ca-sub">meta</text>
    <circle cx="0" cy="85" r="4" class="ca-dot"/>
  </g>
</svg>`;
}

const pgSlot = (id) => `<span class="pg" data-target="${id}">۰۰</span>`;
const secNum = (ch, sec) => `${fa(ch.num)}٫${fa(sec.num)}`;

function renderCover(chapters, nq) {
  const feats = topFeatures();
  const fb = feats.map((f, i) => `<div class="fb-row"><span class="fb-i">${two(i + 1)}</span><span class="fb-n">${esc(f.name)}</span><span class="fb-v">${f.imp.toFixed(4)}</span></div>`).join('');
  return `<section class="cover">
  <div class="cv-top"><div></div><div class="cv-kw">${cfg.keywordsColumn.map((k) => `<div>${esc(k)}</div>`).join('')}</div></div>
  <div class="cv-label"><span class="a">${esc(cfg.latinTitle)}</span><span class="b">STUDY GUIDE</span></div>
  <h1 class="cv-title">راهنمای مطالعه</h1>
  <div class="cv-title2">${esc(cfg.titleLines.join(" "))}</div>
  <div class="cv-sub">${inline(cfg.subtitle)}</div>
  <div class="cv-rule"></div>
  <div class="cv-desc">${fa(nq)} پرسش و پاسخ کوتاه در ${fa(chapters.length)} فصل برای آمادگی جلسه‌ی پرسش و پاسخ ارائه، از مفاهیم پایه تا نتایج بازپیاده‌سازی و نقدهای مقاله‌ی اصلی.</div>
  ${coverArt(feats)}
  <div class="cv-bottom">
    <div class="people">
      <div><span class="role">دانشجو</span><span class="name">${esc(cfg.author)}</span></div>
      <div><span class="role">استاد</span><span class="name">${esc(cfg.supervisor)}</span></div>
      <div class="inst">${esc(cfg.university)} · ${esc(cfg.semester)}</div>
    </div>
    <div class="feat-block"><div class="fb-head">TOP-8 FI FEATURES · SEED 42</div>${fb}</div>
  </div>
</section>`;
}

function renderToc(chapters) {
  const rows = chapters.map((ch) => {
    const secs = ch.secs.map((s) => {
      const first = s.qas[0].n, last = s.qas[s.qas.length - 1].n;
      return `<a class="toc-sec" href="#${s.id}"><span class="ts-num">${secNum(ch, s)}</span><span class="ts-title">${inline(s.title)}</span><span class="ts-q">پرسش ${fa(first)}–${fa(last)}</span>${pgSlot(s.id)}</a>`;
    }).join('');
    return `<div class="toc-ch"><a class="toc-main" href="#${ch.id}"><span class="tc-num">${fa(two(ch.num))}</span><span class="tc-titles"><span class="tc-title">${inline(ch.title)}</span><span class="tc-lat">${esc(ch.lat)}</span></span><span class="leader"></span>${pgSlot(ch.id)}</a><div class="toc-secs">${secs}</div></div>`;
  }).join('\n');
  return `<section class="toc">
  <div class="toc-head"><h1>فهرست</h1><span class="toc-lat">CONTENTS</span></div>
  ${rows}
  <p class="toc-note">هر پاسخ سه تا شش جمله دارد و برای گفتن در حدود یک دقیقه نوشته شده است. «ص.» در فصل‌های ۲ و ۳ به صفحه‌ی مقاله‌ی همان فصل و در فصل‌های ۱ و ۴ به صفحه‌ی مقاله‌ی اصلی اشاره می‌کند، مگر اینکه نام مقاله‌ی دیگری آمده باشد. پرسش‌های نارنجی نقدها و پرسش‌های چالشی هستند.</p>
  <div class="legend"><span class="g"><i></i>مفهوم کلیدی و مسیر درست</span><span class="o"><i></i>نقد، نشت و هشدار</span><span class="n"><i></i>ساختار و داده</span></div>
</section>`;
}

function renderBlock(b) {
  if (b.kind === 'cards') {
    const cards = b.lines.map((l) => {
      const o = l.startsWith('! ');
      const [lab, title, text] = (o ? l.slice(2) : l).split(' | ');
      return `<div class="card${o ? ' o' : ''}"><div class="cl">${esc(lab)}</div><div class="ct">${inline(title)}</div><div class="cx">${inline(text)}</div></div>`;
    }).join('');
    return `<div class="cards">${cards}</div>`;
  }
  if (b.kind === 'summary') {
    if (b.lines.length !== 3) throw new Error('summary box needs exactly three items');
    const items = b.lines.map((l, i) => {
      const [lab, text] = l.split(' | ');
      return `<div class="sm-item"><div class="sm-n">${fa(i + 1)}</div><div><div class="sm-l">${esc(lab)}</div><div class="sm-t">${inline(text)}</div></div></div>`;
    }).join('');
    return `<div class="summary"><div class="sm-head"><h4>جمع‌بندی برای ارائه</h4><span>SUMMARY FOR THE PRESENTATION</span></div>${items}</div>`;
  }
  if (b.kind === 'table') {
    const rows = b.lines.filter((l) => !/^\|[-| ]+\|$/.test(l)).map((l) => l.replace(/^\||\|$/g, '').split('|').map((c) => c.trim()));
    const [head, ...body] = rows;
    const last = head.length - 1;
    const th = head.map((h, i) => `<th${i === last ? ' class="w"' : ''}>${inline(h)}</th>`).join('');
    const tb = body.map((r) => `<tr>${r.map((c, i) => `<td class="${i === 0 ? 'first' : i === last ? 'w' : 'num'}">${inline(c)}</td>`).join('')}</tr>`).join('');
    return `<table><thead><tr>${th}</tr></thead><tbody>${tb}</tbody></table>`;
  }
  throw new Error(`unknown block ${b.kind}`);
}

function renderChapter(ch) {
  const out = [];
  out.push(`<section class="chapter"><header class="ch-head"><div class="ch-num">${fa(two(ch.num))}</div><div class="ch-titles"><h1 id="${ch.id}">${inline(ch.title)}</h1><div class="ch-lat">${esc(ch.lat)}</div></div></header><div class="zigzag"></div>`);
  ch.intro.forEach((p) => out.push(`<p class="intro">${inline(p)}</p>`));
  for (const it of ch.items) {
    if (it.type === 'sec') out.push(`<h2 id="${it.sec.id}"><span class="sec-num">${secNum(ch, it.sec)}</span>${inline(it.sec.title)}</h2><div class="sec-lat">${esc(it.sec.lat)}</div>`);
    else if (it.type === 'qa') out.push(`<div class="qa${it.qa.warn ? ' warn' : ''}" id="q${it.qa.n}"><h3><span class="dia"></span><span class="qt">${inline(it.qa.q)}</span><span class="qn">Q${two(it.qa.n)}</span></h3><p>${inline(it.qa.answer)}</p></div>`);
    else out.push(renderBlock(it.block));
  }
  out.push('</section>');
  return out.join('\n');
}

function renderHtml(chapters, nq) {
  return `<!DOCTYPE html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8"><title>راهنمای مطالعه · ${esc(cfg.title)}</title>
<link rel="stylesheet" href="../guide/guide.css"></head>
<body>
${renderCover(chapters, nq)}
${renderToc(chapters)}
${chapters.map(renderChapter).join('\n')}
</body></html>`;
}

async function printPdf(browser, htmlPath) {
  const page = await browser.newPage();
  await page.goto('file://' + htmlPath, { waitUntil: 'networkidle0' });
  await page.evaluate(async () => { await document.fonts.ready; });
  const bytes = await page.pdf({ preferCSSPageSize: true, printBackground: true, displayHeaderFooter: false, outline: false, tagged: false });
  await page.close();
  return Buffer.from(bytes);
}

async function main() {
  const chapters = parse(fs.readFileSync(path.join(guideDir, 'guide.md'), 'utf8'));
  let n = 0;
  chapters.forEach((ch) => {
    ch.id = `ch${ch.num}`;
    ch.secs.forEach((s) => { s.id = `ch${ch.num}-s${s.num}`; s.qas.forEach((q) => { q.n = ++n; }); });
  });
  const qas = chapters.flatMap((ch) => ch.secs.flatMap((s) => s.qas));
  const errors = [], warnings = [];
  if (chapters.length !== 4) errors.push(`expected 4 chapters, found ${chapters.length}`);
  if (qas.length < Q_RANGE[0] || qas.length > Q_RANGE[1]) errors.push(`${qas.length} questions, expected ${Q_RANGE.join('-')}`);
  for (const q of qas) {
    if (!q.answer) errors.push(`Q${q.n} has no answer`);
    const s = sentences(q.answer);
    if (s < SENT_RANGE[0] || s > SENT_RANGE[1]) errors.push(`Q${q.n} has ${s} sentences: ${q.q}`);
    if (!/؟$/.test(q.q)) errors.push(`Q${q.n} does not end with a question mark`);
  }
  // Internal references like «پرسش ۲۸» must point at the leakage question.
  for (const q of qas) for (const m of q.answer.matchAll(/پرسش ([۰-۹]+)/g)) {
    const target = qas[Number(toLatin(m[1])) - 1];
    if (!target || !/نشت/.test(target.q)) errors.push(`Q${q.n} refers to question ${m[1]}, which is "${target ? target.q : 'missing'}"`);
  }
  const known = knownNumbers();
  for (const q of qas) checkNumbers(`Q${q.n}`, q.q + ' ' + q.answer, known, warnings);
  chapters.forEach((ch) => {
    ch.intro.forEach((p) => checkNumbers(`chapter ${ch.num} intro`, p, known, warnings));
    ch.items.filter((it) => it.type === 'block').forEach((it) => checkNumbers(`chapter ${ch.num} ${it.block.kind}`, it.block.lines.join(' '), known, warnings));
  });
  if (errors.length) throw new Error(errors.join('\n'));
  warnings.forEach((w) => console.warn(`[check] ${w}`));

  fs.mkdirSync(buildDir, { recursive: true });
  const htmlPath = path.join(buildDir, 'study-guide.html');
  const html1 = renderHtml(chapters, qas.length);
  fs.writeFileSync(htmlPath, html1);
  const targets = [...html1.matchAll(/<span class="pg" data-target="([^"]+)">/g)].map((m) => m[1]);
  const browser = await puppeteer.launch({ executablePath: CHROME, args: ['--font-render-hinting=none'] });
  let bytes, pass2;
  try {
    const pass1 = await destinationPages(await printPdf(browser, htmlPath));
    const missing = targets.filter((t) => !pass1.map.has(t));
    if (missing.length) throw new Error(`no PDF destination for: ${missing.join(', ')}`);
    const html2 = html1.replace(/<span class="pg" data-target="([^"]+)">۰۰<\/span>/g, (m, id) => `<span class="pg" data-target="${id}">${fa(pass1.map.get(id))}</span>`);
    fs.writeFileSync(htmlPath, html2);
    bytes = await printPdf(browser, htmlPath);
    pass2 = await destinationPages(bytes);
    const moved = targets.filter((t) => pass2.map.get(t) !== pass1.map.get(t));
    if (moved.length || pass2.count !== pass1.count) throw new Error(`pagination changed between passes: ${moved.join(', ')}`);
  } finally {
    await browser.close();
  }
  fs.writeFileSync(path.join(buildDir, 'study-guide-draft.pdf'), bytes);
  if (pass2.count < PAGE_RANGE[0] || pass2.count > PAGE_RANGE[1]) throw new Error(`${pass2.count} pages, expected ${PAGE_RANGE.join('-')}`);
  const out = path.join(outDir, 'study-guide.pdf');
  fs.writeFileSync(out, await cleanPdfMetadata(bytes, { title: `راهنمای مطالعه · ${cfg.title}`, author: cfg.author }));
  const pages = targets.map((t) => `${t}=${pass2.map.get(t)}`).join(' ');
  console.log(`study guide: ${qas.length} questions, ${pass2.count} pages, TOC ${pages}`);
  console.log(`-> ${path.relative(path.resolve(root, '..'), out)}`);
  if (wantPng) {
    const pngDir = path.join(buildDir, 'guide-png');
    fs.rmSync(pngDir, { recursive: true, force: true });
    fs.mkdirSync(pngDir, { recursive: true });
    execFileSync('pdftoppm', ['-r', '80', '-png', out, path.join(pngDir, 'page')]);
    console.log(`png: ${fs.readdirSync(pngDir).length} images -> ${path.relative(root, pngDir)}/`);
  }
}

main().catch((e) => { console.error(e.message); process.exit(1); });
