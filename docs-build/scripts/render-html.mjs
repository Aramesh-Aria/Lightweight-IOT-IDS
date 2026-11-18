// Renders the parsed document model to a single print-ready HTML file.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fa, ieee } from './parse.mjs';

const require = createRequire(import.meta.url);
const katex = require('katex');

const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

// Latin run inside Persian text: starts with a letter, may contain inner spaces, dots, hyphens, slashes and digits.
const LAT_RUN = /[A-Za-zχ][A-Za-z0-9χ²_’'+&.]*(?:[ \-/:]+[A-Za-z0-9χ²][A-Za-z0-9χ²_’'+&.]*)*/g;

export const stats = { strayDigits: [] };

function persianText(s, ctx) {
  let out = '';
  let last = 0;
  LAT_RUN.lastIndex = 0;
  let m;
  const plain = (t) => esc(t.replace(/[0-9]+/g, (d) => { stats.strayDigits.push(`${ctx}: ${d}`); return fa(d); }));
  while ((m = LAT_RUN.exec(s))) {
    let run = m[0];
    let end = m.index + run.length;
    while (/[.\s]$/.test(run)) { run = run.slice(0, -1); end--; }
    out += plain(s.slice(last, m.index));
    out += `<span class="lat" dir="ltr">${esc(run)}</span>`;
    last = end;
    LAT_RUN.lastIndex = end;
  }
  out += plain(s.slice(last));
  return out;
}

// Wraps pure-digit compound numbers (۲-۳) in an LTR isolate.
const numIso = (label) => esc(label).replace(/[۰-۹]+(?:-[۰-۹]+)*/g, (n) => `<span class="n" dir="ltr">${n}</span>`);

export function inlineHtml(tokens, ctx = '', lang = 'fa') {
  return tokens.map((t) => {
    switch (t.t) {
      case 'text': return lang === 'en' ? esc(t.s) : persianText(t.s, ctx);
      case 'code': return `<code dir="ltr">${esc(t.s)}</code>`;
      case 'bold': return `<strong>${inlineHtml(t.c, ctx, lang)}</strong>`;
      case 'en': return `(<span class="en">${inlineHtml(t.c, ctx, lang)}</span>)`;
      case 'quote': return `«<span class="lat q" dir="ltr">${esc(t.s)}</span>»`;
      case 'kv': return `<span class="lat kv" dir="ltr">${esc(t.s)}</span>`;
      case 'ref': return `<a class="xref" href="#${t.id}">${numIso(t.label)}</a>`;
      case 'cite': {
        const sep = t.items.some((x) => x.page) ? '؛ ' : '، ';
        const parts = t.items.map((x) => `<a href="#ref-${x.key}">${fa(x.n)}</a>${x.page ? '، ' + esc(x.page) : ''}`);
        return `<span class="cite">[${parts.join(sep)}]</span>`;
      }
      default: throw new Error('unknown token ' + t.t);
    }
  }).join('');
}

const isNumericCell = (s) => /^[\s۰-۹٫٬±()\-–/%.]+$/.test(s) || s === '–';
const pgSlot = (id) => `<span class="pg" data-target="${id}">۰۰</span>`;
const two = (n) => fa(String(n).padStart(2, '0'));

function chapterHead(ch, cfg) {
  const lat = cfg.chapterLabels[ch.id] || '';
  const num = ch.numbered ? `<div class="ch-num">${two(ch.num)}</div>` : '';
  const titleHtml = ch.lang === 'en' ? esc(ch.title) : inlineHtml(ch.titleInl, ch.id);
  return `<header class="ch-head${ch.numbered ? '' : ' unnumbered'}">${num}<div class="ch-titles"><h1 id="${ch.id}">${titleHtml}</h1><div class="ch-lat">${esc(lat)}</div></div></header><div class="zigzag"></div>`;
}

function renderBlocks(ch) {
  const lang = ch.lang;
  const out = [];
  for (const b of ch.blocks) {
    const ctx = `${ch.file}`;
    if (b.type === 'heading') {
      const num = b.num ? `<span class="sec-num" dir="ltr">${esc(b.num)}</span>` : '';
      if (b.level === 2) out.push(`<h2 id="${b.id}">${num}<span class="h-text">${inlineHtml(b.inl, ctx, lang)}</span></h2>`);
      else out.push(`<h3 id="${b.id}"><span class="dia"></span>${num}<span class="h-text">${inlineHtml(b.inl, ctx, lang)}</span></h3>`);
    } else if (b.type === 'para') {
      const kw = b.text.match(/^(کلیدواژه‌ها:|Keywords:)\s*/);
      if (kw) {
        const rest = b.inl.slice();
        rest[0] = { ...rest[0], s: rest[0].s.slice(kw[0].length) };
        out.push(`<p class="kw"><strong>${esc(kw[1])}</strong> ${inlineHtml(rest, ctx, lang)}</p>`);
      } else out.push(`<p>${inlineHtml(b.inl, ctx, lang)}</p>`);
    } else if (b.type === 'table') {
      const head = b.headerInl.map((c) => `<th>${inlineHtml(c, ctx)}</th>`).join('');
      const rows = b.rowsInl.map((r, ri) => '<tr>' + r.map((c, ci) => `<td class="${ci === 0 ? 'first' : ''}${isNumericCell(b.rows[ri][ci]) ? ' num' : ''}">${inlineHtml(c, ctx)}</td>`).join('') + '</tr>').join('');
      const wide = b.header.length >= 5 ? ' wide' : '';
      out.push(`<div class="tbl${wide}" id="${b.id}"><div class="caption"><span class="lbl">جدول <span dir="ltr">${esc(b.num)}</span></span><span class="cap-text">${inlineHtml(b.captionInl, ctx)}</span></div><table><thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table></div>`);
    } else if (b.type === 'figure') {
      out.push(`<figure id="${b.id}"><div class="fig-box"><img src="file://${b.src}" alt=""></div><figcaption><span class="lbl">شکل <span dir="ltr">${esc(b.num)}</span></span><span class="cap-text">${inlineHtml(b.captionInl, ctx)}</span></figcaption></figure>`);
    } else if (b.type === 'equation') {
      const html = katex.renderToString(b.tex, { displayMode: true, throwOnError: true, output: 'html' });
      out.push(`<div class="eq"${b.id ? ` id="${b.id}"` : ''}><div class="eq-body" dir="ltr">${html}</div>${b.num ? `<div class="eq-num">(<span dir="ltr">${esc(b.num)}</span>)</div>` : ''}</div>`);
    } else if (b.type === 'code') {
      out.push(`<pre class="code" dir="ltr"><code>${esc(b.text)}</code></pre>`);
    }
  }
  return out.join('\n');
}

function renderChapter(ch, cfg) {
  const cls = ['chapter', ch.lang === 'en' ? 'lang-en' : '', ch.numbered ? '' : 'front'].filter(Boolean).join(' ');
  return `<section class="${cls}"${ch.lang === 'en' ? ' dir="ltr" lang="en"' : ''}>${chapterHead(ch, cfg)}\n${renderBlocks(ch)}</section>`;
}

function renderToc(doc, cfg) {
  const rows = [];
  const entries = doc.chapters.filter((c) => c.numbered);
  const tail = doc.chapters.filter((c) => c.id === 'sec:appendix');
  const one = (ch, numLabel) => {
    const secs = ch.blocks.filter((b) => b.type === 'heading' && b.level === 2);
    const secHtml = secs.map((s) => `<a class="toc-sec" href="#${s.id}">${s.num ? `<span class="ts-num" dir="ltr">${esc(s.num)}</span>` : ''}<span class="ts-title">${inlineHtml(doc.parseInline(s.text, { noCite: true }), 'toc')}</span>${pgSlot(s.id)}</a>`).join('');
    return `<div class="toc-ch"><a class="toc-main" href="#${ch.id}"><span class="tc-num">${numLabel}</span><span class="tc-titles"><span class="tc-title">${esc(ch.title)}</span><span class="tc-lat">${esc(cfg.chapterLabels[ch.id] || '')}</span></span><span class="leader"></span>${pgSlot(ch.id)}</a>${secs.length ? `<div class="toc-secs">${secHtml}</div>` : ''}</div>`;
  };
  for (const ch of entries) rows.push(one(ch, two(ch.num)));
  rows.push(`<div class="toc-ch"><a class="toc-main" href="#sec:references"><span class="tc-num">–</span><span class="tc-titles"><span class="tc-title">مراجع</span><span class="tc-lat">${esc(cfg.chapterLabels['sec:references'])}</span></span><span class="leader"></span>${pgSlot('sec:references')}</a></div>`);
  for (const ch of tail) rows.push(one(ch, 'پ'));
  const front = [
    ['sec:abstract-fa', 'چکیده'], ['sec:abstract-en', 'Abstract'], ['sec:lists', 'فهرست شکل‌ها و جدول‌ها'],
  ].map(([id, t]) => `<a class="toc-front" href="#${id}"><span>${esc(t)}</span><span class="leader"></span>${pgSlot(id)}</a>`).join('');
  return `<section class="toc"><header class="toc-head"><h1 id="sec:toc">فهرست مطالب</h1><span class="toc-lat">CONTENTS</span></header><div class="toc-fronts">${front}</div>${rows.join('\n')}</section>`;
}

function renderLists(doc) {
  const item = (b, kind) => `<a class="lst" href="#${b.id}"><span class="lst-lbl">${kind} <span dir="ltr">${esc(b.num)}</span></span><span class="lst-cap">${inlineHtml(b.captionListInl, 'lists')}</span><span class="leader"></span>${pgSlot(b.id)}</a>`;
  return `<section class="lists"><header class="toc-head"><h1 id="sec:lists">فهرست شکل‌ها و جدول‌ها</h1><span class="toc-lat">FIGURES · TABLES</span></header>
<h2 class="lst-h">فهرست شکل‌ها</h2>${doc.figures.map((b) => item(b, 'شکل')).join('')}
<h2 class="lst-h">فهرست جدول‌ها</h2>${doc.tables.map((b) => item(b, 'جدول')).join('')}</section>`;
}

function renderBibliography(doc, cfg) {
  const items = doc.bibliography.map(({ n, ref }) => {
    const body = ieee(ref).map((s) => (s.i ? `<i>${esc(s.s)}</i>` : esc(s.s))).join('');
    return `<li id="ref-${ref.id}"><span class="bn">[${fa(n)}]</span><span class="be" dir="ltr" lang="en">${body}</span></li>`;
  }).join('\n');
  const head = `<header class="ch-head unnumbered"><div class="ch-titles"><h1 id="sec:references">مراجع</h1><div class="ch-lat">${esc(cfg.chapterLabels['sec:references'])}</div></div></header><div class="zigzag"></div>`;
  return `<section class="chapter front bib">${head}<ol class="bib-list">${items}</ol></section>`;
}

function readTopFeatures(cfg, root) {
  const csv = fs.readFileSync(path.resolve(root, cfg.featureSource), 'utf8').trim().split('\n');
  const cols = csv[0].split(',');
  const fi = cols.indexOf('feature'), ii = cols.indexOf('importance');
  return csv.slice(1, 9).map((l) => { const c = l.split(','); return { name: c[fi], imp: Number(c[ii]) }; });
}

function coverArt(feats) {
  // Line art: FI ranking bars (left) feeding a two-level stacking diagram (right).
  const max = feats[0].imp;
  const bars = feats.map((f, i) => {
    const y = 18 + i * 21;
    const w = Math.round((f.imp / max) * 230);
    return `<g><text x="0" y="${y + 10}" class="ca-mono">${f.name}</text><rect x="110" y="${y}" width="${w}" height="12" rx="2" class="ca-bar${i < 3 ? ' hi' : ''}"/><text x="${116 + w}" y="${y + 10}" class="ca-val">${f.imp.toFixed(3)}</text></g>`;
  }).join('');
  return `<svg class="cover-art" viewBox="0 0 640 200" xmlns="http://www.w3.org/2000/svg">
  <g class="ca-bars">${bars}</g>
  <g class="ca-stack" transform="translate(400,10)">
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

function renderCover(cfg, feats) {
  const kw = cfg.keywordsColumn.map((k) => `<div>${esc(k)}</div>`).join('');
  const block = feats.map((f, i) => `<div class="fb-row"><span class="fb-i">${String(i + 1).padStart(2, '0')}</span><span class="fb-n">${esc(f.name)}</span><span class="fb-v">${f.imp.toFixed(4)}</span></div>`).join('');
  return `<section class="cover">
  <div class="cover-top">
    <div class="cover-inst"><div class="logo-tile"><img src="../assets/iau-logo.png" alt=""></div><div class="inst-text"><div class="uni">${esc(cfg.university)}</div><div class="fac">${esc(cfg.faculty)}</div><div class="kind">${esc(cfg.kind)}</div></div></div>
    <div class="cover-kw" dir="ltr">${kw}</div>
  </div>
  <div class="cover-label" dir="ltr"><span class="a">${esc(cfg.latinTitle)}</span><span class="b">${esc(cfg.latinKind)}</span></div>
  <h1 class="cover-title">${cfg.titleLines.map(esc).join('<br>')}</h1>
  <div class="cover-sub">${inlineHtml([{ t: 'text', s: cfg.coverSubtitle }], 'cover')}</div>
  <div class="cover-rule"></div>
  <div class="cover-desc">${inlineHtml([{ t: 'text', s: cfg.subtitle }], 'cover')}</div>
  ${coverArt(feats)}
  <div class="cover-bottom">
    <div class="people">
      <div><span class="role">دانشجو</span><span class="name">${esc(cfg.author)}</span></div>
      <div><span class="role">استاد درس</span><span class="name">${esc(cfg.supervisor)}</span></div>
      <div><span class="role">نیمسال</span><span class="name">${esc(cfg.semester.replace('نیمسال ', ''))}</span></div>
    </div>
    <div class="feat-block" dir="ltr"><div class="fb-head">TOP-8 FI · EXTRATREES · SEED 42</div>${block}</div>
  </div>
</section>`;
}

export function renderHtml(doc, cfg, { root, variant, pages = null }) {
  const feats = readTopFeatures(cfg, root);
  const byId = (id) => doc.chapters.find((c) => c.id === id);
  const body = [
    renderCover(cfg, feats),
    renderChapter(byId('sec:abstract-fa'), cfg),
    renderChapter(byId('sec:abstract-en'), cfg),
    renderToc(doc, cfg),
    renderLists(doc),
    ...doc.chapters.filter((c) => c.numbered).map((c) => renderChapter(c, cfg)),
    renderBibliography(doc, cfg),
    renderChapter(byId('sec:appendix'), cfg),
  ].join('\n');
  let html = `<!doctype html>
<html lang="fa" dir="rtl" class="${variant}"><head><meta charset="utf-8"><title>${esc(cfg.title)}</title>
<link rel="stylesheet" href="../node_modules/katex/dist/katex.min.css">
<link rel="stylesheet" href="../styles/report.css">
${variant === 'print' ? '<link rel="stylesheet" href="../styles/print.css">' : ''}
<style>@page { @top-left { content: "${cfg.latinTitle} · ${cfg.latinKind}"; } @top-right { content: "${cfg.shortTitle}"; } }</style>
</head><body>
${body}
</body></html>`;
  if (pages) html = fillPages(html, pages);
  return html;
}

export function fillPages(html, pages) {
  return html.replace(/<span class="pg" data-target="([^"]+)">۰۰<\/span>/g, (m, id) => {
    if (!pages.has(id)) throw new Error(`no page found for ${id}`);
    return `<span class="pg" data-target="${id}">${fa(pages.get(id))}</span>`;
  });
}

export function pageTargets(html) {
  return [...html.matchAll(/<span class="pg" data-target="([^"]+)">/g)].map((m) => m[1]);
}
