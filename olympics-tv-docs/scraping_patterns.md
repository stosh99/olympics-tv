# NBC Scraping Patterns

## Status
**Investigation needed** - NBC.com structure not yet analyzed.

---

## Expected Data Structure

### Single Event Broadcasts
Maps 1:1 to olympics.com schedule units:
- Network (NBC, USA, CNBC, Peacock, E!)
- Air time (start/end)
- Live vs replay indicator
- Event reference

### Recap Shows
Cover multiple events, typically replays:
- "Afternoon Recap" / "Evening Recap" / "Primetime"
- Description lists 3-5+ sports covered
- Need AI agent to parse description → extract sports

**Example description:**
> "Recap coverage featuring Alpine Skiing Men's Downhill, Figure Skating Ice Dance, and Freestyle Skiing Women's Slopestyle highlights"

**Parsed output:**
```json
["Alpine Skiing", "Figure Skating", "Freestyle Skiing"]
```

---

## Likely URL Patterns

Check these during investigation:
```
https://www.nbc.com/olympics/schedule
https://www.nbcolympics.com/schedule
https://www.peacocktv.com/sports/olympics
```

---

## Scraping Approach

### Option A: Direct HTML Scraping
- Use requests + BeautifulSoup
- Parse schedule tables/grids
- Handle JavaScript-rendered content with Playwright if needed

### Option B: API Discovery
- Check network tab for XHR requests
- NBC may have internal API similar to olympics.com
- Preferred if available (more reliable)

### Option C: Hybrid
- Playwright to render page
- Extract structured data from DOM
- Fall back to description parsing

---

## Phase 2: Nightly Sync

### Schedule
```cron
0 3 * * * /path/to/nightly_sync.py  # 3 AM daily
```

### Sync Logic
```python
def nightly_sync():
    # 1. Fetch current NBC schedule
    new_data = scrape_nbc_schedule()
    
    # 2. Compare with existing
    existing = db.get_broadcasts(air_start >= today)
    
    # 3. Diff and update
    for broadcast in new_data:
        if broadcast.id in existing:
            if broadcast != existing[broadcast.id]:
                db.update_broadcast(broadcast)
                log_change('updated', broadcast)
        else:
            db.insert_broadcast(broadcast)
            log_change('inserted', broadcast)
    
    # 4. Mark removed broadcasts
    for old in existing:
        if old.id not in new_data:
            db.mark_removed(old)
            log_change('removed', old)
```

### Change Tracking
Store in sync_log table:
- Timestamp
- Records processed/inserted/updated
- Any errors

---

## AI Parsing for Recap Shows

### Prompt Template
```
Extract the sports mentioned in this Olympics broadcast description.
Return as JSON array of sport names matching these disciplines:
[Alpine Skiing, Biathlon, Bobsled, Cross-Country Skiing, Curling, 
Figure Skating, Freestyle Skiing, Ice Hockey, Luge, Nordic Combined,
Short Track Speed Skating, Skeleton, Ski Jumping, Snowboard, Speed Skating]

Description: "{description}"

Output: ["Sport1", "Sport2", ...]
```

### Implementation
```python
async def parse_recap_sports(description: str) -> list[str]:
    response = await anthropic.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=100,
        messages=[{"role": "user", "content": PROMPT.format(description=description)}]
    )
    return json.loads(response.content[0].text)
```

---

## Networks to Track

| Network | Type | Notes |
|---------|------|-------|
| NBC | Broadcast | Primetime coverage |
| USA | Cable | Daytime events |
| CNBC | Cable | Overflow coverage |
| E! | Cable | Limited coverage |
| Peacock | Streaming | All events, live |

---

## TODO
- [ ] Investigate NBC.com page structure
- [ ] Identify API endpoints if available
- [ ] Test scraping approach
- [ ] Build initial scraper
- [ ] Implement nightly sync job
