import React from "react"
import type { Metadata } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import { Analytics } from '@vercel/analytics/next'
import './globals.css'

const _geist = Geist({ subsets: ["latin"] });
const _geistMono = Geist_Mono({ subsets: ["latin"] });

export const metadata: Metadata = {
  metadataBase: new URL('https://watcholympics2026.com'),
  title: 'Winter Olympics 2026 Milano Cortina - TV Schedule',
  description: 'Complete TV schedule for the 2026 Winter Olympics in Milano Cortina. Find live events, replays, and commentary across NBC, USA, CNBC, and Peacock.',
  keywords: ['Winter Olympics 2026', 'Milano Cortina', 'Olympic TV Schedule', 'NBC Olympics', 'Peacock Olympics', 'Olympic medals', 'Winter Games 2026'],
  icons: {
    icon: [
      {
        url: '/icon-light-32x32.png',
        media: '(prefers-color-scheme: light)',
      },
      {
        url: '/icon-dark-32x32.png',
        media: '(prefers-color-scheme: dark)',
      },
      {
        url: '/icon.svg',
        type: 'image/svg+xml',
      },
    ],
    apple: '/apple-icon.png',
  },
  openGraph: {
    title: 'Winter Olympics 2026 Milano Cortina - TV Schedule & Results',
    description: 'Complete NBC TV schedule for the 2026 Winter Olympics. Live events, replays, and AI commentary across NBC, USA, CNBC, and Peacock.',
    url: 'https://watcholympics2026.com',
    siteName: 'Watch Olympics 2026',
    locale: 'en_US',
    type: 'website',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'Winter Olympics 2026 Milano Cortina TV Schedule',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Winter Olympics 2026 Milano Cortina - TV Schedule & Results',
    description: 'Complete NBC TV schedule for the 2026 Winter Olympics. Live events, replays, and AI commentary across NBC, USA, CNBC, and Peacock.',
    images: ['/og-image.png'],
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  const jsonLd = [
    {
      "@context": "https://schema.org",
      "@type": "WebSite",
      "name": "Watch Olympics 2026",
      "url": "https://watcholympics2026.com",
      "description": "Complete NBC TV schedule for the 2026 Winter Olympics in Milano Cortina. Live events, replays, and AI commentary.",
      "potentialAction": {
        "@type": "SearchAction",
        "target": "https://watcholympics2026.com?q={search_term_string}",
        "query-input": "required name=search_term_string"
      }
    },
    {
      "@context": "https://schema.org",
      "@type": "SportsEvent",
      "name": "2026 Winter Olympics",
      "description": "The XXV Olympic Winter Games held across Milano, Cortina d'Ampezzo, Bormio, Livigno, Predazzo, Tesero, and Anterselva in Italy.",
      "startDate": "2026-02-06",
      "endDate": "2026-02-22",
      "eventStatus": "https://schema.org/EventScheduled",
      "eventAttendanceMode": "https://schema.org/MixedEventAttendanceMode",
      "location": {
        "@type": "Place",
        "name": "Milano Cortina",
        "address": {
          "@type": "PostalAddress",
          "addressCountry": "IT",
          "addressRegion": "Lombardy, Veneto, Trentino-Alto Adige"
        }
      },
      "organizer": {
        "@type": "Organization",
        "name": "International Olympic Committee",
        "url": "https://www.olympics.com"
      },
      "broadcaster": {
        "@type": "Organization",
        "name": "NBCUniversal",
        "url": "https://www.nbcolympics.com"
      }
    }
  ];

  return (
    <html lang="en">
      <head>
        <script data-goatcounter="https://stosh99.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
      </head>
      <body className={`font-sans antialiased`}>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
        {children}
        <Analytics />
      </body>
    </html>
  )
}
