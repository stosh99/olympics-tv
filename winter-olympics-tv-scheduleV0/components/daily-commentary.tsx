"use client"

import { useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ChevronDown, ChevronUp, Clock, Eye, EyeOff } from "lucide-react"
import { SPORT_COLORS } from "@/lib/schedule-data"

const commentaryData = [
  {
    id: "c1",
    sport: "Alpine Skiing",
    headline: "Men's Downhill Preview: Bormio Course Set for Drama",
    preview: "Athletes have been training on the legendary Stelvio course. Conditions look fast with fresh grooming overnight...",
    author: "Olympics TV",
    updatedMinutesAgo: 30,
    spoilerContent: "Check back after the event for results.",
  },
  {
    id: "c2",
    sport: "Curling",
    headline: "Mixed Doubles Round Robin Heats Up",
    preview: "The USA mixed doubles team faces a crucial stretch of matches that could determine their path to the medal round...",
    author: "Olympics TV",
    updatedMinutesAgo: 45,
    spoilerContent: "Check back after the event for results.",
  },
  {
    id: "c3",
    sport: "Figure Skating",
    headline: "Team Event Competition Begins",
    preview: "The team event kicks off the figure skating program with short programs across all four disciplines...",
    author: "Olympics TV",
    updatedMinutesAgo: 60,
    spoilerContent: "Check back after the event for results.",
  },
]

function SportBadge({ sport }: { sport: string }) {
  const bgColor = SPORT_COLORS[sport] || "bg-gray-500"
  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded-full text-white ${bgColor}`}>
      {sport}
    </span>
  )
}

interface CommentaryCardProps {
  commentary: (typeof commentaryData)[0]
}

function CommentaryCard({ commentary }: CommentaryCardProps) {
  const [showSpoiler, setShowSpoiler] = useState(false)

  return (
    <Card className="overflow-hidden hover:shadow-md transition-shadow bg-card border-border">
      <CardContent className="p-5">
        <div className="flex items-center justify-between mb-3">
          <SportBadge sport={commentary.sport} />
          <div className="flex items-center gap-1 text-muted-foreground">
            <Clock className="h-3 w-3" />
            <span className="text-xs">Updated {commentary.updatedMinutesAgo} min ago</span>
          </div>
        </div>

        <h3 className="font-semibold text-foreground mb-2 text-base leading-snug">
          {commentary.headline}
        </h3>

        <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
          {commentary.preview}
        </p>

        <p className="text-xs text-muted-foreground mb-4">
          By <span className="font-medium text-foreground">{commentary.author}</span>
        </p>

        {/* Spoiler Section */}
        <div className="border-t border-border pt-3">
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-between text-muted-foreground hover:text-foreground"
            onClick={() => setShowSpoiler(!showSpoiler)}
          >
            <span className="flex items-center gap-2">
              {showSpoiler ? (
                <EyeOff className="h-4 w-4" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
              {showSpoiler ? "Hide Results" : "Show Results (Spoiler)"}
            </span>
            {showSpoiler ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </Button>

          {showSpoiler && (
            <div className="mt-3 p-3 bg-secondary rounded-md">
              <p className="text-sm text-foreground">{commentary.spoilerContent}</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export default function DailyCommentary() {
  return (
    <section className="pb-12">
      <h2 className="text-xl font-semibold text-foreground mb-4">Daily Commentary</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {commentaryData.map((commentary) => (
          <CommentaryCard key={commentary.id} commentary={commentary} />
        ))}
      </div>
    </section>
  )
}
