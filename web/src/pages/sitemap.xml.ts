import type { APIRoute } from 'astro'
import { HANDBUCH_NAV } from '../data/handbuch-nav'

const SITE = 'https://rechnungsfee.app'

const staticPages = [
  { url: '/',            priority: '1.0', changefreq: 'weekly'  },
  { url: '/funktionen', priority: '0.8', changefreq: 'monthly' },
  { url: '/download',   priority: '0.9', changefreq: 'weekly'  },
  { url: '/changelog',  priority: '0.7', changefreq: 'weekly'  },
  { url: '/handbuch',   priority: '0.8', changefreq: 'weekly'  },
  { url: '/spenden',    priority: '0.5', changefreq: 'monthly' },
  { url: '/impressum',  priority: '0.2', changefreq: 'yearly'  },
  { url: '/datenschutz',priority: '0.2', changefreq: 'yearly'  },
]

const handbuchPages = HANDBUCH_NAV
  .flatMap(g => g.items)
  .map(item => ({ url: `/handbuch/${item.slug}`, priority: '0.6', changefreq: 'monthly' }))

const allPages = [...staticPages, ...handbuchPages]

export const GET: APIRoute = () => {
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${allPages.map(p => `  <url>
    <loc>${SITE}${p.url}</loc>
    <changefreq>${p.changefreq}</changefreq>
    <priority>${p.priority}</priority>
  </url>`).join('\n')}
</urlset>`

  return new Response(xml, {
    headers: { 'Content-Type': 'application/xml; charset=utf-8' },
  })
}
