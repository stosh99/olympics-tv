"use client"

import { useState, useRef, useEffect } from "react"
import Header from "@/components/header"
import WhatsOnNow from "@/components/whats-on-now"
import ComingUpNext from "@/components/coming-up-next"
import ScheduleGrid from "@/components/schedule-grid"
import DailyCommentary from "@/components/daily-commentary"
import Footer from "@/components/footer"

export default function Home() {
  return (
    <main className="min-h-screen bg-background">
      <Header />
      <div className="mx-auto px-4 py-4 space-y-4">
        <WhatsOnNow />
        <ComingUpNext />
        <ScheduleGrid />
        <DailyCommentary />
      </div>
      <Footer />
    </main>
  )
}
