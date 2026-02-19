import { Pool } from "pg"

const pool = new Pool({
  host: process.env.DB_HOST || "127.0.0.1",
  port: parseInt(process.env.DB_PORT || "5432"),
  database: process.env.DB_NAME || "olympics_tv",
  user: process.env.DB_USER || "stosh99",
  password: process.env.DB_PASSWORD || "olympics_tv_dev",
  max: 10,
})

export async function query<T extends Record<string, unknown>>(
  text: string,
  params?: unknown[]
): Promise<T[]> {
  const result = await pool.query(text, params)
  return result.rows as T[]
}

export default pool
