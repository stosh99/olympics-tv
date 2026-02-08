"use client"

import { useState, useEffect, useRef } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Button } from "@/components/ui/button"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { NETWORK_COLORS, getSportColor } from "@/lib/schedule-data"
import {
  fetchTvSchedule,
  flattenBroadcasts,
  isLiveNow,
  getDisciplineFromBroadcast,
  formatDateParam,
  type Broadcast,
} from "@/lib/api"

function NetworkBadge({ network }: { network: string }) {
  const colors = NETWORK_COLORS[network] || { bg: "bg-gray-500", text: "text-white" }
  return (
    <span className={`px-2 py-1 text-xs font-bold rounded ${colors.bg} ${colors.text}`}>
      {network}
    </span>
  )
}

function SportBadge({ sport }: { sport: string }) {
  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded-full text-white ${getSportColor(sport)}`}>
      {sport}
    </span>
  )
}

function CountdownTimer({ endTime }: { endTime: string }) {
  const [timeLeft, setTimeLeft] = useState("")

  useEffect(() => {
    const updateTimer = () => {
      const now = new Date()
      const end = new Date(endTime)
      const diff = end.getTime() - now.getTime()
      if (diff <= 0) {
        setTimeLeft("Ending soon")
        return
      }
      const hours = Math.floor(diff / (1000 * 60 * 60))
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
      const seconds = Math.floor((diff % (1000 * 60)) / 1000)
      setTimeLeft(
        hours > 0
          ? `${hours}h ${minutes}m remaining`
          : `${minutes}:${seconds.toString().padStart(2, "0")} remaining`
      )
    }

    updateTimer()
    const interval = setInterval(updateTimer, 1000)
    return () => clearInterval(interval)
  }, [endTime])

  return <span className="text-sm text-muted-foreground">{timeLeft}</span>
}

export default function WhatsOnNow() {
  const [liveBroadcasts, setLiveBroadcasts] = useState<
    Array<Broadcast & { network_name: string }>
  >([])
  const [loading, setLoading] = useState(true)
  const scrollContainerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    async function loadLive() {
      try {
        const today = formatDateParam(new Date())
        const data = await fetchTvSchedule(today)
        const all = flattenBroadcasts(data.networks)
        const live = all.filter((b) => isLiveNow(b))
        setLiveBroadcasts(live)
      } catch (err) {
        console.error("Failed to load live broadcasts:", err)
      } finally {
        setLoading(false)
      }
    }

    loadLive()
    // Refresh every 60 seconds
    const interval = setInterval(loadLive, 60000)
    return () => clearInterval(interval)
  }, [])

  const scroll = (direction: "left" | "right") => {
    if (scrollContainerRef.current) {
      const scrollAmount = 320 // Scroll by approximately one card width
      const { scrollLeft } = scrollContainerRef.current
      scrollContainerRef.current.scrollTo({
        left: direction === "left" ? scrollLeft - scrollAmount : scrollLeft + scrollAmount,
        behavior: "smooth",
      })
    }
  }

  if (loading) {
    return (
      <section>
        <div className="flex items-center gap-2 mb-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500"></span>
          </span>
          <h2 className="text-lg font-semibold text-foreground">What&apos;s On Now</h2>
        </div>
        <p className="text-sm text-muted-foreground">Loading...</p>
      </section>
    )
  }

  if (liveBroadcasts.length === 0) {
    return (
      <section>
        <div className="flex items-center gap-2 mb-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-gray-400"></span>
          </span>
          <h2 className="text-lg font-semibold text-foreground">What&apos;s On Now</h2>
        </div>
        <p className="text-sm text-muted-foreground">No live broadcasts at the moment.</p>
      </section>
    )
  }

  return (
    <section>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500"></span>
          </span>
          <h2 className="text-lg font-semibold text-foreground">What&apos;s On Now</h2>
        </div>
        <div className="flex gap-1.5">
          {/* Left scroll button */}
          <Button
            variant="outline"
            size="icon"
            className="h-7 w-7 bg-transparent"
            onClick={() => scroll("left")}
            aria-label="Scroll left"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>

          {/* Right scroll button */}
          <Button
            variant="outline"
            size="icon"
            className="h-7 w-7 bg-transparent"
            onClick={() => scroll("right")}
            aria-label="Scroll right"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div
        ref={scrollContainerRef}
        className="flex gap-3 overflow-x-auto scrollbar-hide scroll-smooth"
        style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}
      >
          {liveBroadcasts.map((broadcast) => {
            const discipline = getDisciplineFromBroadcast(broadcast)
            return (
              <Card
                key={broadcast.drupal_id}
                className="overflow-hidden hover:shadow-lg transition-shadow cursor-pointer bg-card border-border flex-shrink-0"
                style={{ width: "320px" }}
              >
                <CardContent className="p-2">
                  <div className="flex items-center justify-between mb-1">
                    <NetworkBadge network={broadcast.network_name} />
                    <Badge variant="destructive" className="text-xs font-semibold animate-pulse">
                      LIVE
                    </Badge>
                  </div>

                  <h3 className="font-semibold text-foreground mb-1 line-clamp-1 text-sm">
                    {broadcast.short_title || broadcast.title}
                  </h3>

                  <div className="flex items-center justify-between gap-1">
                    <SportBadge sport={discipline} />
                    <CountdownTimer endTime={broadcast.end_time} />
                    {broadcast.summary && (
                      <Popover>
                        <PopoverTrigger asChild>
                          <button
                            type="button"
                            className="px-2 py-0.5 text-xs font-medium rounded-full bg-secondary text-secondary-foreground hover:bg-secondary/80 transition-colors"
                          >
                            Preview
                          </button>
                        </PopoverTrigger>
                        <PopoverContent className="w-72 p-3" align="start">
                          <div className="space-y-2">
                            <div className="flex items-center gap-2">
                              <SportBadge sport={discipline} />
                            </div>
                            <p className="text-sm text-foreground leading-relaxed">
                              {broadcast.summary}
                            </p>
                            {broadcast.video_url && (
                              <a
                                href={broadcast.video_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs text-blue-600 hover:underline block"
                              >
                                Watch Stream →
                              </a>
                            )}
                          </div>
                        </PopoverContent>
                      </Popover>
                    )}
                  </div>
                </CardContent>
              </Card>
            )
          })}
      </div>
    </section>
  )
}
