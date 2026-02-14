"use client"

import Link from "next/link"
import { ChevronLeft } from "lucide-react"
import Header from "@/components/header"
import Footer from "@/components/footer"
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "@/components/ui/accordion"

const faqData = [
  {
    section: "How to Watch",
    questions: [
      {
        question: "How can I watch the 2026 Winter Olympics?",
        answer:
          "NBC has exclusive US broadcast rights. Events air across NBC, USA Network, CNBC, and Peacock streaming. Peacock carries every event live, while the TV networks feature curated coverage with primetime highlights on NBC.",
      },
      {
        question: "What channels are the Olympics on?",
        answer:
          "NBC (primetime and marquee events), USA Network (daytime and secondary events), CNBC (additional live coverage), and Peacock (all events streaming live). NBC's Gold Zone channel provides a red-zone style whip-around show during peak sessions.",
      },
      {
        question: "Can I watch the Olympics on Peacock without cable?",
        answer:
          "Yes. Peacock is a standalone streaming service — no cable subscription needed. A Peacock subscription gives you access to every Olympic event live. Some content may also be available on the free Peacock tier.",
      },
      {
        question: "How do I watch without cable TV?",
        answer:
          "Peacock streaming is the simplest option and carries all events. You can also access NBC, USA, and CNBC through live TV streaming services like YouTube TV, Hulu + Live TV, Sling TV, or FuboTV.",
      },
      {
        question: "What is NBC Gold Zone?",
        answer:
          "Gold Zone is NBC's whip-around channel that jumps between the most exciting live action across all venues. Think NFL RedZone but for the Olympics — it switches between events as medals are decided, records are broken, or drama unfolds.",
      },
    ],
  },
  {
    section: "Schedule & Timing",
    questions: [
      {
        question: "What time do events start each day?",
        answer:
          "Most events begin between 4:00 AM and 6:00 AM Eastern Time due to the 6-hour time difference between the US East Coast and Italy. Primetime NBC coverage typically airs from 8:00 PM to midnight ET.",
      },
      {
        question: "What is the time difference between the US and Italy?",
        answer:
          "Italy is 6 hours ahead of US Eastern Time, 9 hours ahead of Pacific Time. An event starting at 10:00 AM in Cortina would be 4:00 AM ET / 1:00 AM PT.",
      },
      {
        question: "When are the medal events?",
        answer:
          "Medal events are spread across all 16 competition days (Feb 6–22). This site marks medal sessions with a special badge in the schedule grid so you can find them at a glance.",
      },
      {
        question: "How long are the 2026 Winter Olympics?",
        answer:
          "Competition runs 16 days from February 6 to February 22, 2026. The opening ceremony was February 6 in Milan, and the closing ceremony is February 22 in Verona's ancient Roman arena.",
      },
    ],
  },
  {
    section: "About the Games",
    questions: [
      {
        question: "Where are the 2026 Winter Olympics being held?",
        answer:
          "Events are spread across multiple venues in northern Italy. Milano hosts ice sports (figure skating, short track, hockey). Cortina d'Ampezzo has alpine skiing, bobsled, luge, skeleton, and curling. Bormio and Livigno cover additional alpine skiing, freestyle, and snowboard. Predazzo and Tesero host ski jumping, Nordic combined, and cross-country. Anterselva hosts biathlon.",
      },
      {
        question: "What sports are in the 2026 Winter Olympics?",
        answer:
          "16 disciplines: Alpine Skiing, Biathlon, Bobsled, Cross-Country Skiing, Curling, Figure Skating, Freestyle Skiing, Ice Hockey, Luge, Nordic Combined, Short Track Speed Skating, Skeleton, Ski Jumping, Snowboard, Speed Skating, and Ski Mountaineering — which is making its Olympic debut.",
      },
      {
        question: "What is ski mountaineering?",
        answer:
          "Ski mountaineering is a new Olympic sport debuting in 2026. Athletes race uphill on skis with climbing skins, transition to downhill skiing, and carry skis on steep bootpack sections. It combines endurance, technical skiing, and fast transitions across varied mountain terrain.",
      },
      {
        question: "How does the TV schedule grid on this site work?",
        answer:
          "The schedule grid shows all Olympic broadcasts on a timeline. Switch between TV Schedule view (grouped by network) and All Events view (grouped by sport). Events are color-coded by sport, and you can filter by specific sports using the pills above the grid. Scroll horizontally to move through all 16 days, or use the date picker to jump to a specific day.",
      },
    ],
  },
]

export default function FaqPage() {
  // Generate JSON-LD from FAQ data
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqData.flatMap((section) =>
      section.questions.map((q) => ({
        "@type": "Question",
        name: q.question,
        acceptedAnswer: {
          "@type": "Answer",
          text: q.answer,
        },
      }))
    ),
  }

  return (
    <main className="min-h-screen bg-background">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <Header />
      <div className="mx-auto px-4 py-4 max-w-4xl">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-primary hover:underline mb-6"
        >
          <ChevronLeft className="h-4 w-4" />
          Back to Schedule
        </Link>

        <h1 className="text-2xl font-bold text-foreground mb-2">
          Frequently Asked Questions
        </h1>
        <p className="text-muted-foreground mb-8">
          Everything you need to know about watching the 2026 Winter Olympics
        </p>

        {faqData.map((section, sectionIndex) => (
          <div key={section.section}>
            <h2 className="text-lg font-semibold text-foreground mt-8 mb-4">
              {section.section}
            </h2>
            <Accordion type="multiple" className="space-y-2">
              {section.questions.map((item, questionIndex) => (
                <AccordionItem
                  key={`${sectionIndex}-${questionIndex}`}
                  value={`${sectionIndex}-${questionIndex}`}
                  className="border border-border rounded-lg px-4 bg-card"
                >
                  <AccordionTrigger className="text-foreground">
                    {item.question}
                  </AccordionTrigger>
                  <AccordionContent>
                    <p className="text-muted-foreground leading-relaxed">
                      {item.answer}
                    </p>
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </div>
        ))}
      </div>
      <Footer />
    </main>
  )
}
