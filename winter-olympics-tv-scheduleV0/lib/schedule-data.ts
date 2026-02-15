// Constants and styling only — no mock data

export type Network = "NBC" | "USA" | "CNBC" | "Peacock" | "GOLD ZONE"

export type ViewMode = "tv" | "all" | "euro"

export const NETWORKS: Network[] = ["NBC", "USA", "CNBC", "Peacock", "GOLD ZONE"]

export const NETWORK_COLORS: Record<string, { bg: string; text: string }> = {
  NBC: { bg: "bg-gradient-to-r from-red-500 via-yellow-500 to-green-500", text: "text-white" },
  USA: { bg: "bg-blue-600", text: "text-white" },
  CNBC: { bg: "bg-emerald-600", text: "text-white" },
  Peacock: { bg: "bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500", text: "text-white" },
  "GOLD ZONE": { bg: "bg-gradient-to-r from-yellow-500 to-amber-600", text: "text-white" },
}

export const SPORT_COLORS: Record<string, string> = {
  "Alpine Skiing": "bg-sky-500",
  Biathlon: "bg-amber-600",
  Bobsleigh: "bg-slate-700",
  Bobsled: "bg-slate-700",
  "Cross-Country Skiing": "bg-green-600",
  Curling: "bg-red-500",
  "Figure Skating": "bg-pink-500",
  "Freestyle Skiing": "bg-orange-500",
  "Ice Hockey": "bg-blue-700",
  Luge: "bg-indigo-600",
  "Nordic Combined": "bg-teal-600",
  "Short Track Speed Skating": "bg-rose-600",
  "Short Track": "bg-rose-600",
  Skeleton: "bg-zinc-600",
  "Ski Jumping": "bg-cyan-600",
  Snowboard: "bg-violet-600",
  "Speed Skating": "bg-emerald-500",
  Olympics: "bg-gray-500",
}

export const COUNTRY_COLORS: Record<string, { bg: string; text: string }> = {
  GB: { bg: "bg-blue-700", text: "text-white" },
  DE: { bg: "bg-yellow-500", text: "text-black" },
  IT: { bg: "bg-green-600", text: "text-white" },
  FR: { bg: "bg-blue-500", text: "text-white" },
  NO: { bg: "bg-red-600", text: "text-white" },
  SE: { bg: "bg-blue-400", text: "text-yellow-400" },
  FI: { bg: "bg-white border border-blue-500", text: "text-blue-700" },
  DK: { bg: "bg-red-500", text: "text-white" },
}

export const COUNTRY_FLAGS: Record<string, string> = {
  GB: "\u{1F1EC}\u{1F1E7}", DE: "\u{1F1E9}\u{1F1EA}", IT: "\u{1F1EE}\u{1F1F9}", FR: "\u{1F1EB}\u{1F1F7}",
  NO: "\u{1F1F3}\u{1F1F4}", SE: "\u{1F1F8}\u{1F1EA}", FI: "\u{1F1EB}\u{1F1EE}", DK: "\u{1F1E9}\u{1F1F0}",
}

export function getSportColor(discipline: string): string {
  return SPORT_COLORS[discipline] || "bg-gray-500"
}
