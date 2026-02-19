import { NextRequest, NextResponse } from "next/server"
import { query } from "@/lib/db"

interface BroadcastRow {
  drupal_id: string
  title: string
  short_title: string | null
  network_name: string | null
  start_time: string
  end_time: string
  day_part: string | null
  summary: string | null
  video_url: string | null
  peacock_url: string | null
  is_medal_session: boolean
  is_replay: boolean
  olympic_day: number | null
}

interface LinkedEventRow {
  event_unit_code: string
  event_unit_name: string
  discipline: string | null
  medal_flag: number | null
}

interface RundownRow {
  header: string | null
  description: string | null
  segment_time: number | null
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ date: string }> }
) {
  const { date } = await params

  // Validate date format
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
    return NextResponse.json(
      { detail: "Invalid date format. Use YYYY-MM-DD" },
      { status: 400 }
    )
  }

  try {
    // Query broadcasts for the date
    const broadcasts = await query<BroadcastRow>(
      `SELECT
        nb.drupal_id,
        nb.title,
        nb.short_title,
        nb.network_name,
        nb.start_time,
        nb.end_time,
        nb.day_part,
        nb.summary,
        nb.video_url,
        nb.peacock_url,
        nb.is_medal_session,
        nb.is_replay,
        nb.olympic_day
      FROM nbc_broadcasts nb
      WHERE DATE(nb.start_time) = $1
      ORDER BY nb.network_name, nb.start_time`,
      [date]
    )

    // Group broadcasts by network
    const networks: Record<string, unknown[]> = {}

    for (const broadcast of broadcasts) {
      const network = broadcast.network_name || "Peacock"

      if (!networks[network]) {
        networks[network] = []
      }

      // Get linked events
      const events = await query<LinkedEventRow>(
        `SELECT
          su.event_unit_code,
          su.event_unit_name,
          d.name as discipline,
          su.medal_flag
        FROM nbc_broadcast_units nbu
        JOIN schedule_units su ON nbu.unit_code = su.event_unit_code
        LEFT JOIN events e ON su.event_id = e.event_id
        LEFT JOIN disciplines d ON e.discipline_code = d.code
        WHERE nbu.broadcast_drupal_id = $1
        ORDER BY su.start_time`,
        [broadcast.drupal_id]
      )

      const linked_events = events.map((e) => ({
        event_unit_code: e.event_unit_code,
        event_unit_name: e.event_unit_name,
        discipline: e.discipline || "Unknown",
        medal_flag: Boolean(e.medal_flag),
      }))

      // Get rundown segments
      const rundownRows = await query<RundownRow>(
        `SELECT header, description, segment_time
        FROM nbc_broadcast_rundown
        WHERE broadcast_drupal_id = $1
        ORDER BY segment_order`,
        [broadcast.drupal_id]
      )

      const rundown = rundownRows.map((r) => ({
        header: r.header,
        description: r.description,
        segment_time: r.segment_time,
      }))

      networks[network].push({
        drupal_id: broadcast.drupal_id,
        title: broadcast.title,
        short_title: broadcast.short_title,
        start_time: broadcast.start_time,
        end_time: broadcast.end_time,
        day_part: broadcast.day_part,
        summary: broadcast.summary,
        video_url: broadcast.video_url,
        peacock_url: broadcast.peacock_url,
        is_medal_session: broadcast.is_medal_session,
        is_replay: broadcast.is_replay,
        olympic_day: broadcast.olympic_day,
        linked_events,
        rundown,
      })
    }

    return NextResponse.json({ date, networks })
  } catch (error) {
    console.error("TV schedule query error:", error)
    return NextResponse.json(
      { detail: "Internal server error" },
      { status: 500 }
    )
  }
}
