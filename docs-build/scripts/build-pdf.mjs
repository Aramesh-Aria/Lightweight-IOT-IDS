// Prints the report HTML with Chrome in two passes: pass 1 finds the page of every TOC/list target
// from the PDF's named destinations, pass 2 prints with those numbers and is checked against pass 1.
import fs from 'node:fs';
import path from 'node:path';
import puppeteer from 'puppeteer-core';
import { PDFDocument, PDFName, PDFDict, PDFArray, PDFString, PDFHexString } from 'pdf-lib';
import { renderHtml, fillPages, pageTargets } from './render-html.mjs';

const CHROME = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

async function printPdf(browser, htmlPath) {
  const page = await browser.newPage();
  await page.goto('file://' + htmlPath, { waitUntil: 'networkidle0' });
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all([...document.images].map((img) => (img.complete ? img.decode().catch(() => {}) : new Promise((r) => { img.onload = img.onerror = r; }))));
  });
  const bytes = await page.pdf({ preferCSSPageSize: true, printBackground: true, displayHeaderFooter: false, outline: false, tagged: false });
  await page.close();
  return Buffer.from(bytes);
}

export async function destinationPages(bytes) {
  const pdf = await PDFDocument.load(bytes);
  const pages = pdf.getPages();
  const index = new Map(pages.map((p, i) => [p.ref.objectNumber, i + 1]));
  const out = new Map();
  const add = (name, arr) => {
    if (!(arr instanceof PDFArray)) return;
    const ref = arr.get(0);
    if (ref && index.has(ref.objectNumber)) out.set(name, index.get(ref.objectNumber));
  };
  const dests = pdf.catalog.lookupMaybe(PDFName.of('Dests'), PDFDict);
  if (dests) for (const [k, v] of dests.entries()) add(k.decodeText(), pdf.context.lookup(v));
  const names = pdf.catalog.lookupMaybe(PDFName.of('Names'), PDFDict);
  const tree = names && names.lookupMaybe(PDFName.of('Dests'), PDFDict);
  const walk = (node) => {
    const kids = node.lookupMaybe(PDFName.of('Kids'), PDFArray);
    if (kids) for (let i = 0; i < kids.size(); i++) walk(kids.lookup(i, PDFDict));
    const arr = node.lookupMaybe(PDFName.of('Names'), PDFArray);
    if (arr) for (let i = 0; i < arr.size(); i += 2) {
      const n = arr.lookup(i);
      const key = n instanceof PDFString || n instanceof PDFHexString ? n.decodeText() : String(n);
      add(key, arr.lookup(i + 1));
    }
  };
  if (tree) walk(tree);
  return { map: out, count: pages.length };
}

export async function cleanPdfMetadata(bytes, { title, author }) {
  const pdf = await PDFDocument.load(bytes, { updateMetadata: false });
  const info = pdf.getInfoDict();
  for (const k of [...info.keys()]) info.delete(k);
  pdf.catalog.delete(PDFName.of('Metadata'));
  pdf.setTitle(title);
  pdf.setAuthor(author);
  pdf.setLanguage('fa-IR');
  return Buffer.from(await pdf.save({ useObjectStreams: false }));
}

export async function buildPdfs({ doc, cfg, root, buildDir, outDir, log }) {
  const browser = await puppeteer.launch({ executablePath: CHROME, args: ['--font-render-hinting=none'] });
  const results = {};
  try {
    for (const variant of ['screen', 'print']) {
      const html1 = renderHtml(doc, cfg, { root, variant });
      const htmlPath = path.join(buildDir, `report-${variant}.html`);
      fs.writeFileSync(htmlPath, html1);
      const pass1 = await destinationPages(await printPdf(browser, htmlPath));
      const targets = [...new Set(pageTargets(html1))];
      const missing = targets.filter((t) => !pass1.map.has(t));
      if (missing.length) throw new Error(`no PDF destination for: ${missing.join(', ')}`);
      const html2 = fillPages(html1, pass1.map);
      fs.writeFileSync(htmlPath, html2);
      const bytes2 = await printPdf(browser, htmlPath);
      const pass2 = await destinationPages(bytes2);
      const moved = targets.filter((t) => pass2.map.get(t) !== pass1.map.get(t));
      if (moved.length || pass2.count !== pass1.count) throw new Error(`pagination changed between passes: ${moved.join(', ')} (${pass1.count} -> ${pass2.count} pages)`);
      const name = variant === 'screen' ? 'seminar-report.pdf' : 'seminar-report-print.pdf';
      const clean = await cleanPdfMetadata(bytes2, { title: cfg.title, author: cfg.author });
      fs.writeFileSync(path.join(outDir, name), clean);
      results[variant] = { pages: pass2.count, map: pass2.map, file: name };
      log(`${name}: ${pass2.count} pages, ${targets.length} TOC/list targets verified`);
    }
  } finally {
    await browser.close();
  }
  return results;
}
