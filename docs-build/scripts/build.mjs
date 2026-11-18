// npm run report: rebuilds deliverables/seminar-report.pdf, seminar-report-print.pdf and seminar-report.docx.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadDocument } from './parse.mjs';
import { stats } from './render-html.mjs';
import { buildPdfs } from './build-pdf.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');              // docs-build/
const srcDir = path.join(root, 'report');
const buildDir = path.join(root, 'build');
const outDir = path.resolve(root, '..', 'deliverables');
const cfg = JSON.parse(fs.readFileSync(path.join(root, 'config', 'report.json'), 'utf8'));
const log = (...a) => console.log('[report]', ...a);

const only = process.argv[2]; // optional: pdf | docx
fs.mkdirSync(buildDir, { recursive: true });
fs.mkdirSync(outDir, { recursive: true });

const doc = loadDocument(srcDir);
log(`parsed ${doc.chapters.length} files, ${doc.tables.length} tables, ${doc.figures.length} figures, ${doc.citeOrder.length} cited references`);
if (doc.unusedRefs.length) log(`references never cited (not printed): ${doc.unusedRefs.join(', ')}`);

if (!only || only === 'pdf') {
  const res = await buildPdfs({ doc, cfg, root, buildDir, outDir, log });
  if (stats.strayDigits.length) log(`converted ${stats.strayDigits.length} stray Latin digits: ${[...new Set(stats.strayDigits)].join('; ')}`);
  const pages = res.screen.pages;
  if (pages > 45 || pages < 25) log(`WARNING: ${pages} pages is outside the 25-45 range of Q54`);
  fs.writeFileSync(path.join(buildDir, 'pages.json'), JSON.stringify(Object.fromEntries(res.screen.map), null, 1));
}
if (!only || only === 'docx') {
  const { buildDocx } = await import('./build-docx.mjs');
  await buildDocx({ doc, cfg, root, buildDir, outDir, log });
}
