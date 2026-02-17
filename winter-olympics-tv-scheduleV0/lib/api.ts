// API client for Olympics TV FastAPI backend

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

// --- TV Schedule Types ---

export interface LinkedEvent {
  event_unit_code: string
  event_unit_name: string
  discipline: string
  medal_flag: boolean
}

export interface RundownItem {
  title: string
  description?: string
}

export interface Broadcast {
  drupal_id: string
  title: string
  short_title: string
  start_time: string
  end_time: string
  day_part: string | null
  summary: string | null
  video_url: string | null
  peacock_url: string | null
  is_medal_session: boolean
  is_replay: boolean
  olympic_day: number
  linked_events: LinkedEvent[]
  rundown: RundownItem[]
}

export interface TvScheduleResponse {
  date: string
  networks: Record<string, Broadcast[]>
}

// --- Olympic Schedule Types ---

export interface Competitor {
  code: string
  name: string
  noc: string
  competitor_type: string
}

export interface OlympicEvent {
  event_unit_code: string
  event_unit_name: string
  discipline: string
  event_name: string
  gender: string
  start_time: string
  end_time: string
  venue: string
  medal_flag: boolean
  phase_name: string
  status: string
  competitors: Competitor[]
}

export interface ScheduleResponse {
  date: string
  medal_events_count: number
  total_events: number
  events: OlympicEvent[]
}

// --- Date Info Types ---

export interface DateInfo {
  date: string
  olympic_day: number
  event_count: number
  medal_count: number
}

export interface DatesResponse {
  dates: DateInfo[]
}

// --- Commentary Types ---

export interface ResultSummary {
  name: string
  noc: string
  position: number | null
  mark: string | null
  medal_type: string | null  // ME_GOLD, ME_SILVER, ME_BRONZE
  wlt: string | null  // W, L, T for head-to-head
}

export interface CommentaryItem {
  event_unit_code: string
  commentary_type: "pre_event" | "post_event"
  discipline: string
  event_name: string
  event_date: string | null
  medal_flag: boolean
  first_paragraph: string
  full_content: string
  status: string
  updated_at: string | null
  results: ResultSummary[]
}

export interface CommentaryResponse {
  previews: CommentaryItem[]
  today_recaps: CommentaryItem[]
  previous_recaps: CommentaryItem[]
}

// --- Euro TV Types ---

export interface EuroBroadcast {
  broadcast_id: string
  channel_code: string
  channel_name: string
  country_code: string
  region: string
  title_original: string | null
  start_time: string
  end_time: string | null
  duration_minutes: number | null
  is_live: boolean
  is_replay: boolean
}

export interface EuroTVResponse {
  date: string
  channels: Record<string, EuroBroadcast[]>
}

// --- API Functions ---

export async function fetchTvSchedule(date: string): Promise<TvScheduleResponse> {
  const res = await fetch(`${API_BASE}/api/tv/${date}`)
  if (!res.ok) throw new Error(`Failed to fetch TV schedule: ${res.status}`)
  return res.json()
}

export async function fetchOlympicSchedule(date: string): Promise<ScheduleResponse> {
  const res = await fetch(`${API_BASE}/api/schedule/${date}`)
  if (!res.ok) throw new Error(`Failed to fetch schedule: ${res.status}`)
  return res.json()
}

export async function fetchDates(): Promise<DatesResponse> {
  const res = await fetch(`${API_BASE}/api/dates`)
  if (!res.ok) throw new Error(`Failed to fetch dates: ${res.status}`)
  return res.json()
}

export async function fetchCommentary(date?: string): Promise<CommentaryResponse> {
  const params = date ? `?date=${date}` : ''
  const res = await fetch(`${API_BASE}/api/commentary${params}`)
  if (!res.ok) throw new Error(`Failed to fetch commentary: ${res.status}`)
  return res.json()
}

export async function searchEvents(query: string): Promise<OlympicEvent[]> {
  const res = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(query)}`)
  if (!res.ok) throw new Error(`Search failed: ${res.status}`)
  return res.json()
}

// --- Helper Functions ---

export function formatDateParam(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

// Generate array of date strings from start to end (inclusive)
export function generateDateRange(start: string, end: string): string[] {
  const dates: string[] = []

  // Parse date strings explicitly in local timezone (YYYY-MM-DD format)
  const parseLocalDate = (dateStr: string): Date => {
    const [year, month, day] = dateStr.split('-').map(Number)
    return new Date(year, month - 1, day) // month is 0-indexed in Date constructor
  }

  const current = parseLocalDate(start)
  const endDate = parseLocalDate(end)

  while (current <= endDate) {
    dates.push(formatDateParam(current))
    current.setDate(current.getDate() + 1)
  }
  return dates
}

// Fetch TV schedule for date range (returns map of date -> response)
export async function fetchTvScheduleRange(startDate: string, endDate: string): Promise<Map<string, TvScheduleResponse>> {
  const dates = generateDateRange(startDate, endDate)
  const promises = dates.map(date => fetchTvSchedule(date).catch(() => ({ date, networks: {} } as TvScheduleResponse)))
  const results = await Promise.all(promises)

  const rangeData = new Map<string, TvScheduleResponse>()
  dates.forEach((date, index) => {
    rangeData.set(date, results[index])
  })
  return rangeData
}

// Fetch Olympic schedule for date range (returns map of date -> response)
export async function fetchOlympicScheduleRange(startDate: string, endDate: string): Promise<Map<string, ScheduleResponse>> {
  const dates = generateDateRange(startDate, endDate)
  const promises = dates.map(date => fetchOlympicSchedule(date).catch(() => ({ date, medal_events_count: 0, total_events: 0, events: [] } as ScheduleResponse)))
  const results = await Promise.all(promises)

  const rangeData = new Map<string, ScheduleResponse>()
  dates.forEach((date, index) => {
    rangeData.set(date, results[index])
  })
  return rangeData
}

// Fetch Euro schedule for a single date
export async function fetchEuroSchedule(date: string): Promise<EuroTVResponse> {
  const res = await fetch(`${API_BASE}/api/euro/${date}`)
  if (!res.ok) throw new Error(`Failed to fetch Euro schedule: ${res.status}`)
  return res.json()
}

// Fetch Euro schedule for date range (returns map of date -> response)
export async function fetchEuroScheduleRange(startDate: string, endDate: string): Promise<Map<string, EuroTVResponse>> {
  const dates = generateDateRange(startDate, endDate)
  const promises = dates.map(date => fetchEuroSchedule(date).catch(() => ({ date, channels: {} } as EuroTVResponse)))
  const results = await Promise.all(promises)
  const rangeData = new Map<string, EuroTVResponse>()
  dates.forEach((date, index) => {
    rangeData.set(date, results[index])
  })
  return rangeData
}

export function isLiveNow(broadcast: Broadcast): boolean {
  if (broadcast.is_replay) return false
  const now = new Date()
  const start = new Date(broadcast.start_time)
  const end = new Date(broadcast.end_time)
  return now >= start && now <= end
}

// Check if broadcast is currently airing (includes replays)
export function isOnNow(broadcast: Broadcast): boolean {
  const now = new Date()
  const start = new Date(broadcast.start_time)
  const end = new Date(broadcast.end_time)
  return now >= start && now <= end
}

export function isUpcoming(broadcast: Broadcast): boolean {
  const now = new Date()
  const start = new Date(broadcast.start_time)
  return start > now
}

export function getDisciplineFromBroadcast(broadcast: Broadcast): string {
  if (broadcast.linked_events.length > 0) {
    return broadcast.linked_events[0].discipline
  }
  // Try to infer from title
  return "Olympics"
}

/** Flatten all broadcasts from all networks into a single sorted array */
export function flattenBroadcasts(
  networks: Record<string, Broadcast[]>
): Array<Broadcast & { network_name: string }> {
  const all: Array<Broadcast & { network_name: string }> = []
  for (const [network, broadcasts] of Object.entries(networks)) {
    for (const b of broadcasts) {
      all.push({ ...b, network_name: network })
    }
  }
  return all.sort(
    (a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime()
  )
}
