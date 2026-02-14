import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'FAQ - Winter Olympics 2026 TV Schedule | Watch Olympics 2026',
  description: 'Frequently asked questions about watching the 2026 Winter Olympics. Find out how to watch on NBC, Peacock, USA Network, event times, and more.',
  openGraph: {
    title: 'FAQ - Winter Olympics 2026 TV Schedule',
    description: 'Frequently asked questions about watching the 2026 Winter Olympics on NBC and Peacock.',
    url: 'https://watcholympics2026.com/faq',
  },
}

export default function FaqLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}
