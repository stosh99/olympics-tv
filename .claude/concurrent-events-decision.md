# Concurrent Events Display - Decision Document

**Session Date:** February 6, 2026
**Status:** Planning Phase - Three Approaches Identified
**Next Step:** Select preferred approach and implement

---

## Session Summary

Fixed three UI regressions in the Olympics TV schedule grid:
1. ✅ "View Selected" button - restored always-visible behavior (was conditionally hidden)
2. ✅ Event box content - restored three-field display (Sport, Event name, Summary)
3. ✅ Legend - removed "Faded = Replay" caption (LIVE/REPLAY badges now in event boxes)

Identified critical issue: With infinite scroll across 19 days, how to handle Peacock's 30 concurrent events?

---

## The Problem

**Current Architecture:**
- Grid displays 19 days of Olympics schedule horizontally (infinite scroll)
- Events are positioned absolutely based on start/end times
- Each network can have multiple concurrent events requiring multiple rows

**Data Analysis Results:**
```
Network             Max Concurrent Events
─────────────────────────────────────────
Peacock/Streaming         30
CNBC                       5
NBC                        2
USA                        1
GOLD ZONE                  1
```

**The Dilemma:**
- Static rows for Peacock (30 rows) = massive vertical space waste
- Dynamic rows = potential jarring UX as rows appear/disappear during scroll
- Need middle ground solution

---

## Solution: Cap Peacock at 5 Rows

Instead of showing all 30 concurrent events, cap display at 5 (matching CNBC's peak).

**Decision Deferred:** Which 5 of 30? (tier, chronological, priority - decide later)

---

## Three Approaches Under Consideration

### **Approach 1: Static Capped Rows**

**How it works:**
- Pre-compute max concurrent per network across entire 19-day range
- Cap at 5 rows per network
- Create rows upfront (once, never change)
- Events flow in/out as user scrolls through time

**Implementation:**
- Calculate max concurrent once when component mounts
- Create `<NetworkRow>` components based on calculation
- No row add/remove logic needed

**Pros:**
- ✅ Rock-solid stable UX
- ✅ No layout shifts
- ✅ Matches original single-day behavior
- ✅ Simple implementation

**Cons:**
- ❌ Some unused rows at off-peak times
- ❌ Vertical space not optimized
- ❌ Feb 4 might have 5 concurrent, Feb 10 might have 1 (3 wasted rows)

**Best for:** Users who prioritize stability and consistency

---

### **Approach 2: Day-Based Dynamic Rows** ⭐ (Recommended)

**How it works:**
- Divide 19 days into 19 daily blocks
- For each day, calculate max concurrent per network (capped at 5)
- Create rows based on that day's max
- When leftmost visible column changes to new day, adjust row count
- Use fade/transition for smooth visual change

**Implementation:**
- Track which day is in leftmost column
- When day changes, recalculate max concurrent for that day
- Animate row height changes (not instant add/remove)
- Can use `useEffect` watching the selected date

**Pros:**
- ✅ Natural boundaries (days, not arbitrary time blocks)
- ✅ Predictable transitions (only at day changes)
- ✅ Space-efficient (no wasted rows per day)
- ✅ Makes sense to users ("New day, new layout")
- ✅ Less jarring than constant updates
- ✅ Balances efficiency and UX

**Cons:**
- ⚠️ Rows do add/remove (but predictably)
- ⚠️ More complex than static approach
- ⚠️ Animation needed for smooth transition

**Best for:** Balanced approach - efficiency + UX stability

---

### **Approach 3: Viewport-Based Dynamic Rows**

**How it works:**
- Calculate concurrent events in visible viewport ± X hours
- Rows update constantly as user scrolls
- Always show only what's needed (most space-efficient)
- Cap at 5 rows

**Implementation:**
- Track viewport position
- For each visible time range, calculate concurrent
- Update rows on every scroll
- Could debounce for ~100ms smoothing

**Pros:**
- ✅ Most space-efficient
- ✅ Zero wasted rows
- ✅ Responsive to actual content

**Cons:**
- ❌ Rows changing during scroll (jarring)
- ❌ Most complex implementation
- ❌ Poor UX if rows pop in/out constantly
- ❌ User can't predict layout changes

**Best for:** Space optimization above all else

---

## Comparison Matrix

| Criteria | Approach 1 | Approach 2 | Approach 3 |
|----------|-----------|-----------|-----------|
| **Stability** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **Space Efficiency** | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Implementation Complexity** | ⭐⭐⭐⭐⭐ (easiest) | ⭐⭐⭐ | ⭐⭐ |
| **UX Smoothness** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **Predictability** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐ |

---

## Recommendation

**Approach 2 (Day-Based Dynamic)** appears optimal:
- Not over-engineered (Approach 1 wastes space unnecessarily)
- Not over-complicated (Approach 3 too jarring)
- Natural boundaries that users understand
- Smooth transitions with animation
- Space-efficient without sacrificing UX

---

## Next Steps

1. **Decision:** Select preferred approach
2. **Refinement:** If Approach 2, define transition animation
3. **Implementation:**
   - Calculate concurrent events per day per network
   - Implement row adjustment logic
   - Test smooth transitions
   - Verify no layout shift during scroll
4. **Polish:**
   - Choose which 5 of 30 Peacock events to show
   - Document row priority logic
   - Test on various devices/sizes

---

## Related Code Files

**Current changes (Session 17):**
- `/home/stosh99/PycharmProjects/olympics-tv/winter-olympics-tv-scheduleV0/components/schedule-grid.tsx`
  - Lines 631-644: Restored "View Selected" button
  - Lines 771-801: Three-field event box display
  - Lines 867-872: Simplified legend

**Database Query Results:**
```sql
SELECT
  network_name,
  MAX(concurrent_count) as max_concurrent
FROM (
  -- Overlapping events calculation
) t
GROUP BY network_name
ORDER BY max_concurrent DESC;
```

---

## Decision Checkpoint

**User needs to decide:**
- [ ] Approach 1 (Static - safest)
- [ ] Approach 2 (Day-Based - recommended)
- [ ] Approach 3 (Viewport - most efficient)

Once selected, implementation can proceed immediately.
