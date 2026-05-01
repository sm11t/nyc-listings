---
name: Schedule vs Housing matrix
type: decision-matrix
purpose: The bridge file. Maps "how many days/week on campus" → "what commute is acceptable" → "which housing tiers are viable". Read this before signing a lease.
created: 2026-04-25
updated: 2026-04-25
status: stub-pending-research
tags: [housing, decision-matrix, fall-2026]
---

# Schedule vs Housing Matrix

**Why this file exists:** Course slate and lease are coupled. A 5-day-a-week slate makes a 60-min commute a daily 2-hour tax. A 2-day-a-week slate makes the same commute a weekly 4-hour tax — and unlocks $300+/mo of rent savings. Decide together, not separately.

## The matrix

| On-campus days/week | Max acceptable one-way commute | Viable tiers | Annual commute hours (52 wks) | Rent budget freed up |
|---|---|---|---|---|
| **5 days** | 25 min | A only | ~217 hrs | $0 — pay top of band |
| **4 days** | 35 min | A + best of B | ~245 hrs | ~$50/mo savings vs A |
| **3 days** | 45 min | A + B | ~234 hrs | ~$100/mo savings |
| **2 days** | 75 min | A + B + C + D | ~260 hrs | ~$200-300/mo savings vs A |
| **1 day** | 90 min | All tiers, optimize for cost + life | ~156 hrs | ~$300+/mo savings |
| **0 days (fully online)** | n/a | Optimize purely for life + ecosystem | 0 | Maximum |

## Decision rule

**1.** Build the candidate slate in [[Fall-2026-Plan]] first.
**2.** Count distinct on-campus days the slate creates (e.g., "Mon + Wed evening lectures + Thu in-person discussion = 3 days").
**3.** Look up the row in the matrix above → that's the housing constraint.
**4.** Filter [[Neighborhoods]] table to viable tiers, rank by total cost + ecosystem proximity ([[NYC-MOC]] meetups within walking distance).

## Bonus: cluster the schedule on purpose

Two slates with identical credit count can have different on-campus footprints:
- **Slate A:** Mon/Wed/Fri evening lectures = **3 days/week** → max commute 45 min → tiers A+B
- **Slate B:** Tue/Thu evening lectures = **2 days/week** → max commute 75 min → tiers A+B+C+D

If the courses are equally aligned, **always pick the slate that clusters fewer days**. Cheaper rent compounds; algorithms knowledge does not.

## Edge cases to watch for

- **Hybrid courses with mandatory in-person discussion**: a "Tue evening lecture + Thu in-person lab" course counts as **2 days**, not 1.
- **Late lectures (8-9 pm end times)**: late-night subway from Tier C/D adds 15-20 min vs daytime; safety perception varies (see neighborhood notes).
- **Lab/research opportunities**: if I land an RA role with a Priority-3 faculty (see [[intelligence/people/nyu-tandon/INDEX|faculty INDEX]]), that's +1 day on campus → re-run the matrix.
- **NYU-MOC events**: AGI House NYC, AI Tinkerers, MCP NYC events from [[NYC-MOC]] are in Manhattan — Tier A/B are walking-distance to the L/F/A trains and to BAM/Brooklyn AI scene; Tier D is a hike.

## Connections

**inputs:** [[Fall-2026-Plan]] · [[Neighborhoods]]
**uses-rubric:** [[interests/Interest-Profile|Interest-Profile]]
**ecosystem:** [[NYC-MOC]]
**parent:** [[study/README|study/README]]
