// Builds the presentation slides and the speaker-notes PDF.
//   node scripts/build-slides.mjs          -> deliverables/seminar-slides.pdf + deliverables/speaker-notes.pdf
//   node scripts/build-slides.mjs --png    -> also writes one PNG per slide to build/slides-png/ for review
// Checks: slide count, overflow inside each slide, notes count matches slides, numbers in slides and notes
// appear in the report sources, notes length against the 20-minute target.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import puppeteer from 'puppeteer-core';
import { cleanPdfMetadata } from './build-pdf.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const slidesDir = path.join(root, 'slides');
const buildDir = path.join(root, 'build');
const outDir = path.resolve(root, '..', 'deliverables');
const CHROME = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const EXPECTED_SLIDES = 18;
const WORDS_PER_MINUTE = 125; // slow, clear Persian presentation pace
const wantPng = process.argv.includes('--png');

const cfg = JSON.parse(fs.readFileSync(path.join(root, 'config', 'report.json'), 'utf8'));
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const faDigits = (s) => String(s).replace(/[0-9]/g, (d) => '۰۱۲۳۴۵۶۷۸۹'[d]);
const toLatin = (s) => s.replace(/[۰-۹]/g, (d) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(d))).replace(/٫/g, '.').replace(/٬/g, '');

// A Persian comma between two Latin words is a neutral between two LTR runs, so the bidi algorithm
// joins the words into one LTR run and a list like "PFI، MI" reads backwards in RTL text.
// A right-to-left mark after the comma breaks the run. English glosses in .en spans are left alone.
function fixLatinLists(html) {
  return html.split(/(<span class="en">[^<]*<\/span>)/).map((part, i) => (i % 2
    ? part
    : part.replace(/([A-Za-z0-9²)])، (?=[A-Za-z])/g, '$1،\u200f '))).join('');
}

function topFeatures() {
  const csv = fs.readFileSync(path.resolve(root, cfg.featureSource), 'utf8').trim().split('\n');
  const cols = csv[0].split(',');
  const fi = cols.indexOf('feature'), ii = cols.indexOf('importance');
  return csv.slice(1, 9).map((l) => { const c = l.split(','); return { name: c[fi], imp: Number(c[ii]) }; });
}

function coverArt(feats) {
  // Same line art as the report cover: FI ranking bars feeding a two-level stacking diagram.
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

function renderSlides() {
  let html = fs.readFileSync(path.join(slidesDir, 'slides.html'), 'utf8');
  const tokens = {
    title: esc(cfg.title),
    titleLine: esc(cfg.titleLines.join(' ')),
    coverSubtitle: esc(cfg.coverSubtitle),
    subtitle: esc(cfg.subtitle),
    latinTitle: esc(cfg.latinTitle),
    university: esc(cfg.university),
    faculty: esc(cfg.faculty),
    author: esc(cfg.author),
    supervisor: esc(cfg.supervisor),
    semester: esc(cfg.semester.replace('نیمسال ', '')),
    keywords: cfg.keywordsColumn.map((k) => `<div>${esc(k)}</div>`).join(''),
    coverArt: coverArt(topFeatures()),
  };
  html = html.replace(/\{\{(\w+)\}\}/g, (m, k) => {
    if (!(k in tokens)) throw new Error(`unknown token ${m}`);
    return tokens[k];
  });
  html = fixLatinLists(html);
  // Add header and slide number to every slide.
  let n = 0;
  const total = (html.match(/<section class="slide/g) || []).length;
  html = html.replace(/<section class="slide([^"]*)"([^>]*)>/g, (m, cls, attrs) => {
    n += 1;
    const sec = /data-sec="([^"]+)"/.exec(attrs);
    const num = /data-n="([^"]+)"/.exec(attrs);
    const lat = /data-lat="([^"]+)"/.exec(attrs);
    const hd = sec ? `<div class="hd"><div class="sec"><b>${num[1]}</b>${sec[1]}</div><div class="lat">${lat[1]}</div></div>` : '';
    return `${m}${hd}<div class="num">${faDigits(n)} <span>/ ${faDigits(total)}</span></div>`;
  });
  return { html, total };
}

// ---------- speaker notes ----------
function parseNotes() {
  const src = fs.readFileSync(path.join(slidesDir, 'notes.md'), 'utf8');
  const parts = src.split(/^## /m).slice(1);
  return parts.map((p) => {
    const [head, ...rest] = p.split('\n');
    const paras = rest.join('\n').trim().split(/\n\s*\n/).map((s) => s.replace(/\s*\n\s*/g, ' ').trim()).filter(Boolean);
    return { n: Number(toLatin(head.trim())), paras };
  });
}

const inline = (s) => fixLatinLists(esc(s)).replace(/(?<![\w`.-])([A-Za-z]+(?:-[A-Za-z0-9]+)+)(?![\w`])/g, '<span class="nw">$1</span>').replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');
const words = (s) => s.split(/\s+/).filter(Boolean).length;

function renderNotes(notes, titles) {
  const blocks = notes.map((nt, i) => {
    const w = nt.paras.reduce((a, p) => a + words(p), 0);
    const min = (w / WORDS_PER_MINUTE).toFixed(1);
    return `<section class="note">
  <div class="nh"><div class="nn">${faDigits(String(nt.n).padStart(2, '0'))}</div><div><h2>${esc(titles[i])}</h2><div class="meta">حدود ${faDigits(min.replace('.', '٫'))} دقیقه · ${faDigits(w)} کلمه</div></div></div>
  ${nt.paras.map((p) => `<p>${inline(p)}</p>`).join('\n  ')}
</section>`;
  }).join('\n');
  const totalW = notes.reduce((a, nt) => a + nt.paras.reduce((b, p) => b + words(p), 0), 0);
  return { totalW, html: `<!DOCTYPE html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8"><title>متن گفتاری · ${esc(cfg.title)}</title>
<link rel="stylesheet" href="../slides/notes.css"></head>
<body>
<header class="cover-note">
  <div class="lab"><span class="a">${esc(cfg.latinTitle)}</span><span class="b">SPEAKER NOTES</span></div>
  <h1>متن گفتاری ارائه</h1>
  <div class="sub">${esc(cfg.title)}</div>
  <div class="by">${esc(cfg.author)} · ${esc(cfg.semester)} · ${faDigits(notes.length)} اسلاید، حدود ${faDigits(Math.round(totalW / WORDS_PER_MINUTE))} دقیقه</div>
</header>
${blocks}
</body></html>` };
}

// ---------- number check ----------
function reportNumbers() {
  const files = fs.readdirSync(path.join(root, 'report')).filter((f) => f.endsWith('.md'));
  let text = files.map((f) => fs.readFileSync(path.join(root, 'report', f), 'utf8')).join('\n');
  text += JSON.stringify(cfg);
  return new Set((toLatin(text).match(/\d+(?:\.\d+)?/g) || []));
}
function checkNumbers(label, text, known) {
  const nums = toLatin(text).match(/\d+(?:\.\d+)?/g) || [];
  // Small integers (counts, k values, slide numbers) are too common to check; check decimals and >= 21.
  const bad = [...new Set(nums.filter((x) => (x.includes('.') || Number(x) > 20) && !known.has(x)))];
  if (bad.length) console.warn(`[check] ${label}: numbers not found in report sources: ${bad.join(', ')}`);
  return bad;
}

async function main() {
  fs.mkdirSync(buildDir, { recursive: true });
  const { html, total } = renderSlides();
  if (total !== EXPECTED_SLIDES) throw new Error(`expected ${EXPECTED_SLIDES} slides, found ${total}`);
  const slidesHtml = path.join(slidesDir, 'build-slides.tmp.html'); // next to slides.css so relative paths hold
  fs.writeFileSync(slidesHtml, html);

  const notes = parseNotes();
  if (notes.length !== total) throw new Error(`notes.md has ${notes.length} sections, slides have ${total}`);
  notes.forEach((nt, i) => { if (nt.n !== i + 1) throw new Error(`notes section ${i + 1} is numbered ${nt.n}`); });

  const browser = await puppeteer.launch({ executablePath: CHROME, args: ['--font-render-hinting=none'] });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 720 });
    await page.goto('file://' + slidesHtml, { waitUntil: 'networkidle0' });
    await page.evaluate(async () => { await document.fonts.ready; });
    const info = await page.evaluate(() => {
      const out = [];
      document.querySelectorAll('section.slide').forEach((s, i) => {
        const box = s.getBoundingClientRect();
        const issues = [];
        if (s.scrollHeight > s.clientHeight + 1 || s.scrollWidth > s.clientWidth + 1) issues.push('scroll overflow');
        s.querySelectorAll('*').forEach((el) => {
          if (el.closest('svg') && el.tagName !== 'svg') return;
          if (el.closest('.num')) return;
          const r = el.getBoundingClientRect();
          if (!r.width || !r.height) return;
          if (r.bottom > box.bottom - 56 && !el.closest('.num') && !el.closest('.cv-bottom')) issues.push(`below content area: ${el.tagName}.${el.className} (${Math.round(r.bottom - box.top)}px)`);
          if (r.left < box.left + 40 || r.right > box.right - 40) issues.push(`outside side margin: ${el.tagName}.${el.className}`);
        });
        const h2 = s.querySelector('h2');
        out.push({ i: i + 1, issues: [...new Set(issues)], title: h2 ? h2.textContent.trim() : '', text: (() => { const w = document.createTreeWalker(s, NodeFilter.SHOW_TEXT); const t = []; while (w.nextNode()) if (!w.currentNode.parentElement.closest('svg')) t.push(w.currentNode.nodeValue); return t.join(' '); })() });
      });
      return out;
    });
    const problems = info.filter((s) => s.issues.length);
    for (const s of problems) console.error(`[overflow] slide ${s.i}: ${s.issues.join('; ')}`);

    const known = reportNumbers();
    info.forEach((s) => checkNumbers(`slide ${s.i}`, s.text, known));
    notes.forEach((nt) => checkNumbers(`notes ${nt.n}`, nt.paras.join(' '), known));

    const pdf = await page.pdf({ preferCSSPageSize: true, printBackground: true, displayHeaderFooter: false, outline: false, tagged: false });
    const slidesOut = path.join(outDir, 'seminar-slides.pdf');
    fs.writeFileSync(slidesOut, await cleanPdfMetadata(Buffer.from(pdf), { title: cfg.title, author: cfg.author }));
    console.log(`slides: ${total} pages -> ${path.relative(path.resolve(root, '..'), slidesOut)}`);

    await page.close();
    if (problems.length) throw new Error(`${problems.length} slide(s) overflow`);

    const titles = info.map((s) => s.title || (s.i === 1 ? 'اسلاید عنوان' : 'پایان و پرسش'));
    const { html: notesHtml, totalW } = renderNotes(notes, titles);
    const notesPath = path.join(buildDir, 'speaker-notes.html');
    fs.writeFileSync(notesPath, notesHtml);
    const np = await browser.newPage();
    await np.goto('file://' + notesPath, { waitUntil: 'networkidle0' });
    await np.evaluate(async () => { await document.fonts.ready; });
    const npdf = await np.pdf({ preferCSSPageSize: true, printBackground: true, displayHeaderFooter: false, outline: false, tagged: false });
    const notesOut = path.join(outDir, 'speaker-notes.pdf');
    fs.writeFileSync(notesOut, await cleanPdfMetadata(Buffer.from(npdf), { title: `متن گفتاری · ${cfg.title}`, author: cfg.author }));
    await np.close();
    const perSlide = notes.map((nt) => nt.paras.reduce((a, p) => a + words(p), 0));
    console.log(`notes: ${totalW} words, about ${(totalW / WORDS_PER_MINUTE).toFixed(1)} min at ${WORDS_PER_MINUTE} wpm; per slide ${perSlide.join(' ')}`);
    console.log(`notes -> ${path.relative(path.resolve(root, '..'), notesOut)}`);
    if (wantPng) {
      // Review images are rendered from the final PDFs, so they show exactly what was delivered.
      const pngDir = path.join(buildDir, 'slides-png');
      fs.rmSync(pngDir, { recursive: true, force: true });
      fs.mkdirSync(pngDir, { recursive: true });
      execFileSync('pdftoppm', ['-r', '72', '-png', slidesOut, path.join(pngDir, 'slide')]);
      execFileSync('pdftoppm', ['-r', '60', '-png', notesOut, path.join(pngDir, 'notes')]);
      console.log(`png: ${fs.readdirSync(pngDir).length} images -> ${path.relative(root, pngDir)}/`);
    }
  } finally {
    await browser.close();
    fs.rmSync(slidesHtml, { force: true });
  }
}

main().catch((e) => { console.error(e.message); process.exit(1); });
