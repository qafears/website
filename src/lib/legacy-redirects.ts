/**
 * Old Wix URL -> the page on this site that now covers it.
 *
 * quentinfears.com used to be a Wix site whose portfolio lived on its own
 * category pages. The domain now points at this site, which has six pages, so
 * each of those old URLs is a 404 while still sitting in Google's index. See
 * src/pages/[legacy].astro for how the stubs are rendered.
 *
 * Routes taken from the old site's structure as recorded in
 * tools/fetch_site_images.py (KNOWN_ROUTES).
 */
export const LEGACY_REDIRECTS: Record<string, string> = {
  celebrity: 'work',
  'celebrity-men': 'work',
  'red-carpet': 'work',
  editorial: 'work',
  'editorial-men': 'work',
  commercial: 'work',
  production: 'work',
  services: 'work',
  'tv-correspondent': 'speak',
  'about-me': 'about',
  press: 'about',
  testimonials: 'about',
  'press-testimonials': 'about',
};
