# Detailed Session History (Sessions 3-23)

## Session 3 - Feb 4, 2026 (Initial Setup)
✅ Database setup + scrapers built
1. Set up PostgreSQL on localhost:5432
2. Created database schema with 10 tables + 2 views
3. Built olympics.com scraper (olympics_scraper.py)
4. Loaded all Feb 3-22 Olympics data:
   - 17 disciplines, 124 events, 15 venues
   - 628 schedule units, 236 competitors, 964 unit_competitors
   - 30 sync log entries

## Session 4 - Feb 5, 2026 (Header Redesign)
✅ Frontend header optimization
1. Restructured header for horizontal three-zone layout
2. Reduced Olympic rings: 160x80 → 120x60
3. Reduced header height by 50% (~200px → ~100px)
4. Maintained responsive design (desktop/tablet/mobile)

## Session 5 - Feb 5, 2026 (Three-Field Event Display)
✅ Event box redesign with responsive truncation
1. Added three fields to event boxes:
   - Sport (discipline) - 9px uppercase, muted
   - Event (name) - 10px bold
   - Summary - 9px with line-clamp-2 (responsive truncation)
2. Repositioned LIVE/REPLAY badges to top-right corner
3. Full summary in popover on click

## Session 6 - Feb 5, 2026 (Concurrent Event Handling)
✅ Lane assignment algorithm for overlapping events
1. Implemented `assignBandIndices()` algorithm
2. Dynamic row heights: 56px per event band
3. Full-width separators (border-b-2 border-slate-800)
4. All networks support unlimited concurrent events (capped display)

## Session 7 - Feb 5, 2026 (Grid Layout Fix)
✅ Fixed vertical scrollbar + reordered networks
1. Restructured grid: row-based → column-based layout
2. Fixed scroll sync: arrow buttons now scroll header + content together
3. Reordered networks: NBC, USA, CNBC, Peacock, GOLD ZONE
4. Single horizontal scrollbar, no vertical scrollbar

## Session 8 - Feb 5, 2026 (Auto-Scroll)
✅ Auto-scroll to current time on page load
1. Added useEffect to scroll to nearest half-hour slot
2. Time rounding: <15min → :00, 15-44min → :30, 45+min → next :00
3. Only scrolls when viewing today's schedule
4. Smooth animation with 128px slot calculation

## Session 9 - Feb 5, 2026 (View Selected Button)
✅ Fixed button visibility and positioning
1. Changed from conditional rendering to always-visible
2. Removed ml-auto positioning (flows naturally after sports)
3. Disabled state when no sports checked
4. Active state when sports selected and filter on

## Session 10 - Feb 5, 2026 (Grid Precision + Hydration)
✅ 5-minute grid precision + React hydration fix
1. Changed event width: 30-minute → 5-minute precision
2. Fixed hydration error in header (time rendering mismatch)
3. Added `mounted` state to track client-side hydration

## Session 11 - Feb 5, 2026 (Date Display Bug)
✅ Fixed timezone issue in date formatting
1. Problem: Events displayed one day early after 7 PM EST
2. Root cause: `toISOString()` converts to UTC before extracting date
3. Solution: Use `getFullYear()`, `getMonth()`, `getDate()` for local timezone
4. Fixed in: schedule-grid, coming-up-next, whats-on-now

## Session 12 - Feb 5, 2026 (Event Position Precision)
✅ Fixed start time positioning with absolute calculation
1. Problem: 30-minute slot rounding vs 5-minute width precision caused false overlaps
2. Solution: Use absolute positioning from 5:00 AM grid start
3. Formula: `minutesSinceGridStart * (128 / 30)` for pixel offset
4. Result: No more 15-minute shifts, exact positioning

## Session 16 - Feb 6, 2026 (Scroll Listener Debug)
✅ Added debug logging + improved UX with Math.round()
1. Confirmed scroll listener working (React's onScroll prop)
2. Changed Math.floor() → Math.round() for snappier date updates
3. Date now updates at 50% threshold (midpoint of day)
4. Added console logs for debugging scroll events

## Session 18 - Feb 6, 2026 (Concurrent Event System)
✅ Day-based dynamic row heights (5 phases complete)
1. Implemented `calculateMaxConcurrentPerDay()` function
2. Band assignment with greedy algorithm (bands 0-4)
3. Track `leftmostVisibleDate` state for day boundary detection
4. Dynamic row heights: `maxConcurrent * 56px` per row
5. Vertical positioning: `top: bandIndex * 56px`
6. Smooth CSS transitions (0.3s) when row heights change

**Data Summary:**
- Peacock: Cap at 5 rows (280px)
- CNBC: Cap at 5 rows (280px)
- NBC: 2 rows (112px)
- USA: 1 row (56px)
- GOLD ZONE: 1 row (56px)

## Session 19 - Feb 7, 2026 (Band Assignment Refactor + NBC Timezone)
✅ Global band assignment + timezone fix
1. **Band Assignment Fix:**
   - Problem: Events reassigned bands per time-slot (inconsistent positioning)
   - Solution: New `assignBandIndicesForDay()` function assigns globally
   - Events now get persistent band indices before rendering
   - Removed per-time-slot band reassignment

2. **NBC Scraper Timezone Fix:**
   - Problem: Using `America/Chicago` instead of `America/New_York`
   - Solution: Changed line 72 in scrapers/nbc_scraper.py
   - Impact: Events now correctly grouped by Eastern Time
   - Re-scraped all 20 days (Feb 4-23)

## Session 20 - Feb 7, 2026 (Hero Banner + Olympic Rings)
✅ Complete hero banner redesign
1. **Hero Banner Structure:**
   - Full-width blue background (#f0f4f8)
   - Large toggle buttons (44px tall, 14px font)
   - Olympic rings SVG decoration at edges (10% opacity, then 20%, then 25%)
   - Date/timezone controls right-aligned

2. **Ring Visibility Evolution:**
   - Phase 1: 10% opacity (too subtle)
   - Phase 2: 20% opacity (better)
   - Phase 3: 25% opacity (balanced)
   - Then: Removed opacity class for full vibrant color

3. **Spacing Refinement:**
   - Symmetric padding: 122px on both sides (tablet+)
   - 16px gaps: edge→ring, ring→controls
   - Responsive: Mobile stacks, tablet+ full layout
   - Olympic rings: Hidden on mobile, visible on tablet+

## Session 21 - Feb 7, 2026 (All Events Multi-Row Bug)
✅ Critical concurrent events bug fix
1. **Problem:** Multiple concurrent events in All Events view appeared in different sport rows
2. **Root Cause:** Line 411 used TV grid data instead of Olympic schedule data
3. **The Bug:**
   ```typescript
   // WRONG: TV data has network keys ("NBC", "Peacock")
   const gridEvents = tvToGridEvents(tvRange)
   const maxConcurrent = calculateMaxConcurrentPerDay(gridEvents, allDates)
   ```
4. **The Fix:**
   ```typescript
   // CORRECT: Olympic data has sport keys ("Curling", "Figure Skating")
   const gridEvents = scheduleToGridEvents(schedRange)
   const maxConcurrent = calculateMaxConcurrentPerDay(gridEvents, allDates)
   ```
5. **Impact:** Row heights now calculate correctly, all concurrent events stack properly

## Session 22 - Feb 7, 2026 (Row Height Timing Bug)
✅ Fixed when row heights recalculate
1. **Problem:** Row heights recalculated at ~2:30 PM (mid-day) instead of day boundary
2. **Root Cause:** Math.round() switched dates at 50% threshold:
   - 50% of 4,864px = 2,432px = 19 slots = 9.5 hours
   - 5:00 AM + 9.5 hours = 2:30 PM ❌
3. **Solution:** Revert to Math.floor() for day boundary switching:
   - Math.floor() switches exactly when new day's 5:00 AM reaches left edge
4. **Historical Note:** Session 16 changed to Math.round() for snappier UX, but this broke the day-based row height system
5. **Result:** Row heights now recalculate naturally at 5:00 AM boundary

## Session 23 - Feb 7, 2026 (Hero Banner Styling)
✅ Final hero banner styling polish
1. Changed hero banner background: light gray-blue → light blue (bg-blue-200)
2. Added bg-blue-200 to entire section container (hero + sports + grid)
3. Result: Cohesive blue section with good contrast against white event cards
4. Professional appearance with unified design

## Implementation Reference

### Key Functions & Files
**schedule-grid.tsx:**
- Line 170-217: `assignBandIndicesForDay()` - Global band assignment
- Line 281-310: `handleScroll()` - Scroll listener with date sync
- Line 533-537: `getRowHeight()` - Dynamic row height calculation
- Line 895-900: Event box styling with vertical stacking

**schedule-data.ts:**
- Line 7: NETWORKS array order: ["NBC", "USA", "CNBC", "Peacock", "GOLD ZONE"]

**lib/api.ts:**
- Lines 113-118: `formatDateParam()` - Local timezone date formatting

### Data Structures
- **GridEvent Interface:** Added `bandIndex` property for vertical positioning
- **Map Structure:** `Map<NetworkOrDiscipline, Map<Date, GridEvent[]>>`
- **Row Heights:** `maxConcurrent * 56px` per network/sport

### CSS Classes Used
- `line-clamp-1`, `line-clamp-2` - Responsive text truncation
- `duration-300 ease-in-out` - Smooth row height transitions
- `bg-blue-200` - Hero section background
- `border-slate-800` - Full-width row separators
