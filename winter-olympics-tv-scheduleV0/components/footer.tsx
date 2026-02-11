import Link from "next/link"
import { ExternalLink } from "lucide-react"

export default function Footer() {
  return (
    <footer className="border-t border-border bg-card mt-8">
      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Official Links */}
        <div className="flex flex-wrap justify-center gap-6 mb-4">
          <Link
            href="/faq"
            className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline font-medium"
          >
            FAQ
          </Link>
          <a
            href="https://www.milanocortina2026.olympics.com"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline"
          >
            <ExternalLink className="h-4 w-4" />
            Official Milano Cortina 2026 Website
          </a>
          <a
            href="https://www.nbcolympics.com"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline"
          >
            <ExternalLink className="h-4 w-4" />
            NBC Olympics
          </a>
        </div>

        {/* Disclaimer */}
        <div className="text-center">
          <p className="text-xs text-muted-foreground leading-relaxed max-w-2xl mx-auto">
            <strong>Disclaimer:</strong> This website is for personal use only and is not affiliated with, 
            endorsed by, or connected to the Milano Cortina 2026 Olympic Winter Games, the International 
            Olympic Committee (IOC), NBC Universal, or any of their affiliated entities. All trademarks, 
            logos, and brand names are the property of their respective owners.
          </p>
        </div>
      </div>
    </footer>
  )
}
