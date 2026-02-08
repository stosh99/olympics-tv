"use client"

import { useState, useEffect } from "react"

const OlympicRings = () => (
  <svg width="120" height="60" viewBox="0 0 100 48" className="shrink-0">
    <circle cx="20" cy="18" r="10" fill="none" stroke="#0085C7" strokeWidth="3" />
    <circle cx="50" cy="18" r="10" fill="none" stroke="#000000" strokeWidth="3" />
    <circle cx="80" cy="18" r="10" fill="none" stroke="#DF0024" strokeWidth="3" />
    <circle cx="35" cy="30" r="10" fill="none" stroke="#F4C300" strokeWidth="3" />
    <circle cx="65" cy="30" r="10" fill="none" stroke="#009F3D" strokeWidth="3" />
  </svg>
)

export default function Header() {
  const [mounted, setMounted] = useState(false)
  const [currentTime, setCurrentTime] = useState(new Date())

  useEffect(() => {
    setMounted(true)
    setCurrentTime(new Date())
    const timer = setInterval(() => {
      setCurrentTime(new Date())
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  const formatDate = (date: Date) => {
    return date.toLocaleDateString("en-US", {
      weekday: "short",
      month: "short",
      day: "numeric",
      year: "numeric",
    })
  }

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      second: "2-digit",
      hour12: true,
    })
  }

  return (
    <header className="sticky top-0 z-50 bg-card border-b border-border shadow-sm">
      <div className="relative flex items-center justify-center px-4 py-3">
        {/* Center Zone: Title + Dates */}
        <div className="flex flex-col items-center">
          <h1 className="text-2xl md:text-3xl font-bold text-foreground leading-tight">
            Winter Olympics 2026
          </h1>
          <p className="text-sm md:text-base text-muted-foreground">
            February 6 - 22, 2026
          </p>
        </div>

        {/* Left Zone: Olympic Rings + Milano Cortina */}
        <div className="absolute left-4 flex items-center gap-3 shrink-0">
          <OlympicRings />
          <p className="text-sm tracking-[0.3em] text-muted-foreground font-medium">
            MILANO CORTINA
          </p>
        </div>

        {/* Right Zone: Current Date and Time */}
        <div className="absolute right-4 flex flex-col items-end text-right shrink-0">
          {mounted && (
            <>
              <p className="text-xs text-muted-foreground">{formatDate(currentTime)}</p>
              <p className="text-sm font-semibold text-foreground tabular-nums">
                {formatTime(currentTime)}
              </p>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
