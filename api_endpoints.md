# Olympics.com API Reference

## Schedule Endpoint (Primary)

**URL Pattern:**
```
https://www.olympics.com/wmr-owg2026/schedules/api/ENG/schedule/lite/day/{YYYY-MM-DD}
```

**Example:**
```
GET /wmr-owg2026/schedules/api/ENG/schedule/lite/day/2026-02-08
```

**Response Structure:**
```json
{
  "units": [
    {
      "disciplineName": "Curling",
      "disciplineCode": "CUR",
      "disciplineId": "...",
      
      "eventName": "Mixed Doubles",
      "eventCode": "CURXD",
      "eventId": "...",
      "eventType": "TEAM",
      
      "phaseName": "Round Robin",
      "phaseCode": "CURRR",
      "phaseId": "...",
      "phaseType": "...",
      
      "eventUnitName": "Session 1",
      "eventUnitType": "...",
      "unitNum": 1,
      
      "startDate": "2026-02-08T09:05:00+01:00",
      "endDate": "2026-02-08T11:00:00+01:00",
      "olympicDay": 1,
      
      "venue": "CCP",
      "venueDescription": "Cortina Curling Centre",
      "venueLongDescription": "Cortina Curling Centre",
      "location": "COR",
      "locationDescription": "Cortina d'Ampezzo",
      
      "medalFlag": 0,
      "status": "SCHEDULED",
      "statusDescription": "Scheduled",
      "sessionCode": "...",
      
      "competitors": [
        {
          "noc": "GBR",
          "code": "CURXD-GBR",
          "name": "Great Britain",
          "order": 1
        },
        {
          "noc": "NOR",
          "code": "CURXD-NOR",
          "name": "Norway",
          "order": 2
        }
      ]
    }
  ]
}
```

---

## Key Fields

| Field | Description |
|-------|-------------|
| `disciplineName/Code` | Sport (Curling, Alpine Skiing, etc.) |
| `eventName/Code/Type` | Specific event, TEAM or INDV |
| `phaseName/Type` | Round Robin, Quarterfinal, Final, etc. |
| `eventUnitName` | Session identifier |
| `startDate/endDate` | ISO 8601 with CET timezone (+01:00) |
| `medalFlag` | 1 if medal ceremony follows |
| `status` | SCHEDULED, RUNNING, FINISHED, etc. |
| `competitors` | Array of teams (NOC) or athletes |

---

## Individual Event Competitors

For individual events (eventType: "INDV"), competitors include athlete details:

```json
"competitors": [
  {
    "unitId": "...",
    "noc": "USA",
    "competitorType": "ATHLETE",
    "code": "1234567",
    "name": "Mikaela SHIFFRIN",
    "order": 1
  }
]
```

---

## Supporting Endpoints

### Disciplines & Events
```
GET /wmr-owg2026/info/api/ENG/disciplinesevents
```
Returns all sports and their events. Use to populate disciplines and events tables.

### National Olympic Committees
```
GET /wmr-owg2026/info/api/ENG/nocs
```
Returns country codes and names.

### Venues
```
GET /wmr-owg2026/info/api/ENG/venues
```
Returns venue details (code, name, location, capacity).

---

## Scraping Strategy

1. **Initial load**: Fetch all dates in Olympics range (Feb 6-22, 2026)
2. **Daily refresh**: Re-fetch current + future dates to catch status changes
3. **Rate limiting**: No auth required, but be respectful (1 req/sec)
4. **Error handling**: API returns empty units array for invalid dates
