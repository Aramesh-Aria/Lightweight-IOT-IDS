// Builds the one-month study roadmap.
//   node scripts/build-roadmap.mjs          -> deliverables/study-roadmap.pdf
//   node scripts/build-roadmap.mjs --png    -> also writes one PNG per page to build/roadmap-png/ for review
// Source: roadmap/roadmap.html, styled by guide/guide.css plus roadmap/roadmap.css.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import puppeteer from 'puppeteer-core';
import { cleanPdfMetadata } from './build-pdf.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const buildDir = path.join(root, 'build');
const outDir = path.resolve(root, '..', 'deliverables');
const CHROME = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const cfg = JSON.parse(fs.readFileSync(path.join(root, 'config', 'report.json'), 'utf8'));

async function main() {
  const htmlPath = path.join(root, 'roadmap', 'roadmap.html');
  const browser = await puppeteer.launch({ executablePath: CHROME, args: ['--font-render-hinting=none'] });
  let bytes;
  try {
    const page = await browser.newPage();
    await page.goto('file://' + htmlPath, { waitUntil: 'networkidle0' });
    await page.evaluate(async () => { await document.fonts.ready; });
    bytes = Buffer.from(await page.pdf({ preferCSSPageSize: true, printBackground: true, displayHeaderFooter: false, outline: false, tagged: false }));
  } finally {
    await browser.close();
  }
  fs.mkdirSync(outDir, { recursive: true });
  const out = path.join(outDir, 'study-roadmap.pdf');
  fs.writeFileSync(out, await cleanPdfMetadata(bytes, { title: 'برنامه‌ی مطالعه · آمادگی ارائه‌ی سمینار', author: cfg.author }));
  console.log(`-> ${path.relative(path.resolve(root, '..'), out)}`);
  if (process.argv.includes('--png')) {
    const pngDir = path.join(buildDir, 'roadmap-png');
    fs.rmSync(pngDir, { recursive: true, force: true });
    fs.mkdirSync(pngDir, { recursive: true });
    execFileSync('pdftoppm', ['-r', '80', '-png', out, path.join(pngDir, 'page')]);
    console.log(`png: ${fs.readdirSync(pngDir).length} pages -> ${path.relative(root, pngDir)}/`);
  }
}

main().catch((e) => { console.error(e.message); process.exit(1); });
