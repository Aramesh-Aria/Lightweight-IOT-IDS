// Parses the report Markdown (docs-build/report/FORMAT.md) into a numbered document model.
import fs from 'node:fs';
import path from 'node:path';

export const FA_DIGITS = '۰۱۲۳۴۵۶۷۸۹';
export const fa = (s) => String(s).replace(/[0-9]/g, (d) => FA_DIGITS[d]);

export const FILES = [
  'abstract-fa.md', 'abstract-en.md',
  'ch01-introduction.md', 'ch02-background.md', 'ch03-main-paper.md', 'ch04-support-paper.md',
  'ch05-method.md', 'ch06-results.md', 'ch07-critique.md', 'ch08-conclusion.md',
  'appendix.md',
];

const UNNUMBERED = new Set(['sec:abstract-fa', 'sec:abstract-en', 'sec:appendix']);
const APPENDIX_PREFIX = 'پ';

class BuildError extends Error {}
const fail = (msg) => { throw new BuildError(msg); };

// ---------- block parsing ----------

function parseHeading(line) {
  const m = line.match(/^(#{1,3}) (.*?)(?:\s*\{#(sec:[a-z0-9-]+)\})?\s*$/);
  if (!m) return null;
  return { level: m[1].length, text: m[2].trim(), id: m[3] || null };
}

function splitRow(line) {
  let s = line.trim();
  if (s.startsWith('|')) s = s.slice(1);
  if (s.endsWith('|')) s = s.slice(0, -1);
  return s.split('|').map((c) => c.trim());
}

function parseFile(file, srcDir) {
  const lines = fs.readFileSync(path.join(srcDir, file), 'utf8').replace(/\r/g, '').split('\n');
  const blocks = [];
  let i = 0;
  const first = parseHeading(lines[0] || '');
  if (!first || first.level !== 1 || !first.id) fail(`${file}: first line must be a level-1 heading with an id`);
  i = 1;
  const nextNonBlank = (j) => { while (j < lines.length && lines[j].trim() === '') j++; return j; };
  while (i < lines.length) {
    const line = lines[i];
    const t = line.trim();
    if (t === '') { i++; continue; }
    const h = parseHeading(line);
    if (h) {
      if (h.level === 1) fail(`${file}:${i + 1}: second level-1 heading`);
      blocks.push({ type: 'heading', ...h, line: i + 1 });
      i++; continue;
    }
    if (t === '$$') {
      const body = [];
      i++;
      while (i < lines.length && lines[i].trim() !== '$$') body.push(lines[i++]);
      if (i >= lines.length) fail(`${file}: unterminated $$`);
      i++;
      let id = null;
      const j = nextNonBlank(i);
      const m = (lines[j] || '').trim().match(/^\{#(eq:[a-z0-9-]+)\}$/);
      if (m) { id = m[1]; i = j + 1; }
      blocks.push({ type: 'equation', tex: body.join('\n').trim(), id });
      continue;
    }
    if (t.startsWith('```')) {
      const lang = t.slice(3).trim();
      const body = [];
      i++;
      while (i < lines.length && lines[i].trim() !== '```') body.push(lines[i++]);
      if (i >= lines.length) fail(`${file}: unterminated code block`);
      i++;
      blocks.push({ type: 'code', lang, text: body.join('\n') });
      continue;
    }
    if (t.startsWith('|')) {
      const rows = [];
      while (i < lines.length && lines[i].trim().startsWith('|')) rows.push(lines[i++]);
      if (rows.length < 2 || !/^\|?\s*:?-{3,}/.test(rows[1].trim())) fail(`${file}:${i}: table without |---| row`);
      const header = splitRow(rows[0]);
      const body = rows.slice(2).map(splitRow);
      body.forEach((r, k) => { if (r.length !== header.length) fail(`${file}: table row ${k + 1} has ${r.length} cells, header has ${header.length}`); });
      const j = nextNonBlank(i);
      const cm = (lines[j] || '').trim().match(/^: (.*?)\s*\{#(tbl:[a-z0-9-]+)\}\s*$/);
      if (!cm) fail(`${file}:${j + 1}: table caption ": ... {#tbl:...}" missing`);
      i = j + 1;
      blocks.push({ type: 'table', header, rows: body, caption: cm[1], id: cm[2] });
      continue;
    }
    if (t.startsWith('![')) {
      const m = t.match(/^!\[(.*)\]\(([^)]+)\)\{#(fig:[a-z0-9-]+)\}$/);
      if (!m) fail(`${file}:${i + 1}: bad figure syntax`);
      const src = path.resolve(srcDir, m[2]);
      if (!fs.existsSync(src)) fail(`${file}: figure not found ${m[2]}`);
      blocks.push({ type: 'figure', caption: m[1], src, id: m[3] });
      i++; continue;
    }
    if (/^[-*] |^\d+\. /.test(t)) fail(`${file}:${i + 1}: lists are not allowed by FORMAT.md`);
    const para = [];
    while (i < lines.length && lines[i].trim() !== '' && !parseHeading(lines[i]) && !/^(\$\$|```|\||!\[)/.test(lines[i].trim())) {
      para.push(lines[i].trim()); i++;
    }
    blocks.push({ type: 'para', text: para.join(' ') });
  }
  return { file, title: first.text, id: first.id, blocks };
}

// ---------- inline parsing ----------

const INLINE_RE = new RegExp([
  '`([^`]+)`',                                        // 1 code
  '\\*\\*(.+?)\\*\\*',                                // 2 bold
  '\\[(@[^\\]]+)\\]',                                 // 3 citation group
  '@((?:sec|fig|tbl|eq):[a-z0-9]+(?:-[a-z0-9]+)*)',  // 4 cross-ref
  '«([A-Za-z][^»]*)»',                                // 5 latin quote
  '\\(([A-Za-z][^()]*)\\)',                           // 6 parenthesised english
  '(?<![\\w.])([A-Za-z_]+=[A-Za-z0-9_.]*[A-Za-z0-9_])', // 7 setting token, e.g. k=8
].join('|'), 'gu');

export function makeInlineParser(doc) {
  const citeOrder = doc.citeOrder;
  const refsById = doc.refsById;
  const parse = (text, opts = {}) => {
    const out = [];
    let last = 0;
    INLINE_RE.lastIndex = 0;
    const re = new RegExp(INLINE_RE.source, 'gu');
    let m;
    while ((m = re.exec(text))) {
      if (m.index > last) out.push({ t: 'text', s: text.slice(last, m.index) });
      if (m[1] !== undefined) out.push({ t: 'code', s: m[1] });
      else if (m[2] !== undefined) out.push({ t: 'bold', c: parse(m[2], opts) });
      else if (m[3] !== undefined) {
        if (opts.noCite) { /* dropped in lists */ }
        else out.push(citation(m[3]));
      } else if (m[4] !== undefined) out.push(crossref(m[4]));
      else if (m[5] !== undefined) out.push({ t: 'quote', s: m[5] });
      else if (m[6] !== undefined) out.push({ t: 'en', c: parse(m[6], opts) });
      else if (m[7] !== undefined) out.push({ t: 'kv', s: m[7] });
      last = re.lastIndex;
    }
    if (last < text.length) out.push({ t: 'text', s: text.slice(last) });
    // trim a dangling space left before a removed citation
    if (opts.noCite) for (const tok of out) if (tok.t === 'text') tok.s = tok.s.replace(/\s+([.،؛])/g, '$1').replace(/\s+$/, '');
    return out;
  };
  const citation = (inner) => {
    const items = inner.split(';').map((p) => p.trim()).map((p) => {
      const m = p.match(/^@([A-Za-z0-9_-]+)(?:,\s*(.+))?$/);
      if (!m) fail(`bad citation item "${p}"`);
      if (!refsById.has(m[1])) fail(`undefined reference key @${m[1]}`);
      if (!citeOrder.includes(m[1])) citeOrder.push(m[1]);
      return { key: m[1], n: citeOrder.indexOf(m[1]) + 1, page: m[2] || null };
    });
    const sep = items.some((x) => x.page) ? '؛ ' : '، ';
    const label = '[' + items.map((x) => fa(x.n) + (x.page ? '، ' + x.page : '')).join(sep) + ']';
    return { t: 'cite', label, items };
  };
  const crossref = (id) => {
    const target = doc.targets.get(id);
    if (!target) fail(`undefined cross-reference @${id}`);
    return { t: 'ref', id, label: target.refLabel };
  };
  return parse;
}

// ---------- numbering ----------

export function loadDocument(srcDir) {
  const refs = JSON.parse(fs.readFileSync(path.join(srcDir, 'references.json'), 'utf8'));
  const doc = {
    chapters: FILES.map((f) => parseFile(f, srcDir)),
    refs, refsById: new Map(refs.map((r) => [r.id, r])),
    citeOrder: [], targets: new Map(), figures: [], tables: [],
  };
  let chapNo = 0;
  let autoId = 0;
  for (const ch of doc.chapters) {
    const isAppendix = ch.id === 'sec:appendix';
    ch.numbered = !UNNUMBERED.has(ch.id);
    ch.num = ch.numbered ? ++chapNo : null;
    ch.prefix = ch.numbered ? fa(ch.num) : (isAppendix ? APPENDIX_PREFIX : null);
    ch.lang = ch.id === 'sec:abstract-en' ? 'en' : 'fa';
    const reg = (id, t) => { if (doc.targets.has(id)) fail(`duplicate id ${id}`); doc.targets.set(id, t); };
    reg(ch.id, { kind: 'chapter', refLabel: ch.numbered ? `فصل ${fa(ch.num)}` : ch.title, chapter: ch });
    let s2 = 0, s3 = 0, nFig = 0, nTbl = 0, nEq = 0;
    for (const b of ch.blocks) {
      if (b.type === 'heading') {
        if (b.level === 2) { s2++; s3 = 0; } else { if (!s2) fail(`${ch.file}: ### before ##`); s3++; }
        b.num = ch.prefix ? (b.level === 2 ? `${ch.prefix}-${fa(s2)}` : `${ch.prefix}-${fa(s2)}-${fa(s3)}`) : null;
        if (!b.id) b.id = `h-${++autoId}`;
        reg(b.id, { kind: 'section', refLabel: b.num ? `بخش ${b.num}` : b.text, block: b });
      } else if (b.type === 'figure') {
        if (!ch.prefix) fail(`${ch.file}: figure in unnumbered chapter`);
        b.num = `${ch.prefix}-${fa(++nFig)}`;
        reg(b.id, { kind: 'figure', refLabel: `شکل ${b.num}` });
        doc.figures.push(b);
      } else if (b.type === 'table') {
        if (!ch.prefix) fail(`${ch.file}: table in unnumbered chapter`);
        b.num = `${ch.prefix}-${fa(++nTbl)}`;
        reg(b.id, { kind: 'table', refLabel: `جدول ${b.num}` });
        doc.tables.push(b);
      } else if (b.type === 'equation') {
        b.num = ch.prefix ? `${ch.prefix}-${fa(++nEq)}` : null;
        if (b.id) reg(b.id, { kind: 'equation', refLabel: `رابطه‌ی (${b.num})` });
      }
    }
  }
  // Inline parse in reading order so citations are numbered by first appearance.
  const parse = makeInlineParser(doc);
  doc.parseInline = parse;
  for (const ch of doc.chapters) {
    ch.titleInl = parse(ch.title);
    for (const b of ch.blocks) {
      if (b.type === 'heading') b.inl = parse(b.text);
      else if (b.type === 'para') b.inl = parse(b.text);
      else if (b.type === 'table') {
        b.captionInl = parse(b.caption);
        b.headerInl = b.header.map((c) => parse(c));
        b.rowsInl = b.rows.map((r) => r.map((c) => parse(c)));
        b.captionListInl = parse(b.caption, { noCite: true });
      } else if (b.type === 'figure') {
        b.captionInl = parse(b.caption);
        b.captionListInl = parse(b.caption, { noCite: true });
      }
    }
  }
  doc.bibliography = doc.citeOrder.map((k, i) => ({ n: i + 1, ref: doc.refsById.get(k) }));
  const unused = refs.filter((r) => !doc.citeOrder.includes(r.id)).map((r) => r.id);
  doc.unusedRefs = unused;
  return doc;
}

// ---------- IEEE formatting (returns segments: {s, i?}) ----------

function authorList(authors) {
  const names = authors.map((a) => (a.given ? `${a.given} ${a.family}` : a.family));
  if (names.length > 6) return `${names[0]} et al.`;
  if (names.length === 1) return names[0];
  if (names.length === 2) return `${names[0]} and ${names[1]}`;
  return names.slice(0, -1).join(', ') + ', and ' + names[names.length - 1];
}
const ordinal = (n) => { n = Number(n); const s = ['th', 'st', 'nd', 'rd']; const v = n % 100; return n + (s[(v - 20) % 10] || s[v] || s[0]); };

export function ieee(ref) {
  const seg = [];
  const year = ref.issued?.['date-parts']?.[0]?.[0];
  const pages = ref.page ? (/[–-]/.test(ref.page) ? `pp. ${ref.page}` : `p. ${ref.page}`) : null;
  seg.push({ s: authorList(ref.author) + ', ' });
  if (ref.type === 'book') {
    seg.push({ s: ref.title, i: true });
    let tail = ', ';
    if (ref.edition) tail += `${ordinal(ref.edition)} ed. `;
    if (ref['publisher-place']) tail += `${ref['publisher-place']}: `;
    if (ref.publisher) tail += `${ref.publisher}, `;
    tail += `${year}`;
    seg.push({ s: tail });
  } else {
    seg.push({ s: `“${ref.title},” ` });
    if (ref.type === 'paper-conference') seg.push({ s: 'in ' });
    seg.push({ s: ref['container-title'], i: true });
    const parts = [];
    if (ref.type === 'paper-conference') {
      parts.push(String(year));
      if (pages) parts.push(pages);
    } else {
      if (ref.volume) parts.push(`vol. ${ref.volume}`);
      if (ref.issue) parts.push(`no. ${ref.issue}`);
      if (pages) parts.push(pages);
      if (ref.number) parts.push(`Art. no. ${ref.number}`);
      parts.push(String(year));
    }
    seg.push({ s: ', ' + parts.join(', ') });
  }
  if (ref.DOI) seg.push({ s: `, doi: ${ref.DOI}.` });
  else if (ref.URL) seg.push({ s: `. [Online]. Available: ${ref.URL}` });
  else seg.push({ s: '.' });
  return seg;
}

export { BuildError };
