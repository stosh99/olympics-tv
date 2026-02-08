"use client"

import { useState, useRef, useMemo, useEffect, useCallback } from "react"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Calendar as CalendarComponent } from "@/components/ui/calendar"
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
  fetchTvScheduleRange,
  fetchOlympicSchedule,
  fetchOlympicScheduleRange,
  formatDateParam,
  generateDateRange,
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
  bandIndex?: number // Vertical band for concurrent events (0-4)
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

// Get all Olympic dates as strings (Feb 4-22, 2026)
function getAllOlympicDates(): string[] {
  const start = new Date(2026, 1, 4)
  const end = new Date(2026, 1, 22)
  return generateDateRange(formatDateParam(start), formatDateParam(end))
}

const TIMEZONES = [
  { value: "EST", label: "Eastern (EST)" },
  { value: "CST", label: "Central (CST)" },
  { value: "MST", label: "Mountain (MST)" },
  { value: "PST", label: "Pacific (PST)" },
  { value: "CET", label: "Central European (CET)" },
]

// Olympic Rings SVG component for hero banner decoration
const OlympicRings = ({ className = "" }: { className?: string }) => (
  <svg width="120" height="60" viewBox="0 0 100 48" className={className} style={{ height: "45px", width: "auto" }}>
    <circle cx="20" cy="18" r="10" fill="none" stroke="#0085C7" strokeWidth="3" />
    <circle cx="50" cy="18" r="10" fill="none" stroke="#000000" strokeWidth="3" />
    <circle cx="80" cy="18" r="10" fill="none" stroke="#DF0024" strokeWidth="3" />
    <circle cx="35" cy="30" r="10" fill="none" stroke="#F4C300" strokeWidth="3" />
    <circle cx="65" cy="30" r="10" fill="none" stroke="#009F3D" strokeWidth="3" />
  </svg>
)

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

// --- Phase 1: Calculate max concurrent events per day per network ---
function calculateMaxConcurrentPerDay(
  tvData: Map<string, Map<string, GridEvent[]>>,
  olympicDates: string[]
): Map<string, Map<string, number>> {
  const result = new Map<string, Map<string, number>>()

  // For each date
  for (const targetDate of olympicDates) {
    const dateMap = new Map<string, number>()

    // For each network, get events only for this date
    for (const [network, dateToEventsMap] of tvData.entries()) {
      // IMPORTANT: dateToEventsMap is Map<date, events>, NOT the events array directly
      const eventsForThisDate = dateToEventsMap.get(targetDate) || []

      // Calculate max concurrent for THIS DATE only
      let maxConcurrentThisDate = 0

      // For each event, count how many other events overlap with it
      for (let i = 0; i < eventsForThisDate.length; i++) {
        const event1 = eventsForThisDate[i]
        let overlappingCount = 1 // Count the event itself

        // Check against all other events on THE SAME DATE
        for (let j = 0; j < eventsForThisDate.length; j++) {
          if (i === j) continue
          const event2 = eventsForThisDate[j]

          // Check time overlap: event1 starts before event2 ends AND ends after event2 starts
          const event1Start = new Date(event1.startTime).getTime()
          const event1End = new Date(event1.endTime).getTime()
          const event2Start = new Date(event2.startTime).getTime()
          const event2End = new Date(event2.endTime).getTime()

          if (event1Start < event2End && event1End > event2Start) {
            overlappingCount++
          }
        }

        maxConcurrentThisDate = Math.max(maxConcurrentThisDate, overlappingCount)
      }

      // Store the max concurrent for this network on this date, capped at 5
      dateMap.set(network, Math.min(Math.max(1, maxConcurrentThisDate), 5))
    }

    result.set(targetDate, dateMap)
  }

  return result
}

// --- Phase 2: Band assignment algorithm for ENTIRE DAY (not per time-slot) ---
function assignBandIndicesForDay(events: GridEvent[]): GridEvent[] {
  if (events.length === 0) return events

  // Sort by start time
  const sorted = [...events].sort((a, b) =>
    new Date(a.startTime).getTime() - new Date(b.startTime).getTime()
  )

  // Track which bands are occupied and when they'll be free
  const bands: { endTime: Date; index: number }[] = []

  for (const event of sorted) {
    const startTime = new Date(event.startTime)
    const endTime = new Date(event.endTime)

    // Find first available band (where endTime <= event startTime, meaning no overlap)
    let assignedBand = -1

    for (let i = 0; i < bands.length; i++) {
      if (bands[i].endTime <= startTime) {
        assignedBand = i
        break
      }
    }

    if (assignedBand === -1) {
      // No free band, create new one (up to cap of 5)
      if (bands.length < 5) {
        assignedBand = bands.length
        bands.push({ endTime, index: assignedBand })
      } else {
        // Cap reached at 5, assign to band 0 (will appear as overlap if > 5)
        assignedBand = 0
        bands[0].endTime = endTime
      }
    } else {
      // Update band's end time
      bands[assignedBand].endTime = endTime
    }

    event.bandIndex = assignedBand
  }

  return sorted
}

// --- Band assignment for per-time-slot rendering (DEPRECATED - use global assignment above) ---
function assignBandIndices(events: GridEvent[]): GridEvent[] {
  // This function is now deprecated - bands should be assigned globally during data load
  // But keep it for backward compatibility in case it's still being called
  if (events.length === 0) return events

  // Just use the pre-assigned bandIndex if available
  // If not, assign new bands for this time slot
  if (events.every(e => e.bandIndex !== undefined)) {
    return events
  }

  // Fallback: assign bands if not already set
  const sorted = [...events].sort((a, b) =>
    new Date(a.startTime).getTime() - new Date(b.startTime).getTime()
  )

  const bands: { endTime: Date; index: number }[] = []

  for (const event of sorted) {
    const startTime = new Date(event.startTime)
    const endTime = new Date(event.endTime)

    let assignedBand = -1

    for (let i = 0; i < bands.length; i++) {
      if (bands[i].endTime <= startTime) {
        assignedBand = i
        break
      }
    }

    if (assignedBand === -1) {
      if (bands.length < 5) {
        assignedBand = bands.length
        bands.push({ endTime, index: assignedBand })
      } else {
        assignedBand = 0
        bands[0].endTime = endTime
      }
    } else {
      bands[assignedBand].endTime = endTime
    }

    event.bandIndex = assignedBand
  }

  return sorted
}

// --- Convert API data to grid events ---

function tvToGridEvents(rangeData: Map<string, TvScheduleResponse>): Map<string, Map<string, GridEvent[]>> {
  const multiDayMap = new Map<string, Map<string, GridEvent[]>>()

  for (const network of NETWORKS) {
    const dateMap = new Map<string, GridEvent[]>()

    for (const [date, tvData] of rangeData.entries()) {
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

      // GLOBAL band assignment for this network on this date
      // This ensures consistent band indices across all time slots for the day
      assignBandIndicesForDay(events)

      dateMap.set(date, events)
    }

    multiDayMap.set(network, dateMap)
  }

  return multiDayMap
}

function scheduleToGridEvents(rangeData: Map<string, ScheduleResponse>): Map<string, Map<string, GridEvent[]>> {
  const multiDayMap = new Map<string, Map<string, GridEvent[]>>()

  for (const [date, schedData] of rangeData.entries()) {
    for (const ev of schedData.events) {
      const discipline = ev.discipline
      if (!multiDayMap.has(discipline)) {
        multiDayMap.set(discipline, new Map<string, GridEvent[]>())
      }
      if (!multiDayMap.get(discipline)!.has(date)) {
        multiDayMap.get(discipline)!.set(date, [])
      }

      multiDayMap.get(discipline)!.get(date)!.push({
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
  }

  // GLOBAL band assignment for Olympic events (discipline/date)
  for (const [discipline, dateMap] of multiDayMap.entries()) {
    for (const [date, events] of dateMap.entries()) {
      assignBandIndicesForDay(events)
    }
  }

  return multiDayMap
}

export default function ScheduleGrid() {
  // Olympics dates
  const OLYMPICS_START = new Date(2026, 1, 4)   // Feb 4, 2026
  const OLYMPICS_END = new Date(2026, 1, 22)    // Feb 22, 2026

  const [selectedDate, setSelectedDate] = useState(new Date())
  const [timezone, setTimezone] = useState<string>("")
  const [selectedSport, setSelectedSport] = useState<string | null>(null)
  const [checkedSports, setCheckedSports] = useState<Set<string>>(new Set())
  const [showCheckedOnly, setShowCheckedOnly] = useState(false)
  const [viewMode, setViewMode] = useState<ViewMode>("tv")
  const [tvData, setTvData] = useState<TvScheduleResponse | null>(null)
  const [schedData, setSchedData] = useState<ScheduleResponse | null>(null)
  const [tvRangeData, setTvRangeData] = useState<Map<string, TvScheduleResponse> | null>(null)
  const [schedRangeData, setSchedRangeData] = useState<Map<string, ScheduleResponse> | null>(null)
  const [loading, setLoading] = useState(true)
  const [maxConcurrentPerDay, setMaxConcurrentPerDay] = useState<
    Map<string, Map<string, number>>
  >(new Map())
  // Initialize to Feb 4 (first Olympic date), not today
  const [leftmostVisibleDate, setLeftmostVisibleDate] = useState<string>("2026-02-04")
  const gridRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setTimezone(detectUserTimezone())
  }, [])

  // Fetch all 19 days at once when view mode changes
  useEffect(() => {
    async function loadData() {
      setLoading(true)
      const startDate = formatDateParam(OLYMPICS_START)
      const endDate = formatDateParam(OLYMPICS_END)

      try {
        if (viewMode === "tv") {
          const rangeData = await fetchTvScheduleRange(startDate, endDate)
          setTvRangeData(rangeData)
          // Calculate max concurrent for TV view
          const gridEvents = tvToGridEvents(rangeData)
          const allDates = getAllOlympicDates()
          try {
            const maxConcurrent = calculateMaxConcurrentPerDay(gridEvents, allDates)
            setMaxConcurrentPerDay(maxConcurrent)
          } catch (calcErr) {
            console.error("[CALCULATION ERROR]", calcErr)
            setMaxConcurrentPerDay(new Map())
          }
        } else {
          const [tvRange, schedRange] = await Promise.all([
            fetchTvScheduleRange(startDate, endDate),
            fetchOlympicScheduleRange(startDate, endDate),
          ])
          setTvRangeData(tvRange)
          setSchedRangeData(schedRange)
          // For all events view, use Olympic data for calculation
          const gridEvents = scheduleToGridEvents(schedRange)
          const allDates = getAllOlympicDates()
          try {
            const maxConcurrent = calculateMaxConcurrentPerDay(gridEvents, allDates)
            setMaxConcurrentPerDay(maxConcurrent)
          } catch (calcErr) {
            console.error("[CALCULATION ERROR]", calcErr)
            setMaxConcurrentPerDay(new Map())
          }
        }
      } catch (err) {
        console.error("Failed to load schedule:", err)
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [viewMode])

  // Auto-scroll to current date and time on initial load
  useEffect(() => {
    if (!loading && gridRef.current) {
      const now = new Date()
      const currentDateStr = formatDateParam(now)
      const allDates = getAllOlympicDates()
      const dayIndex = allDates.indexOf(currentDateStr)

      if (dayIndex >= 0) {
        // Update leftmost visible date to match current date
        console.log('[CONCURRENT DEBUG] Auto-scroll: Setting leftmostVisibleDate to', currentDateStr)
        setLeftmostVisibleDate(currentDateStr)

        const DAY_WIDTH = 38 * 128

        // Calculate scroll position for current time
        // Grid starts at 5:00 AM, each 30-min slot = 128px
        const GRID_START_HOUR = 5
        const SLOT_WIDTH = 128
        const MINUTES_PER_SLOT = 30

        const currentHour = now.getHours()
        const currentMinute = now.getMinutes()

        // Minutes since 5:00 AM
        let minutesSinceGridStart = (currentHour - GRID_START_HOUR) * 60 + currentMinute

        // Handle times before 5:00 AM (show from start of grid)
        if (minutesSinceGridStart < 0) {
          minutesSinceGridStart = 0
        }

        // Convert minutes to pixel offset (5-minute precision)
        const timeOffset = Math.floor(minutesSinceGridStart / MINUTES_PER_SLOT) * SLOT_WIDTH

        const scrollPosition = dayIndex * DAY_WIDTH + timeOffset
        gridRef.current.scrollTo({
          left: scrollPosition,
          behavior: "smooth",
        })
      }
    }
  }, [loading])

  // Store selectedDate in a ref to avoid stale closure
  const selectedDateRef = useRef<Date>(selectedDate)
  useEffect(() => {
    selectedDateRef.current = selectedDate
  }, [selectedDate])

  // Scroll timeout ref to persist across renders
  const scrollTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Create memoized scroll handler that can be attached as onScroll callback
  const handleScroll = useCallback(() => {
    const gridElement = gridRef.current
    if (!gridElement) {
      console.log('[SCROLL DEBUG] ❌ Grid element not found')
      return
    }

    console.log('[SCROLL DEBUG] ✅ Scroll event fired! scrollLeft:', gridElement.scrollLeft)

    // Debounce scroll updates to avoid too frequent date changes
    if (scrollTimeoutRef.current) clearTimeout(scrollTimeoutRef.current)

    scrollTimeoutRef.current = setTimeout(() => {
      const DAY_WIDTH = 38 * 128
      const allDates = getAllOlympicDates()

      // Get the scroll position (start of viewport)
      const scrollLeft = gridElement.scrollLeft
      const dayIndex = Math.floor(scrollLeft / DAY_WIDTH)  // Switch at day boundary (5:00 AM)
      const clampedIndex = Math.max(0, Math.min(dayIndex, allDates.length - 1))

      console.log('[SCROLL DEBUG] scrollLeft:', scrollLeft, '| dayIndex:', dayIndex, '→', clampedIndex)

      const targetDateStr = allDates[clampedIndex]
      const currentDateStr = formatDateParam(selectedDateRef.current)

      console.log('[SCROLL DEBUG] Current date:', currentDateStr, '| Target date:', targetDateStr)

      // Update leftmost visible date for dynamic row heights
      if (targetDateStr && targetDateStr !== leftmostVisibleDate) {
        console.log('[CONCURRENT DEBUG] Leftmost visible date changed:', leftmostVisibleDate, '→', targetDateStr)
        console.log('[CONCURRENT DEBUG] Setting leftmostVisibleDate to:', targetDateStr, '| Type:', typeof targetDateStr)
        setLeftmostVisibleDate(targetDateStr)
      }

      if (targetDateStr && targetDateStr !== currentDateStr) {
        // Parse the date string to create a Date object in local timezone
        // The date strings are in format "2026-02-06" representing Olympic calendar days
        console.log('[SCROLL DEBUG] ✅ UPDATING DATE:', currentDateStr, '→', targetDateStr)
        const [year, month, day] = targetDateStr.split('-').map(Number)
        const newDate = new Date(year, month - 1, day)
        setSelectedDate(newDate)
      } else {
        console.log('[SCROLL DEBUG] ⏸️  No date change (dates already match)')
      }
    }, 100) // Debounce for 100ms
  }, [leftmostVisibleDate])


  // Build grid data
  const gridData = useMemo(() => {
    if (viewMode === "tv" && tvRangeData) {
      return tvToGridEvents(tvRangeData)
    }
    if (viewMode === "all" && schedRangeData) {
      return scheduleToGridEvents(schedRangeData)
    }
    return new Map<string, Map<string, GridEvent[]>>()
  }, [viewMode, tvRangeData, schedRangeData])

  // Disciplines that have events across all days
  const disciplinesWithEvents = useMemo(() => {
    const set = new Set<string>()
    gridData.forEach((dateMap) => {
      if (dateMap instanceof Map) {
        dateMap.forEach((events) => events.forEach((e) => set.add(e.discipline)))
      } else {
        // Handle case where dateMap is still a GridEvent[] (shouldn't happen)
        (dateMap as any[]).forEach((e: any) => set.add(e.discipline))
      }
    })
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
          const dateMap = gridData.get(row)
          if (dateMap instanceof Map) {
            // Check if any date has events matching filters
            for (const events of dateMap.values()) {
              if (events.some((e) => checkedSports.has(e.discipline))) return true
            }
          }
          return false
        })
      }
      return rows.filter((row) => checkedSports.has(row))
    }
    if (selectedSport) {
      if (viewMode === "tv") {
        return rows.filter((row) => {
          const dateMap = gridData.get(row)
          if (dateMap instanceof Map) {
            // Check if any date has events matching filters
            for (const events of dateMap.values()) {
              if (events.some((e) => e.discipline === selectedSport)) return true
            }
          }
          return false
        })
      }
      return rows.filter((row) => row === selectedSport)
    }
    return rows
  }, [rows, selectedSport, showCheckedOnly, checkedSports, viewMode, gridData])

  const getEventsForSlot = (row: string, hour: number, minute: number): GridEvent[] => {
    // Get events for selected date only
    const dateStr = formatDateParam(selectedDate)
    const dateMap = gridData.get(row)
    if (!dateMap || !(dateMap instanceof Map)) return []

    const dayEvents = dateMap.get(dateStr) || []

    // Apply sport filters to events within the row
    const filtered = dayEvents.filter((e) => {
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
    scrollToDate(newDate)
  }

  const scrollGrid = (direction: "left" | "right") => {
    if (gridRef.current) {
      const HOURS_3_WIDTH = 6 * 128  // 3 hours = 6 slots × 128px = 768px
      gridRef.current.scrollBy({
        left: direction === "left" ? -HOURS_3_WIDTH : HOURS_3_WIDTH,
        behavior: "smooth",
      })
    }
  }

  const scrollToDate = (date: Date) => {
    if (!gridRef.current) return

    const targetDateStr = formatDateParam(date)
    const allDates = getAllOlympicDates()
    const dayIndex = allDates.indexOf(targetDateStr)

    if (dayIndex >= 0) {
      const DAY_WIDTH = 38 * 128  // 4,864px per day
      const scrollPosition = dayIndex * DAY_WIDTH

      // Update leftmost visible date immediately
      setLeftmostVisibleDate(targetDateStr)

      gridRef.current.scrollTo({
        left: scrollPosition,
        behavior: "smooth",
      })
    }
  }

  // Helper function to get row height based on max concurrent for current visible day
  const getRowHeight = (row: string): number => {
    const dateMap = maxConcurrentPerDay.get(leftmostVisibleDate)
    const maxConcurrent = dateMap?.get(row) ?? 1
    const height = Math.max(1, maxConcurrent) * 56 // 56px per band
    return height
  }

  const isNetworkView = viewMode === "tv"
  const statsLabel = schedData
    ? `${schedData.total_events} events · ${schedData.medal_events_count} medal sessions`
    : tvData
    ? `${Object.values(tvData.networks).flat().length} broadcasts`
    : ""

  return (
    <section className="space-y-3 bg-blue-200 rounded-lg p-3">
      {/* Hero Banner - View Toggle */}
      <div className="relative w-full bg-blue-200 py-4 border-b border-border/30">
        {/* Decorative Olympic Rings - Far Edges */}
        <OlympicRings className="absolute left-4 top-1/2 -translate-y-1/2 hidden md:block" />
        <OlympicRings className="absolute right-4 top-1/2 -translate-y-1/2 hidden md:block" />

        {/* Main Content - Inward from Rings */}
        <div className="relative flex flex-col md:flex-row items-center justify-between gap-4 px-4 md:px-[122px] max-w-full mx-auto">
          {/* Left: Large Toggle Buttons */}
          <div className="flex gap-3 w-full md:w-auto">
            {/* TV Schedule Button */}
            <button
              className={`h-11 px-6 rounded-lg text-sm font-semibold flex items-center gap-2 transition-all whitespace-nowrap ${
                viewMode === "tv"
                  ? "bg-foreground text-background shadow-md"
                  : "bg-white border border-border text-foreground hover:bg-secondary hover:border-foreground/20"
              }`}
              onClick={() => {
                setViewMode("tv")
                setSelectedSport(null)
                setShowCheckedOnly(false)
              }}
            >
              <Tv className="h-4 w-4 shrink-0" />
              <span className="hidden sm:inline">TV Schedule</span>
              <span className="sm:hidden">TV</span>
            </button>

            {/* All Events Button */}
            <button
              className={`h-11 px-6 rounded-lg text-sm font-semibold flex items-center gap-2 transition-all whitespace-nowrap ${
                viewMode === "all"
                  ? "bg-foreground text-background shadow-md"
                  : "bg-white border border-border text-foreground hover:bg-secondary hover:border-foreground/20"
              }`}
              onClick={() => {
                setViewMode("all")
                setSelectedSport(null)
                setShowCheckedOnly(false)
              }}
            >
              <Globe className="h-4 w-4 shrink-0" />
              <span className="hidden sm:inline">All Events</span>
              <span className="sm:hidden">All</span>
            </button>
          </div>

          {/* Right: Date Picker + Timezone */}
          <div className="flex items-center gap-2 w-full md:w-auto justify-center md:justify-end">
            {/* Date Navigation */}
            <div className="flex items-center gap-1">
              <Button variant="outline" size="icon" className="h-8 w-8" onClick={() => changeDate(-1)}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Popover>
                <PopoverTrigger asChild>
                  <button className="flex items-center gap-1 px-2 py-1.5 rounded border border-border bg-white hover:bg-secondary transition-colors cursor-pointer whitespace-nowrap">
                    <Calendar className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                    <span className="text-sm font-medium">{formatDate(selectedDate)}</span>
                  </button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-3" align="start">
                  <CalendarComponent
                    mode="single"
                    selected={selectedDate}
                    onSelect={(date) => {
                      if (date) {
                        setSelectedDate(date)
                        scrollToDate(date)
                      }
                    }}
                    defaultMonth={new Date(2026, 1, 1)}
                    disabled={(date) => date < new Date(2026, 1, 4) || date > new Date(2026, 1, 22)}
                    initialFocus
                  />
                </PopoverContent>
              </Popover>
              <Button variant="outline" size="icon" className="h-8 w-8" onClick={() => changeDate(1)}>
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>

            {/* Timezone */}
            {timezone && (
              <Select value={timezone} onValueChange={setTimezone}>
                <SelectTrigger className="w-[160px] h-8 text-xs bg-white">
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
          </div>
        </div>
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

        {/* View Selected button - always visible, disabled when no sports checked */}
        <button
          disabled={checkedSports.size === 0}
          className={`px-2 py-1 text-xs rounded-full border transition-colors ${
            checkedSports.size === 0
              ? "bg-card text-muted-foreground border-border opacity-50 cursor-not-allowed"
              : showCheckedOnly
              ? "bg-foreground text-background border-foreground"
              : "bg-card text-foreground border-border hover:bg-secondary"
          }`}
          onClick={showCheckedSports}
        >
          View Selected
        </button>
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
                    className="flex items-center justify-center px-3 border-b border-border transition-all duration-300 ease-in-out"
                    style={{ height: `${getRowHeight(row)}px` }}
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
                onScroll={handleScroll}
                className="flex-1 overflow-x-auto"
                style={{ scrollbarWidth: "thin" }}
              >
                <div className="min-w-max">
                  {/* Time Headers - Show all dates */}
                  <div className="flex border-b border-border bg-secondary">
                    {getAllOlympicDates().map((dateStr) => (
                      <div key={`date-header-${dateStr}`} className="flex">
                        {TIME_SLOTS.map((slot) => (
                          <div
                            key={`${dateStr}-${slot.value}`}
                            className="w-32 flex-shrink-0 px-2 py-3 text-center text-xs font-medium text-muted-foreground border-r border-border"
                          >
                            {slot.label}
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>

                  {/* Rows - Show all dates */}
                  {filteredRows.map((row) => (
                    <div
                      key={row}
                      className="flex border-b border-border transition-all duration-300 ease-in-out"
                      style={{ height: `${getRowHeight(row)}px` }}
                    >
                      {getAllOlympicDates().map((dateStr) => (
                        <div key={`${row}-${dateStr}`} className="flex">
                          {TIME_SLOTS.map((slot) => {
                            // Get events for this specific date
                            const dateMap = gridData.get(row)
                            if (!dateMap || !(dateMap instanceof Map)) return null

                            const dayEvents = dateMap.get(dateStr) || []

                            // Apply sport filters
                            const filtered = dayEvents.filter((e) => {
                              if (showCheckedOnly && checkedSports.size > 0) {
                                return checkedSports.has(e.discipline)
                              }
                              if (selectedSport) {
                                return e.discipline === selectedSport
                              }
                              return true
                            })

                            // Filter by time slot
                            const cellEvents = filtered.filter((e) => {
                              const h = e.startTime.getHours()
                              const m = e.startTime.getMinutes()
                              const slotMinute = m < 15 ? 0 : m < 45 ? 30 : 0
                              const slotHour = m >= 45 ? h + 1 : h
                              return slotHour === slot.hour && slotMinute === slot.minute
                            })

                            // Note: Band indices are now assigned GLOBALLY during data load (tvToGridEvents/scheduleToGridEvents)
                            // NOT per-time-slot, which ensures consistent vertical positioning across all time slots
                            // Just sort events by start time for display
                            const cellEventsWithBands = cellEvents.sort((a, b) =>
                              new Date(a.startTime).getTime() - new Date(b.startTime).getTime()
                            )

                            // Debug logging for Feb 10, 9 AM Peacock
                            if (dateStr === "2026-02-10" && row === "Peacock" && slot.hour === 9 && slot.minute === 0 && cellEventsWithBands.length > 0) {
                              console.log(`[DEBUG] Feb 10 9:00 AM Peacock (global bands):`, cellEventsWithBands.map(e => ({
                                name: e.name,
                                startTime: e.startTime.toLocaleTimeString(),
                                bandIndex: e.bandIndex,
                                top: `${(e.bandIndex || 0) * 56 + 2}px`
                              })))
                            }

                            return (
                              <div
                                key={`${row}-${dateStr}-${slot.value}`}
                                className="w-32 flex-shrink-0 p-1 border-r border-border relative bg-card hover:bg-secondary/50 transition-colors"
                              >
                                {cellEventsWithBands.map((event) => {
                                  const duration = getEventDuration(event)
                                  const sportColor = getSportColor(event.discipline)

                                  return (
                                    <Popover key={event.id}>
                                      <PopoverTrigger asChild>
                                        <div
                                          className={`absolute left-0.5 right-0.5 rounded-md px-1.5 py-1 cursor-pointer hover:ring-2 hover:ring-ring transition-all overflow-hidden ${sportColor} ${
                                            event.isReplay ? "opacity-60" : ""
                                          }`}
                                          style={{
                                            width: `calc(${duration * 100}% + ${(duration - 1) * 8}px - 4px)`,
                                            // Vertical positioning based on band index (56px per band)
                                            top: `${(event.bandIndex || 0) * 56 + 2}px`,
                                            height: '52px', // 56px - 4px padding
                                            zIndex: 10 + (event.bandIndex || 0), // Stack by band
                                          }}
                                        >
                                          <div className="flex flex-col h-full justify-start gap-0.5">
                                            {/* Sport (discipline) */}
                                            <p className="text-[9px] uppercase text-white/80 leading-tight">
                                              {event.discipline}
                                            </p>
                                            {/* Event name */}
                                            <p className="text-[10px] font-bold text-white line-clamp-1 leading-tight">
                                              {event.name}
                                              {event.isMedal && (
                                                <span className="ml-1">🏅</span>
                                              )}
                                            </p>
                                            {/* Summary */}
                                            {event.summary && (
                                              <p className="text-[9px] text-white/90 line-clamp-2 leading-tight">
                                                {event.summary}
                                              </p>
                                            )}
                                          </div>
                                          {/* LIVE/REPLAY badges positioned absolutely top-right */}
                                          <div className="absolute top-1 right-1 flex items-center gap-0.5">
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
                  ))}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-1">
          🏅 <span>Medal event</span>
        </div>
      </div>
    </section>
  )
}
