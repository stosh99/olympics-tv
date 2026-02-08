"use client"

import { useState, useRef, useMemo, useEffect } from "react"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Calendar, ChevronLeft, ChevronRight, Globe, Tv, Check } from "lucide-react"
import { NETWORKS, NETWORK_COLORS, getSportColor, type ViewMode } from "@/lib/schedule-data"
import {
  fetchTvSchedule,
  fetchOlympicSchedule,
  formatDateParam,
  type TvScheduleResponse,
  type ScheduleResponse,
} from "@/lib/api"

// All Olympic winter sports — always shown
const ALL_DISCIPLINES = [
  "Alpine Skiing",
  "Biathlon",
  "Bobsleigh",
  "Cross-Country Skiing",
  "Curling",
  "Figure Skating",
  "Freestyle Skiing",
  "Ice Hockey",
  "Luge",
  "Nordic Combined",
  "Short Track Speed Skating",
  "Skeleton",
  "Ski Jumping",
  "Snowboard",
  "Speed Skating",
]

// --- Grid row item: normalized for both views ---
interface GridEvent {
  id: string
  name: string
  discipline: string
  startTime: Date
  endTime: Date
  isLive: boolean
  isReplay: boolean
  isMedal: boolean
  network: string | null
  summary: string | null
  videoUrl: string | null
  venue: string | null
}

// Time slots from 5 AM to midnight in 30-min increments
const TIME_SLOTS = Array.from({ length: 38 }, (_, i) => {
  const hour = Math.floor(i / 2) + 5
  const minute = i % 2 === 0 ? "00" : "30"
  const displayHour = hour > 12 ? hour - 12 : hour === 0 ? 12 : hour
  const ampm = hour >= 12 ? "PM" : "AM"
  return {
    value: `${hour}:${minute}`,
    label: `${displayHour}:${minute} ${ampm}`,
    hour,
    minute: parseInt(minute),
  }
})

const TIMEZONES = [
  { value: "EST", label: "Eastern (EST)" },
  { value: "CST", label: "Central (CST)" },
  { value: "MST", label: "Mountain (MST)" },
  { value: "PST", label: "Pacific (PST)" },
  { value: "CET", label: "Central European (CET)" },
]

function detectUserTimezone(): string {
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone
    if (tz.includes("America/New_York") || tz.includes("America/Detroit") || tz.includes("America/Indiana")) return "EST"
    if (tz.includes("America/Chicago") || tz.includes("America/Menominee")) return "CST"
    if (tz.includes("America/Denver") || tz.includes("America/Phoenix") || tz.includes("America/Boise")) return "MST"
    if (tz.includes("America/Los_Angeles") || tz.includes("America/Anchorage")) return "PST"
    if (tz.includes("Europe/")) return "CET"
    return "EST"
  } catch {
    return "EST"
  }
}

function formatDate(date: Date): string {
  return date.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  })
}

// --- Convert API data to grid events ---

function tvToGridEvents(tvData: TvScheduleResponse): Map<string, GridEvent[]> {
  const map = new Map<string, GridEvent[]>()
  for (const network of NETWORKS) {
    const broadcasts = tvData.networks[network] || []
    const events: GridEvent[] = broadcasts.map((b) => ({
      id: b.drupal_id,
      name: b.short_title || b.title,
      discipline: b.linked_events.length > 0 ? b.linked_events[0].discipline : "Olympics",
      startTime: new Date(b.start_time),
      endTime: new Date(b.end_time),
      isLive: !b.is_replay && new Date() >= new Date(b.start_time) && new Date() <= new Date(b.end_time),
      isReplay: b.is_replay,
      isMedal: b.is_medal_session,
      network,
      summary: b.summary,
      videoUrl: b.video_url,
      venue: null,
    }))
    map.set(network, events)
  }
  return map
}

function scheduleToGridEvents(schedData: ScheduleResponse): Map<string, GridEvent[]> {
  const map = new Map<string, GridEvent[]>()
  for (const ev of schedData.events) {
    const discipline = ev.discipline
    if (!map.has(discipline)) map.set(discipline, [])
    map.get(discipline)!.push({
      id: ev.event_unit_code,
      name: ev.event_unit_name,
      discipline,
      startTime: new Date(ev.start_time),
      endTime: new Date(ev.end_time),
      isLive: ev.status === "RUNNING",
      isReplay: false,
      isMedal: ev.medal_flag,
      network: null,
      summary: null,
      videoUrl: null,
      venue: ev.venue,
    })
  }
  return map
}

export default function ScheduleGrid() {
  const [selectedDate, setSelectedDate] = useState(new Date())
  const [timezone, setTimezone] = useState<string>("")
  const [selectedSport, setSelectedSport] = useState<string | null>(null)
  const [checkedSports, setCheckedSports] = useState<Set<string>>(new Set())
  const [showCheckedOnly, setShowCheckedOnly] = useState(false)
  const [viewMode, setViewMode] = useState<ViewMode>("tv")
  const [tvData, setTvData] = useState<TvScheduleResponse | null>(null)
  const [schedData, setSchedData] = useState<ScheduleResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const gridRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setTimezone(detectUserTimezone())
  }, [])

  // Fetch data when date or view mode changes
  useEffect(() => {
    async function loadData() {
      setLoading(true)
      const dateStr = formatDateParam(selectedDate)
      try {
        if (viewMode === "tv") {
          const data = await fetchTvSchedule(dateStr)
          setTvData(data)
        } else {
          const [tv, sched] = await Promise.all([
            fetchTvSchedule(dateStr),
            fetchOlympicSchedule(dateStr),
          ])
          setTvData(tv)
          setSchedData(sched)
        }
      } catch (err) {
        console.error("Failed to load schedule:", err)
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [selectedDate, viewMode])

  // Build grid data
  const gridData = useMemo(() => {
    if (viewMode === "tv" && tvData) {
      return tvToGridEvents(tvData)
    }
    if (viewMode === "all" && schedData) {
      return scheduleToGridEvents(schedData)
    }
    return new Map<string, GridEvent[]>()
  }, [viewMode, tvData, schedData])

  // Disciplines that have events today
  const disciplinesWithEvents = useMemo(() => {
    const set = new Set<string>()
    gridData.forEach((events) => events.forEach((e) => set.add(e.discipline)))
    return set
  }, [gridData])

  const rows = useMemo(() => {
    if (viewMode === "tv") return NETWORKS as string[]
    return ALL_DISCIPLINES
  }, [viewMode])

  // Determine which rows to show based on filters
  const filteredRows = useMemo(() => {
    if (showCheckedOnly && checkedSports.size > 0) {
      if (viewMode === "tv") {
        return rows.filter((row) => {
          const events = gridData.get(row) || []
          return events.some((e) => checkedSports.has(e.discipline))
        })
      }
      return rows.filter((row) => checkedSports.has(row))
    }
    if (selectedSport) {
      if (viewMode === "tv") {
        return rows.filter((row) => {
          const events = gridData.get(row) || []
          return events.some((e) => e.discipline === selectedSport)
        })
      }
      return rows.filter((row) => row === selectedSport)
    }
    return rows
  }, [rows, selectedSport, showCheckedOnly, checkedSports, viewMode, gridData])

  const getEventsForSlot = (row: string, hour: number, minute: number): GridEvent[] => {
    const events = gridData.get(row) || []

    // Apply sport filters to events within the row
    const filtered = events.filter((e) => {
      if (showCheckedOnly && checkedSports.size > 0) {
        return checkedSports.has(e.discipline)
      }
      if (selectedSport) {
        return e.discipline === selectedSport
      }
      return true
    })

    return filtered.filter((e) => {
      const h = e.startTime.getHours()
      const m = e.startTime.getMinutes()
      const slotMinute = m < 15 ? 0 : m < 45 ? 30 : 0
      const slotHour = m >= 45 ? h + 1 : h
      return slotHour === hour && slotMinute === minute
    })
  }

  const getEventDuration = (event: GridEvent): number => {
    const durationMs = event.endTime.getTime() - event.startTime.getTime()
    const durationSlots = Math.ceil(durationMs / (30 * 60 * 1000))
    return Math.max(1, Math.min(durationSlots, 6))
  }

  const toggleCheckedSport = (sport: string) => {
    setCheckedSports((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(sport)) {
        newSet.delete(sport)
      } else {
        newSet.add(sport)
      }
      return newSet
    })
  }

  const selectSingleSport = (sport: string) => {
    setShowCheckedOnly(false)
    setSelectedSport(selectedSport === sport ? null : sport)
  }

  const showCheckedSports = () => {
    if (checkedSports.size > 0) {
      setSelectedSport(null)
      setShowCheckedOnly(true)
    }
  }

  const showAllSports = () => {
    setSelectedSport(null)
    setShowCheckedOnly(false)
  }

  const changeDate = (days: number) => {
    const newDate = new Date(selectedDate)
    newDate.setDate(newDate.getDate() + days)
    setSelectedDate(newDate)
  }

  const scrollGrid = (direction: "left" | "right") => {
    if (gridRef.current) {
      gridRef.current.scrollBy({
        left: direction === "left" ? -300 : 300,
        behavior: "smooth",
      })
    }
  }

  const isNetworkView = viewMode === "tv"
  const statsLabel = schedData
    ? `${schedData.total_events} events · ${schedData.medal_events_count} medal sessions`
    : tvData
    ? `${Object.values(tvData.networks).flat().length} broadcasts`
    : ""

  return (
    <section className="space-y-3">
      {/* Controls Bar */}
      <div className="flex flex-wrap items-center gap-3">
        {/* View Mode Toggle */}
        <div className="flex rounded-lg border border-border overflow-hidden">
          <button
            className={`px-3 py-1.5 text-xs font-medium flex items-center gap-1 transition-colors ${
              viewMode === "tv"
                ? "bg-foreground text-background"
                : "bg-card text-foreground hover:bg-secondary"
            }`}
            onClick={() => { setViewMode("tv"); setSelectedSport(null); setShowCheckedOnly(false) }}
          >
            <Tv className="h-3 w-3" /> TV Schedule
          </button>
          <button
            className={`px-3 py-1.5 text-xs font-medium flex items-center gap-1 transition-colors ${
              viewMode === "all"
                ? "bg-foreground text-background"
                : "bg-card text-foreground hover:bg-secondary"
            }`}
            onClick={() => { setViewMode("all"); setSelectedSport(null); setShowCheckedOnly(false) }}
          >
            <Globe className="h-3 w-3" /> All Events
          </button>
        </div>

        {/* Date Navigation */}
        <div className="flex items-center gap-1">
          <Button variant="outline" size="icon" className="h-7 w-7" onClick={() => changeDate(-1)}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <div className="flex items-center gap-1 px-2">
            <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-sm font-medium">{formatDate(selectedDate)}</span>
          </div>
          <Button variant="outline" size="icon" className="h-7 w-7" onClick={() => changeDate(1)}>
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>

        {/* Timezone */}
        {timezone && (
          <Select value={timezone} onValueChange={setTimezone}>
            <SelectTrigger className="w-[160px] h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TIMEZONES.map((tz) => (
                <SelectItem key={tz.value} value={tz.value}>
                  {tz.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}

        {/* Stats */}
        {statsLabel && (
          <span className="text-xs text-muted-foreground ml-auto">{statsLabel}</span>
        )}
      </div>

      {/* Sport Filter - Dual checkbox/click buttons */}
      <div className="flex flex-wrap items-center gap-1.5">
        {/* All Sports button */}
        <button
          className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${
            !selectedSport && !showCheckedOnly
              ? "bg-foreground text-background border-foreground"
              : "bg-card text-foreground border-border hover:bg-secondary"
          }`}
          onClick={showAllSports}
        >
          All Sports
        </button>

        {/* Show Checked button */}
        {checkedSports.size > 0 && (
          <button
            className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${
              showCheckedOnly
                ? "bg-foreground text-background border-foreground"
                : "bg-card text-foreground border-border hover:bg-secondary"
            }`}
            onClick={showCheckedSports}
          >
            My Sports ({checkedSports.size})
          </button>
        )}

        {/* Individual sport buttons with checkbox */}
        {ALL_DISCIPLINES.map((sport) => {
          const hasEvents = disciplinesWithEvents.has(sport)
          const isChecked = checkedSports.has(sport)
          const isSelected = selectedSport === sport

          return (
            <div key={sport} className="flex items-center">
              {/* Checkbox area */}
              <button
                className={`flex items-center justify-center w-5 h-5 rounded-l border transition-colors ${
                  isChecked
                    ? "bg-foreground border-foreground"
                    : "bg-card border-border hover:bg-secondary"
                } ${!hasEvents ? "opacity-40" : ""}`}
                onClick={() => toggleCheckedSport(sport)}
                title={`${isChecked ? "Uncheck" : "Check"} ${sport}`}
              >
                {isChecked && <Check className="h-3 w-3 text-background" />}
              </button>

              {/* Sport name area */}
              <button
                className={`px-2 py-1 text-xs rounded-r border-y border-r transition-colors ${
                  isSelected
                    ? "bg-foreground text-background border-foreground"
                    : hasEvents
                    ? "bg-card text-foreground border-border hover:bg-secondary"
                    : "bg-card text-muted-foreground/40 border-border/40 cursor-default"
                }`}
                onClick={() => hasEvents && selectSingleSport(sport)}
                disabled={!hasEvents}
              >
                <span className="flex items-center gap-1">
                  <span className={`w-2 h-2 rounded-full ${getSportColor(sport)} ${!hasEvents ? "opacity-40" : ""}`} />
                  {sport}
                </span>
              </button>
            </div>
          )
        })}
      </div>

      {/* Grid Scroll Controls */}
      <div className="flex justify-end gap-1.5">
        <Button variant="outline" size="icon" className="h-7 w-7" onClick={() => scrollGrid("left")}>
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <Button variant="outline" size="icon" className="h-7 w-7" onClick={() => scrollGrid("right")}>
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      {/* Schedule Grid */}
      <Card className="overflow-hidden bg-card border-border">
        <CardContent className="p-0">
          {loading ? (
            <div className="p-8 text-center text-sm text-muted-foreground">Loading schedule...</div>
          ) : filteredRows.length === 0 ? (
            <div className="p-8 text-center text-sm text-muted-foreground">No events found for this date.</div>
          ) : (
            <div className="flex">
              {/* Row Labels (Fixed) */}
              <div className="flex-shrink-0 bg-secondary border-r border-border">
                <div className="h-12 border-b border-border" />
                {filteredRows.map((row) => (
                  <div
                    key={row}
                    className="h-14 flex items-center justify-center px-3 border-b border-border"
                  >
                    {isNetworkView ? (
                      <span
                        className={`px-3 py-1.5 text-xs font-bold rounded whitespace-nowrap ${
                          NETWORK_COLORS[row]?.bg || "bg-gray-500"
                        } ${NETWORK_COLORS[row]?.text || "text-white"}`}
                      >
                        {row}
                      </span>
                    ) : (
                      <div className="flex items-center gap-2">
                        <span className={`w-3 h-3 rounded-full ${getSportColor(row)}`} />
                        <span className="text-xs font-medium text-foreground whitespace-nowrap max-w-[100px] truncate">
                          {row}
                        </span>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Scrollable Time Slots */}
              <div
                ref={gridRef}
                className="flex-1 overflow-x-auto"
                style={{ scrollbarWidth: "thin" }}
              >
                <div className="min-w-max">
                  {/* Time Headers */}
                  <div className="flex border-b border-border bg-secondary">
                    {TIME_SLOTS.map((slot) => (
                      <div
                        key={slot.value}
                        className="w-32 flex-shrink-0 px-2 py-3 text-center text-xs font-medium text-muted-foreground border-r border-border"
                      >
                        {slot.label}
                      </div>
                    ))}
                  </div>

                  {/* Rows */}
                  {filteredRows.map((row) => (
                    <div key={row} className="flex h-14 border-b border-border">
                      {TIME_SLOTS.map((slot) => {
                        const cellEvents = getEventsForSlot(row, slot.hour, slot.minute)
                        return (
                          <div
                            key={`${row}-${slot.value}`}
                            className="w-32 flex-shrink-0 p-1 border-r border-border relative bg-card hover:bg-secondary/50 transition-colors"
                          >
                            {cellEvents.map((event) => {
                              const duration = getEventDuration(event)
                              const sportColor = getSportColor(event.discipline)

                              return (
                                <Popover key={event.id}>
                                  <PopoverTrigger asChild>
                                    <div
                                      className={`absolute top-0.5 left-0.5 right-0.5 bottom-0.5 rounded-md px-1.5 py-1 cursor-pointer hover:ring-2 hover:ring-ring transition-all overflow-hidden ${sportColor} ${
                                        event.isReplay ? "opacity-60" : ""
                                      }`}
                                      style={{
                                        width: `calc(${duration * 100}% + ${(duration - 1) * 8}px - 4px)`,
                                        zIndex: 10,
                                      }}
                                    >
                                      <div className="flex flex-col h-full justify-between">
                                        <p className="text-[11px] font-semibold text-white line-clamp-1 leading-tight">
                                          {event.name}
                                          {event.isMedal && (
                                            <span className="ml-1">🏅</span>
                                          )}
                                        </p>
                                        <div className="flex items-center justify-between">
                                          <div className="flex items-center gap-0.5">
                                            {event.isLive ? (
                                              <Badge variant="destructive" className="text-[9px] px-1 py-0 h-3.5">
                                                LIVE
                                              </Badge>
                                            ) : event.isReplay ? (
                                              <Badge variant="secondary" className="text-[9px] px-1 py-0 h-3.5 bg-white/20 text-white">
                                                REPLAY
                                              </Badge>
                                            ) : null}
                                          </div>
                                          <span className="text-[9px] text-white/80 font-medium">
                                            Preview
                                          </span>
                                        </div>
                                      </div>
                                    </div>
                                  </PopoverTrigger>
                                  <PopoverContent className="w-80 p-3" align="start">
                                    <div className="space-y-2">
                                      <div className="flex items-center gap-2">
                                        <span className={`w-3 h-3 rounded-full ${sportColor}`} />
                                        <span className="text-sm font-medium">{event.discipline}</span>
                                        {event.isMedal && (
                                          <Badge className="text-[10px] bg-yellow-500 text-white">MEDAL EVENT</Badge>
                                        )}
                                      </div>
                                      <p className="text-sm font-semibold">{event.name}</p>
                                      {event.summary && (
                                        <p className="text-sm text-muted-foreground leading-relaxed">
                                          {event.summary}
                                        </p>
                                      )}
                                      {event.venue && (
                                        <p className="text-xs text-muted-foreground">📍 {event.venue}</p>
                                      )}
                                      {event.network && (
                                        <p className="text-xs text-muted-foreground">📺 {event.network}</p>
                                      )}
                                      <p className="text-xs text-muted-foreground">
                                        {new Date(event.startTime).toLocaleTimeString("en-US", {
                                          hour: "numeric",
                                          minute: "2-digit",
                                          hour12: true,
                                        })}
                                        {" — "}
                                        {new Date(event.endTime).toLocaleTimeString("en-US", {
                                          hour: "numeric",
                                          minute: "2-digit",
                                          hour12: true,
                                        })}
                                      </p>
                                      {event.videoUrl && (
                                        <a
                                          href={event.videoUrl}
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
                              )
                            })}
                          </div>
                        )
                      })}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
        {viewMode === "tv" && (
          <div className="flex items-center gap-1">
            <span className="opacity-60">▪</span>
            <span>Faded = Replay</span>
          </div>
        )}
        <div className="flex items-center gap-1">
          🏅 <span>Medal event</span>
        </div>
      </div>
    </section>
  )
}
