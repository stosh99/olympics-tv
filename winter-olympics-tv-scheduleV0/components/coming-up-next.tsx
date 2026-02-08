"use client"

import { useState, useEffect, useRef } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { ChevronLeft, ChevronRight, Clock } from "lucide-react"
import { NETWORK_COLORS, getSportColor } from "@/lib/schedule-data"
import {
  fetchTvSchedule,
  flattenBroadcasts,
  isUpcoming,
  getDisciplineFromBroadcast,
  formatDateParam,
  type Broadcast,
} from "@/lib/api"

function NetworkBadge({ network }: { network: string }) {
  const colors = NETWORK_COLORS[network] || { bg: "bg-gray-500", text: "text-white" }
  return (
    <span className={`px-2 py-0.5 text-xs font-bold rounded ${colors.bg} ${colors.text}`}>
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

function formatTime(isoString: string): string {
  return new Date(isoString).toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  })
}

export default function ComingUpNext() {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [upcoming, setUpcoming] = useState<Array<Broadcast & { network_name: string }>>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadUpcoming() {
      try {
        const today = formatDateParam(new Date())
        const data = await fetchTvSchedule(today)
        const all = flattenBroadcasts(data.networks)
        const next = all.filter((b) => isUpcoming(b) && !b.is_replay).slice(0, 12)
        setUpcoming(next)
      } catch (err) {
        console.error("Failed to load upcoming:", err)
      } finally {
        setLoading(false)
      }
    }

    loadUpcoming()
    const interval = setInterval(loadUpcoming, 120000) // refresh every 2 min
    return () => clearInterval(interval)
  }, [])

  const scroll = (direction: "left" | "right") => {
    if (scrollRef.current) {
      scrollRef.current.scrollBy({
        left: direction === "left" ? -300 : 300,
        behavior: "smooth",
      })
    }
  }

  if (loading) {
    return (
      <section>
        <h2 className="text-lg font-semibold text-foreground mb-2">Coming Up Next</h2>
        <p className="text-sm text-muted-foreground">Loading...</p>
      </section>
    )
  }

  if (upcoming.length === 0) {
    return (
      <section>
        <h2 className="text-lg font-semibold text-foreground mb-2">Coming Up Next</h2>
        <p className="text-sm text-muted-foreground">No upcoming broadcasts today.</p>
      </section>
    )
  }

  return (
    <section>
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-lg font-semibold text-foreground">Coming Up Next</h2>
        <div className="flex gap-1.5">
          <Button
            variant="outline"
            size="icon"
            className="h-7 w-7 bg-transparent"
            onClick={() => scroll("left")}
            aria-label="Scroll left"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
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
        ref={scrollRef}
        className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide scroll-smooth"
        style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}
      >
        {upcoming.map((broadcast) => {
          const discipline = getDisciplineFromBroadcast(broadcast)
          return (
            <Card
              key={broadcast.drupal_id}
              className="flex-shrink-0 w-56 hover:shadow-md transition-shadow cursor-pointer bg-card border-border"
            >
              <CardContent className="p-2">
                <div className="flex items-center justify-between mb-1">
                  <NetworkBadge network={broadcast.network_name} />
                  <div className="flex items-center gap-1 text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    <span className="text-xs">{formatTime(broadcast.start_time)}</span>
                  </div>
                </div>

                <h3 className="font-medium text-foreground mb-1 text-sm line-clamp-1">
                  {broadcast.short_title || broadcast.title}
                </h3>

                <div className="flex items-center justify-between gap-1">
                  <SportBadge sport={discipline} />
                  {broadcast.is_medal_session && (
                    <span className="text-xs">🏅</span>
                  )}
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
                      <PopoverContent className="w-72 p-3" align="end">
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
