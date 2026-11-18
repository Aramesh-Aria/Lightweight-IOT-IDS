// Builds deliverables/seminar-report.docx from the same document model (Q10, Q38: colours and fonts only).
import fs from 'node:fs';
import path from 'node:path';
import puppeteer from 'puppeteer-core';
import JSZip from 'jszip';
import { createRequire } from 'node:module';
import {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, ShadingType,
  AlignmentType, HeadingLevel, TableOfContents, StyleLevel, Footer, Header, PageNumber, BorderStyle,
  PageBreak, VerticalAlign, TableLayoutType,
} from 'docx';
import { fa, ieee } from './parse.mjs';

const require = createRequire(import.meta.url);
const katex = require('katex');
const CHROME = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

const C = { navy: '111A2B', green: '0B6E66', orange: 'B4530B', gray: '7B8191', grayD: '3A4356', soft: 'F4F2EC', rule: 'D8D2C4', greenSoft: 'E2EFEC' };
const BODY = 'IRNazanin', HEAD = 'Vazirmatn', MONO = 'JetBrains Mono', LATIN = 'Crimson Pro';
const TEXT_W = 11906 - 2 * 1417; // A4 width minus 2.5 cm margins, in DXA
const LAT_RUN = /[A-Za-zχ][A-Za-z0-9χ²_’'+&.]*(?:[ \-/:]+[A-Za-z0-9χ²][A-Za-z0-9χ²_’'+&.]*)*/g;

const font = (cs, latin = cs) => ({ ascii: latin, hAnsi: latin, cs, eastAsia: cs });

// ---------- inline tokens -> runs ----------
function textRuns(s, base) {
  const out = [];
  let last = 0; let m;
  LAT_RUN.lastIndex = 0;
  while ((m = LAT_RUN.exec(s))) {
    let run = m[0]; let end = m.index + run.length;
    while (/[.\s]$/.test(run)) { run = run.slice(0, -1); end--; }
    if (m.index > last) out.push(new TextRun({ ...base, text: s.slice(last, m.index), rightToLeft: true }));
    out.push(new TextRun({ ...base, text: run, rightToLeft: false }));
    last = end; LAT_RUN.lastIndex = end;
  }
  if (last < s.length) out.push(new TextRun({ ...base, text: s.slice(last), rightToLeft: true }));
  return out;
}

function runs(tokens, base = {}, lang = 'fa') {
  const out = [];
  for (const t of tokens) {
    if (t.t === 'text') out.push(...(lang === 'en' ? [new TextRun({ ...base, text: t.s })] : textRuns(t.s, base)));
    else if (t.t === 'code') out.push(new TextRun({ ...base, text: t.s, font: font(MONO), size: Math.round((base.size || 26) * 0.75), color: C.green, rightToLeft: false }));
    else if (t.t === 'bold') out.push(...runs(t.c, { ...base, bold: true }, lang));
    else if (t.t === 'en') { out.push(...textRuns('(', base)); out.push(...runs(t.c, { ...base, color: C.gray }, lang)); out.push(...textRuns(')', base)); }
    else if (t.t === 'quote') out.push(...textRuns('«', base), new TextRun({ ...base, text: t.s, rightToLeft: false }), ...textRuns('»', base));
    else if (t.t === 'kv') out.push(new TextRun({ ...base, text: t.s, rightToLeft: false }));
    else if (t.t === 'ref') out.push(new TextRun({ ...base, text: t.label, rightToLeft: true }));
    else if (t.t === 'cite') out.push(new TextRun({ ...base, text: t.label, rightToLeft: true }));
  }
  return out;
}

const para = (children, opts = {}) => new Paragraph({ bidirectional: true, alignment: AlignmentType.BOTH, ...opts, children });

// ---------- images ----------
function pngSize(buf) { return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) }; }
function imageRun(buf, maxW, maxH) {
  const { w, h } = pngSize(buf);
  const s = Math.min(maxW / w, maxH / h, 1);
  return new ImageRun({ type: 'png', data: buf, transformation: { width: Math.round(w * s), height: Math.round(h * s) } });
}

async function renderEquations(doc, root) {
  const eqs = doc.chapters.flatMap((c) => c.blocks.filter((b) => b.type === 'equation'));
  if (!eqs.length) return new Map();
  const browser = await puppeteer.launch({ executablePath: CHROME });
  const out = new Map();
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 900, height: 300, deviceScaleFactor: 3 });
    const css = 'file://' + path.join(root, 'node_modules/katex/dist/katex.min.css');
    for (const b of eqs) {
      const html = katex.renderToString(b.tex, { displayMode: true, output: 'html' });
      const tmp = path.join(root, 'build', 'eq.html');
      fs.writeFileSync(tmp, `<html><head><link rel="stylesheet" href="${css}"><style>body{margin:0;background:#fff;color:#111a2b}#e{display:inline-block;padding:4px 8px;font-size:20px}.katex-display{margin:0}</style></head><body><div id="e">${html}</div></body></html>`);
      await page.goto('file://' + tmp, { waitUntil: 'networkidle0' });
      await page.evaluate(() => document.fonts.ready);
      const el = await page.$('#e');
      out.set(b, Buffer.from(await el.screenshot({ type: 'png' })));
    }
  } finally { await browser.close(); }
  return out;
}

// ---------- blocks ----------
function heading(level, numText, inl, lang) {
  const sizes = { 1: 36, 2: 28, 3: 24 };
  const base = { font: font(HEAD), size: sizes[level], bold: true, color: C.navy };
  const kids = [];
  if (numText) kids.push(new TextRun({ ...base, text: numText + '  ', color: C.green, rightToLeft: true }));
  kids.push(...runs(inl, base, lang));
  const hl = { 1: HeadingLevel.HEADING_1, 2: HeadingLevel.HEADING_2, 3: HeadingLevel.HEADING_3 }[level];
  return new Paragraph({ heading: hl, bidirectional: lang !== 'en', alignment: lang === 'en' ? AlignmentType.LEFT : AlignmentType.RIGHT, children: kids, pageBreakBefore: level === 1 });
}

function caption(kind, num, inl, style) {
  const base = { font: font(HEAD), size: 18, color: C.grayD };
  return new Paragraph({ style, bidirectional: true, alignment: AlignmentType.CENTER, keepNext: style === 'TableCaption',
    children: [new TextRun({ ...base, text: `${kind} ${num} — `, bold: true, color: C.green, rightToLeft: true }), ...runs(inl, base)] });
}

function table(b) {
  const n = b.header.length;
  const len = (s) => Math.min(Math.max(s.length, 4), 60);
  const weights = b.header.map((h, i) => Math.max(len(h), ...b.rows.map((r) => len(r[i]))));
  const total = weights.reduce((a, x) => a + x, 0);
  const widths = weights.map((w) => Math.floor((w / total) * TEXT_W));
  widths[0] += TEXT_W - widths.reduce((a, x) => a + x, 0);
  const size = n >= 5 ? 15 : 17;
  const border = { style: BorderStyle.SINGLE, size: 2, color: 'E6E9EE' };
  const borders = { top: border, bottom: border, left: border, right: border };
  const cell = (inl, i, opts) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA }, borders, verticalAlign: VerticalAlign.CENTER,
    margins: { top: 50, bottom: 50, left: 80, right: 80 }, shading: opts.fill ? { type: ShadingType.CLEAR, color: 'auto', fill: opts.fill } : undefined,
    children: [new Paragraph({ bidirectional: true, alignment: opts.center ? AlignmentType.CENTER : AlignmentType.RIGHT, children: runs(inl, { font: font(HEAD), size, bold: opts.bold, color: opts.color }) })],
  });
  const head = new TableRow({ tableHeader: true, children: b.headerInl.map((c, i) => cell(c, i, { fill: C.navy, color: 'FFFFFF', bold: true, center: true })) });
  const rows = b.rowsInl.map((r, ri) => new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, i, { fill: ri % 2 ? C.soft : undefined, bold: i === 0, center: /^[\s۰-۹٫٬±()\-–/%.]+$/.test(b.rows[ri][i]) })) }));
  return new Table({ width: { size: TEXT_W, type: WidthType.DXA }, columnWidths: widths, layout: TableLayoutType.FIXED, visuallyRightToLeft: true, rows: [head, ...rows] });
}

function blocks(ch, eqImgs) {
  const out = [];
  const lang = ch.lang;
  const bodyBase = lang === 'en' ? { font: font(LATIN), size: 25 } : {};
  for (const b of ch.blocks) {
    if (b.type === 'heading') out.push(heading(b.level, b.num, b.inl, lang));
    else if (b.type === 'para') {
      const kw = b.text.match(/^(کلیدواژه‌ها:|Keywords:)\s*/);
      let inl = b.inl; const kids = [];
      if (kw) { inl = inl.slice(); inl[0] = { ...inl[0], s: inl[0].s.slice(kw[0].length) }; kids.push(new TextRun({ ...bodyBase, text: kw[1] + ' ', bold: true, color: C.green, rightToLeft: lang !== 'en' })); }
      kids.push(...runs(inl, bodyBase, lang));
      out.push(lang === 'en' ? new Paragraph({ alignment: AlignmentType.BOTH, children: kids }) : para(kids));
    } else if (b.type === 'table') {
      out.push(caption('جدول', b.num, b.captionInl, 'TableCaption'));
      out.push(table(b));
      out.push(new Paragraph({ children: [], spacing: { after: 120 } }));
    } else if (b.type === 'figure') {
      out.push(new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, children: [imageRun(fs.readFileSync(b.src), 590, 400)] }));
      out.push(caption('شکل', b.num, b.captionInl, 'FigureCaption'));
    } else if (b.type === 'equation') {
      const img = eqImgs.get(b);
      const { w, h } = pngSize(img);
      out.push(new Paragraph({ bidirectional: true, alignment: AlignmentType.CENTER, shading: { type: ShadingType.CLEAR, color: 'auto', fill: C.greenSoft }, spacing: { before: 120, after: 160 },
        children: [new ImageRun({ type: 'png', data: img, transformation: { width: Math.round(w / 3), height: Math.round(h / 3) } }),
          ...(b.num ? [new TextRun({ text: `     (${b.num})`, font: font(HEAD), size: 19, color: C.green, rightToLeft: true })] : [])] }));
    } else if (b.type === 'code') {
      for (const line of b.text.split('\n')) out.push(new Paragraph({ alignment: AlignmentType.LEFT, spacing: { line: 276, after: 0 }, shading: { type: ShadingType.CLEAR, color: 'auto', fill: C.navy }, children: [new TextRun({ text: line || ' ', font: font(MONO), size: 17, color: 'E6E9EE' })] }));
      out.push(new Paragraph({ children: [] }));
    }
  }
  return out;
}

function chapterTitle(ch, cfg) {
  const lat = cfg.chapterLabels[ch.id] || '';
  const isEn = ch.lang === 'en';
  return [
    heading(1, ch.numbered ? `فصل ${fa(ch.num)}` : null, ch.titleInl, ch.lang),
    new Paragraph({ bidirectional: !isEn, alignment: isEn ? AlignmentType.LEFT : AlignmentType.RIGHT, spacing: { after: 280 }, border: { bottom: { style: BorderStyle.DASHED, size: 6, color: C.navy, space: 4 } },
      children: [new TextRun({ text: lat, font: font(HEAD, 'Instrument Sans'), size: 15, bold: true, color: C.gray, characterSpacing: 40 })] }),
  ];
}

function cover(cfg, root) {
  const logo = fs.readFileSync(path.join(root, 'assets', 'iau-logo.png'));
  const c = (text, o = {}) => new Paragraph({ bidirectional: true, alignment: AlignmentType.CENTER, spacing: { after: o.after ?? 80 }, children: [new TextRun({ text, font: font(HEAD), size: o.size || 24, bold: o.bold, color: o.color || C.navy, rightToLeft: true })] });
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 }, children: [imageRun(logo, 90, 135)] }),
    c(cfg.university, { size: 26, bold: true }),
    c(cfg.faculty, { size: 22, color: C.grayD }),
    c(cfg.kind, { size: 22, color: C.green, after: 900 }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [new TextRun({ text: `${cfg.latinTitle}  ·  `, font: font('Instrument Sans'), size: 16, bold: true, color: C.green, characterSpacing: 40 }), new TextRun({ text: cfg.latinKind, font: font('Instrument Sans'), size: 16, bold: true, color: C.orange, characterSpacing: 40 })] }),
    c(cfg.title, { size: 44, bold: true, after: 240 }),
    new Paragraph({ bidirectional: true, alignment: AlignmentType.CENTER, spacing: { after: 1400 }, children: textRuns(cfg.subtitle, { font: font(HEAD), size: 24, color: C.grayD }) }),
    c(`دانشجو: ${cfg.author}`, { size: 24, bold: true }),
    c(`استاد درس: ${cfg.supervisor}`, { size: 24, bold: true }),
    c(cfg.semester, { size: 22, color: C.grayD }),
  ];
}

function listSection(title, styleName) {
  return [
    new Paragraph({ bidirectional: true, alignment: AlignmentType.RIGHT, spacing: { before: 240, after: 120 }, children: [new TextRun({ text: title, font: font(HEAD), size: 26, bold: true, color: C.navy, rightToLeft: true })] }),
    new TableOfContents(title, { hyperlink: true, stylesWithLevels: [new StyleLevel(styleName, 1)] }),
  ];
}

function bibliography(doc, cfg) {
  const out = chapterTitle({ id: 'sec:references', numbered: false, titleInl: [{ t: 'text', s: 'مراجع' }], lang: 'fa' }, cfg);
  for (const { n, ref } of doc.bibliography) {
    const segs = ieee(ref).map((s) => new TextRun({ text: s.s, italics: !!s.i, font: font(LATIN), size: 21, rightToLeft: false }));
    out.push(new Paragraph({ bidirectional: true, alignment: AlignmentType.RIGHT, spacing: { after: 100, line: 300 }, indent: { right: 560, hanging: 560 },
      children: [new TextRun({ text: `[${fa(n)}]\t`, font: font(HEAD), size: 19, bold: true, color: C.green, rightToLeft: true }), ...segs] }));
  }
  return out;
}

export async function buildDocx({ doc, cfg, root, outDir, log }) {
  const eqImgs = await renderEquations(doc, root);
  const byId = (id) => doc.chapters.find((c) => c.id === id);
  const main = [];
  for (const id of ['sec:abstract-fa', 'sec:abstract-en']) { const ch = byId(id); main.push(...chapterTitle(ch, cfg), ...blocks(ch, eqImgs)); }
  main.push(new Paragraph({ children: [new PageBreak()] }));
  main.push(new Paragraph({ bidirectional: true, alignment: AlignmentType.RIGHT, spacing: { after: 200 }, children: [new TextRun({ text: 'فهرست مطالب', font: font(HEAD), size: 40, bold: true, color: C.navy, rightToLeft: true })] }));
  main.push(new TableOfContents('فهرست مطالب', { hyperlink: true, headingStyleRange: '1-2' }));
  main.push(new Paragraph({ children: [new PageBreak()] }));
  main.push(...listSection('فهرست شکل‌ها', 'FigureCaption'), ...listSection('فهرست جدول‌ها', 'TableCaption'));
  for (const ch of doc.chapters.filter((c) => c.numbered)) main.push(...chapterTitle(ch, cfg), ...blocks(ch, eqImgs));
  main.push(...bibliography(doc, cfg));
  const app = byId('sec:appendix');
  main.push(...chapterTitle(app, cfg), ...blocks(app, eqImgs));

  const fontFile = (p) => fs.readFileSync(path.resolve(root, '..', 'fonts', p));
  const headingStyle = (size, before, after) => ({ run: { font: font(HEAD), size, bold: true, color: C.navy }, paragraph: { spacing: { before, after }, keepNext: true, keepLines: true } });
  const pageProps = { page: { size: { width: 11906, height: 16838 }, margin: { top: 1417, bottom: 1417, left: 1417, right: 1417, header: 700, footer: 700 } } };

  const document = new Document({
    title: cfg.title, creator: cfg.author, description: '', lastModifiedBy: cfg.author,
    features: { updateFields: true },
    fonts: [
      { name: BODY, data: fontFile('IRNazanin/IRNazanin.ttf'), bold: fontFile('IRNazanin/IRNazanin-Bold.ttf') },
      { name: HEAD, data: fontFile('Vazirmatn/Vazirmatn-Regular.ttf'), bold: fontFile('Vazirmatn/Vazirmatn-Bold.ttf') },
      { name: MONO, data: fontFile('latin/JetBrainsMono-Regular.ttf') },
      { name: LATIN, data: fontFile('latin/CrimsonPro-Regular.ttf'), bold: fontFile('latin/CrimsonPro-Bold.ttf'), italic: fontFile('latin/CrimsonPro-Italic.ttf') },
    ],
    styles: {
      default: {
        document: { run: { font: font(BODY, LATIN), size: 26, sizeComplexScript: 26, color: C.navy, language: { value: 'en-US', bidirectional: 'fa-IR' } }, paragraph: { spacing: { line: 360, after: 120 } } },
        heading1: headingStyle(36, 0, 120), heading2: headingStyle(28, 360, 120), heading3: headingStyle(24, 240, 80),
      },
      paragraphStyles: [
        { id: 'FigureCaption', name: 'FigureCaption', basedOn: 'Normal', run: { font: font(HEAD), size: 18, color: C.grayD }, paragraph: { spacing: { before: 60, after: 240 } } },
        { id: 'TableCaption', name: 'TableCaption', basedOn: 'Normal', run: { font: font(HEAD), size: 18, color: C.grayD }, paragraph: { spacing: { before: 200, after: 80 }, keepNext: true } },
      ],
    },
    sections: [
      { properties: { ...pageProps, titlePage: false }, children: cover(cfg, root) },
      {
        properties: { ...pageProps, pageNumbers: { start: 2 } },
        headers: { default: new Header({ children: [new Paragraph({ bidirectional: true, alignment: AlignmentType.RIGHT, children: [new TextRun({ text: cfg.shortTitle, font: font(HEAD), size: 15, color: C.gray, rightToLeft: true })] })] }) },
        footers: { default: new Footer({ children: [new Paragraph({ bidirectional: true, alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: font(HEAD), size: 20, bold: true, color: C.green, rightToLeft: true, language: { bidirectional: 'fa-IR' } })] })] }) },
        children: main,
      },
    ],
  });
  const buf = await Packer.toBuffer(document);
  const clean = await cleanDocxMetadata(buf, cfg);
  const file = path.join(outDir, 'seminar-report.docx');
  fs.writeFileSync(file, clean);
  log(`seminar-report.docx: ${(clean.length / 1024).toFixed(0)} KB, ${eqImgs.size} equation images`);
}

const xmlEsc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

export async function cleanDocxMetadata(buf, cfg) {
  const zip = await JSZip.loadAsync(buf);
  zip.file('docProps/core.xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>${xmlEsc(cfg.title)}</dc:title><dc:creator>${xmlEsc(cfg.author)}</dc:creator></cp:coreProperties>`);
  if (zip.file('docProps/app.xml')) zip.file('docProps/app.xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"></Properties>`);
  if (zip.file('docProps/custom.xml')) zip.file('docProps/custom.xml', `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"></Properties>`);
  // Copy files only, without folder entries (Word refuses some archives that contain them).
  const flat = new JSZip();
  for (const [name, entry] of Object.entries(zip.files)) if (!entry.dir) flat.file(name, await entry.async('nodebuffer'), { createFolders: false, date: new Date('2026-01-01T00:00:00Z') });
  return flat.generateAsync({ type: 'nodebuffer', compression: 'DEFLATE' });
}
