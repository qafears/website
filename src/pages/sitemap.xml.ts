/**
 * sitemap.xml, generated at build time.
 *
 * Two jobs:
 *   1. List the six pages (what the hand-written public/sitemap.xml used to do).
 *   2. Declare every photo each page shows, as <image:image> entries, so Google
 *      Images can find them.
 *
 * (2) is the reason this is generated rather than hand-written. Most of the
 * portfolio photos are only ever inserted into the DOM by the lightbox, from
 * the JSON in <script id="gallery-data">, so a crawler that does not open a
 * gallery never sees them. An image sitemap is Google's supported way to
 * declare exactly those images. Reading the same content/*.yaml the pages read
 * means the list cannot drift when photos are added or trimmed.
 */
import type { APIRoute } from 'astro';
import { reader, SITE_ORIGIN } from '../lib/content';

const IMG_RE = /^assets\/img\/[\w./-]+\.(?:jpe?g|png)$/i;

/** Every `assets/img/...` path anywhere in a content singleton, in order. */
function collectImages(node: unknown, out: string[] = []): string[] {
  if (typeof node === 'string') {
    if (IMG_RE.test(node) && !out.includes(node)) out.push(node);
  } else if (Array.isArray(node)) {
    for (const item of node) collectImages(item, out);
  } else if (node && typeof node === 'object') {
    for (const value of Object.values(node)) collectImages(value, out);
  }
  return out;
}

// pagePath '' is the home page. `extra` pulls in images a page presents but
// does not own: the work page renders the galleries singleton via the lightbox.
const PAGES = [
  { path: '', singleton: 'home', changefreq: 'monthly', priority: '1.0' },
  { path: 'work', singleton: 'work', changefreq: 'monthly', priority: '0.8', extra: 'galleries' },
  { path: 'archives', singleton: 'archives', changefreq: 'monthly', priority: '0.9' },
  { path: 'ideas', singleton: 'ideas', changefreq: 'monthly', priority: '0.8' },
  { path: 'speak', singleton: 'speak', changefreq: 'monthly', priority: '0.8' },
  { path: 'about', singleton: 'about', changefreq: 'monthly', priority: '0.7' },
  { path: 'contact', singleton: 'contact', changefreq: 'yearly', priority: '0.6' },
] as const;

const esc = (s: string) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

export const GET: APIRoute = async () => {
  const lastmod = new Date().toISOString().slice(0, 10);
  const singletons = reader.singletons as Record<string, { read(): Promise<unknown> }>;

  const entries = await Promise.all(
    PAGES.map(async (page) => {
      const images = collectImages(await singletons[page.singleton].read());
      if ('extra' in page && page.extra) {
        collectImages(await singletons[page.extra].read(), images);
      }
      const loc = page.path === '' ? `${SITE_ORIGIN}/` : `${SITE_ORIGIN}/${page.path}`;
      const imageTags = images
        .map((src) => `    <image:image>\n      <image:loc>${esc(`${SITE_ORIGIN}/${src}`)}</image:loc>\n    </image:image>`)
        .join('\n');
      return [
        '  <url>',
        `    <loc>${loc}</loc>`,
        `    <lastmod>${lastmod}</lastmod>`,
        `    <changefreq>${page.changefreq}</changefreq>`,
        `    <priority>${page.priority}</priority>`,
        imageTags,
        '  </url>',
      ]
        .filter(Boolean)
        .join('\n');
    })
  );

  const xml = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
    '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">',
    ...entries,
    '</urlset>',
    '',
  ].join('\n');

  return new Response(xml, { headers: { 'Content-Type': 'application/xml; charset=utf-8' } });
};
