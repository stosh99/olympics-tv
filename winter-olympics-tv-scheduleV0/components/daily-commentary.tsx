"use client"

import { useState, useEffect } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ChevronDown, ChevronUp, Medal, Eye, Calendar } from "lucide-react"
import { SPORT_COLORS } from "@/lib/schedule-data"
import { fetchCommentary, CommentaryItem, ResultSummary } from "@/lib/api"

function SportBadge({ sport }: { sport: string }) {
  const bgColor = SPORT_COLORS[sport] || "bg-gray-500"
  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded-full text-white ${bgColor}`}>
      {sport}
    </span>
  )
}

function TypeBadge({ type }: { type: string }) {
  const isPreview = type === "pre_event"
  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
      isPreview ? "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300"
                : "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
    }`}>
      {isPreview ? "Preview" : "Recap"}
    </span>
  )
}

function MedalBadge({ type }: { type: string }) {
  const emoji = type === "ME_GOLD" ? "🥇" : type === "ME_SILVER" ? "🥈" : "🥉"
  return <span className="text-sm">{emoji}</span>
}

function formatEventDate(dateStr: string | null) {
  if (!dateStr) return ""
  const d = new Date(dateStr)
  return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" })
}

function formatEventTime(dateStr: string | null) {
  if (!dateStr) return ""
  const d = new Date(dateStr)
  return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })
}

function ResultsDisplay({ results }: { results: ResultSummary[] }) {
  if (!results || results.length === 0) return null

  // Head-to-head (has W/L/T)
  const hasWLT = results.some(r => r.wlt)
  if (hasWLT) {
    const winner = results.find(r => r.wlt === "W")
    const loser = results.find(r => r.wlt === "L")
    if (winner && loser) {
      return (
        <div className="text-xs text-muted-foreground mt-2 space-y-0.5">
          <div className="font-medium text-foreground">
            {winner.name} ({winner.noc}) {winner.mark ? `· ${winner.mark}` : ""}
          </div>
          <div>def. {loser.name} ({loser.noc}) {loser.mark ? `· ${loser.mark}` : ""}</div>
        </div>
      )
    }
  }

  // Medal results
  const medalists = results.filter(r => r.medal_type)
  if (medalists.length > 0) {
    return (
      <div className="text-xs mt-2 space-y-0.5">
        {medalists.map((r, i) => (
          <div key={i} className="flex items-center gap-1.5">
            <MedalBadge type={r.medal_type!} />
            <span className="text-foreground font-medium">{r.name}</span>
            <span className="text-muted-foreground">({r.noc})</span>
            {r.mark && <span className="text-muted-foreground">· {r.mark}</span>}
          </div>
        ))}
      </div>
    )
  }

  return null
}

function CommentaryCard({ item }: { item: CommentaryItem }) {
  const [expanded, setExpanded] = useState(false)
  const isPreview = item.commentary_type === "pre_event"

  return (
    <Card className={`overflow-hidden hover:shadow-md transition-shadow bg-card border-border ${
      item.medal_flag ? "ring-1 ring-amber-400/50" : ""
    }`}>
      <CardContent className="p-4">
        {/* Header row: sport + type + medal indicator */}
        <div className="flex items-center gap-2 mb-2 flex-wrap">
          <SportBadge sport={item.discipline} />
          <TypeBadge type={item.commentary_type} />
          {item.medal_flag && <Medal className="h-3.5 w-3.5 text-amber-500" />}
        </div>

        {/* Event name */}
        <h3 className="font-semibold text-foreground text-sm leading-snug mb-1">
          {item.event_name}
        </h3>

        {/* Date/time */}
        {item.event_date && (
          <div className="flex items-center gap-1 text-xs text-muted-foreground mb-2">
            <Calendar className="h-3 w-3" />
            <span>{formatEventDate(item.event_date)} · {formatEventTime(item.event_date)}</span>
          </div>
        )}

        {/* Results (post-event only) */}
        {!isPreview && <ResultsDisplay results={item.results} />}

        {/* First paragraph */}
        <p className="text-sm text-muted-foreground mt-2 leading-relaxed">
          {item.first_paragraph}
        </p>

        {/* Expand/collapse full content */}
        {item.full_content !== item.first_paragraph && (
          <div className="mt-2">
            <Button
              variant="ghost"
              size="sm"
              className="px-0 text-xs text-muted-foreground hover:text-foreground"
              onClick={() => setExpanded(!expanded)}
            >
              {expanded ? "Show less" : "Read more"}
              {expanded ? <ChevronUp className="h-3 w-3 ml-1" /> : <ChevronDown className="h-3 w-3 ml-1" />}
            </Button>
            {expanded && (
              <div className="mt-2 text-sm text-muted-foreground leading-relaxed whitespace-pre-line">
                {item.full_content.slice(item.first_paragraph.length).trim()}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function CommentaryColumn({ title, items, emptyMessage }: {
  title: string
  items: CommentaryItem[]
  emptyMessage: string
}) {
  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-foreground uppercase tracking-wide">
        {title}
        <span className="ml-2 text-xs font-normal text-muted-foreground normal-case">
          ({items.length})
        </span>
      </h3>
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground italic">{emptyMessage}</p>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <CommentaryCard key={item.event_unit_code} item={item} />
          ))}
        </div>
      )}
    </div>
  )
}

export default function DailyCommentary() {
  const [data, setData] = useState<{
    previews: CommentaryItem[]
    today_recaps: CommentaryItem[]
    previous_recaps: CommentaryItem[]
  } | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchCommentary()
      .then(setData)
      .catch((e) => setError(e.message))
  }, [])

  if (error) {
    return (
      <section className="pb-12">
        <h2 className="text-xl font-semibold text-foreground mb-4">Commentary</h2>
        <p className="text-sm text-muted-foreground">Unable to load commentary.</p>
      </section>
    )
  }

  if (!data) {
    return (
      <section className="pb-12">
        <h2 className="text-xl font-semibold text-foreground mb-4">Commentary</h2>
        <p className="text-sm text-muted-foreground">Loading...</p>
      </section>
    )
  }

  const hasContent = data.previews.length + data.today_recaps.length + data.previous_recaps.length > 0

  if (!hasContent) return null

  return (
    <section className="pb-12">
      <h2 className="text-xl font-semibold text-foreground mb-4">Commentary</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <CommentaryColumn
          title="Coming Up"
          items={data.previews}
          emptyMessage="No previews yet"
        />
        <CommentaryColumn
          title="Today's Recaps"
          items={data.today_recaps}
          emptyMessage="No recaps yet for today"
        />
        <CommentaryColumn
          title="Recent"
          items={data.previous_recaps}
          emptyMessage="No recent recaps"
        />
      </div>
    </section>
  )
}
