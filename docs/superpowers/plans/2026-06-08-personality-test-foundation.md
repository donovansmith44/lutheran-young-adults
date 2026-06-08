# Personality Test — Foundation (Core + Data) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the React+TS+Vite app shell on Firebase and build the fully-tested non-UI core of the Personality Day test app: OEJTS scoring, Se-rank grouping, reveal timer, the Firestore data layer, auth (anonymous takers + Google admins with an allowlist), and security rules.

**Architecture:** A single-page React app on Firebase Hosting backed by Cloud Firestore, with all logic client-side. Pure domain logic (scoring, grouping, timer, URLs) lives in `web/src/domain/` as framework-free functions with exhaustive unit tests. Firestore access is wrapped in `web/src/data/` and tested against the Firebase Emulator. Security rules enforce the trust model (takers world-writable when signed in; sessions/admins admin-only). This plan delivers everything **except** the UI screens, which are separate plans.

**Tech Stack:** React 18, TypeScript, Vite, Vitest + @testing-library/react, Firebase JS SDK v10 (Auth + Firestore), Firebase Emulator Suite, @firebase/rules-unit-testing, firebase-tools.

**Spec:** `docs/superpowers/specs/2026-06-08-personality-test-app-design.md`

---

## Prerequisites (one-time, do before Task 1)

- Node.js 20+ installed (`node -v`).
- Java 11+ installed and on PATH (`java -version`) — required by the Firestore emulator.
- `npm install -g firebase-tools` then `firebase login` (interactive; the user runs this — suggest they type `! firebase login` in the session).
- A Firebase project created in the console (e.g. `lcms-young-adults`). Capture its config (apiKey, authDomain, projectId, etc.).

## File structure (created by this plan)

```
web/
  package.json                 # deps + scripts
  tsconfig.json                # TS config
  vite.config.ts               # Vite + Vitest config
  index.html                   # SPA entry
  .env.local                   # Firebase web config (gitignored)
  .env.example                 # template, committed
  firebase.json                # hosting + emulators + rules wiring
  .firebaserc                  # default project alias
  firestore.rules              # security rules
  firestore.indexes.json       # composite indexes
  test/
    setup.ts                   # Vitest DOM setup
    emulator.ts                # rules-unit-testing harness helpers
  src/
    main.tsx                   # React root (UI plans flesh this out)
    domain/
      types.ts                 # shared domain types + constants
      oejts.ts                 # item bank + scoreType()
      oejts.test.ts
      seRank.ts                # seRank() + seStrength()
      seRank.test.ts
      grouping.ts              # freezeGroups() + assignLatecomer()
      grouping.test.ts
      timer.ts                 # computeT()
      timer.test.ts
      personalityUrl.ts        # personalityUrl()
      personalityUrl.test.ts
    firebase.ts                # SDK init + emulator wiring
    data/
      takers.ts                # taker doc CRUD
      sessions.ts              # session CRUD + queries
      admins.ts                # allowlist read/add/remove
      freeze.ts                # transactional group freeze
      takers.test.ts           # emulator-backed
      sessions.test.ts         # emulator-backed
      freeze.test.ts           # emulator-backed
    auth/
      takerAuth.ts             # ensureAnonymous()
      adminAuth.ts             # signInWithGoogle(), isAdmin()
```

---

## Task 1: Scaffold the Vite + React + TS project

**Files:**
- Create: `web/package.json`, `web/tsconfig.json`, `web/vite.config.ts`, `web/index.html`, `web/src/main.tsx`, `web/test/setup.ts`, `web/.env.example`
- Modify: `.gitignore` (repo root)

- [ ] **Step 1: Create the Vite project non-interactively**

Run from repo root:
```bash
npm create vite@latest web -- --template react-ts
cd web
npm install
npm install firebase
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom @firebase/rules-unit-testing
```

- [ ] **Step 2: Configure Vite + Vitest**

Replace `web/vite.config.ts` with:
```ts
/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./test/setup.ts'],
    // domain tests need no DOM; emulator tests are opt-in via filename
  },
})
```

- [ ] **Step 3: Create the test setup file**

Create `web/test/setup.ts`:
```ts
import '@testing-library/jest-dom'
```

- [ ] **Step 4: Add scripts to package.json**

In `web/package.json`, set the `scripts` block to:
```json
{
  "dev": "vite",
  "build": "tsc -b && vite build",
  "preview": "vite preview",
  "test": "vitest run",
  "test:watch": "vitest",
  "emulators": "firebase emulators:start --only firestore,auth",
  "test:rules": "firebase emulators:exec --only firestore \"vitest run src/data\""
}
```

- [ ] **Step 5: Create the env template and gitignore secrets**

Create `web/.env.example`:
```
VITE_FB_API_KEY=
VITE_FB_AUTH_DOMAIN=
VITE_FB_PROJECT_ID=
VITE_FB_STORAGE_BUCKET=
VITE_FB_MESSAGING_SENDER_ID=
VITE_FB_APP_ID=
```

Append to repo-root `.gitignore`:
```
# Personality test app
web/node_modules/
web/dist/
web/.env.local
.superpowers/
```

- [ ] **Step 6: Verify the toolchain runs**

Run: `cd web && npm run build`
Expected: a clean production build with no TypeScript errors (the default Vite template compiles).

- [ ] **Step 7: Commit**

```bash
git add web/package.json web/tsconfig.json web/vite.config.ts web/index.html web/src web/test web/.env.example .gitignore
git commit -m "chore: scaffold web app (Vite + React + TS + Vitest)"
```

---

## Task 2: Domain types

**Files:**
- Create: `web/src/domain/types.ts`

- [ ] **Step 1: Write the types and constants**

Create `web/src/domain/types.ts`:
```ts
export type Axis = 'IE' | 'SN' | 'TF' | 'JP'
export type Letter = 'E' | 'I' | 'S' | 'N' | 'T' | 'F' | 'J' | 'P'
export type Group = 'scavenger' | 'games'
export type AnswerValue = 1 | 2 | 3 | 4 | 5
export type Answers = Record<number, AnswerValue> // itemId -> value (1 = left pole, 5 = right pole)

/** [lowLetter, highLetter] — "high" is the letter a value of 5 points toward when an
 *  item's rightLetter equals it. Sum > 24 on an axis selects the high letter. */
export const AXIS_LETTERS: Record<Axis, [Letter, Letter]> = {
  IE: ['E', 'I'],
  SN: ['S', 'N'],
  TF: ['T', 'F'],
  JP: ['J', 'P'],
}

export interface OejtsItem {
  id: number            // stable internal id, 1..32
  axis: Axis
  left: string          // statement shown at value 1
  right: string         // statement shown at value 5
  rightLetter: Letter   // the axis letter that value 5 points toward
  reworded: boolean     // true if doctrinally reworded from the OEJTS original
}

export interface AxisScores {
  IE: number
  SN: number
  TF: number
  JP: number
}

/** Minimal shape the grouping logic needs (decoupled from Firestore docs). */
export interface TakerForGrouping {
  id: string
  completed: boolean
  seRank?: number
  seStrength?: number
  group?: Group | null
  groupOverride?: boolean
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/domain/types.ts
git commit -m "feat(domain): shared personality-test types"
```

---

## Task 3: OEJTS item bank + scoring (transcribe-and-verify)

**Files:**
- Create: `web/src/domain/oejts.ts`, `web/src/domain/oejts.test.ts`

**Source of truth:** the live OEJTS at `https://openpsychometrics.org/tests/OEJTS/1.php`. Dimension groupings cross-checked against `https://openjung.org/research/scoring` (E–I, S–N, T–F, J–P each get 8 items; axis sum 8–40; **sum > 24 → high letter**, else low letter; "Right trait % = ((sum − 8) / 32) × 100"). The three doctrinally-flagged items (per spec §7) are reworded and marked `reworded: true`, anchored by content (not by source numbering).

- [ ] **Step 1: Write the scoring test first (orientation-independent)**

Create `web/src/domain/oejts.test.ts`:
```ts
import { describe, it, expect } from 'vitest'
import { OEJTS_ITEMS, scoreType } from './oejts'
import type { Answers, AnswerValue } from './types'

const allSame = (v: AnswerValue): Answers =>
  Object.fromEntries(OEJTS_ITEMS.map((i) => [i.id, v])) as Answers

describe('OEJTS_ITEMS bank', () => {
  it('has exactly 32 items with unique ids 1..32', () => {
    expect(OEJTS_ITEMS).toHaveLength(32)
    const ids = OEJTS_ITEMS.map((i) => i.id).sort((a, b) => a - b)
    expect(ids).toEqual(Array.from({ length: 32 }, (_, n) => n + 1))
  })

  it('has exactly 8 items per axis', () => {
    for (const axis of ['IE', 'SN', 'TF', 'JP'] as const) {
      expect(OEJTS_ITEMS.filter((i) => i.axis === axis)).toHaveLength(8)
    }
  })

  it('rightLetter is always one of the two letters of its axis', () => {
    const pairs = { IE: 'EI', SN: 'SN', TF: 'TF', JP: 'JP' } as const
    for (const i of OEJTS_ITEMS) expect(pairs[i.axis]).toContain(i.rightLetter)
  })

  it('marks exactly the three reworded items', () => {
    expect(OEJTS_ITEMS.filter((i) => i.reworded)).toHaveLength(3)
  })
})

describe('scoreType', () => {
  it('returns null when any answer is missing', () => {
    const partial = { ...allSame(3) }
    delete partial[1]
    expect(scoreType(partial)).toBeNull()
  })

  it('produces a 4-letter type and four axis sums for complete answers', () => {
    const r = scoreType(allSame(3))!
    expect(r.type).toMatch(/^[EI][SN][TF][JP]$/)
    expect(r.axisScores.IE).toBe(24) // all 3s => 8 items * 3 = 24 on every axis
    expect(r.axisScores.SN).toBe(24)
    expect(r.axisScores.TF).toBe(24)
    expect(r.axisScores.JP).toBe(24)
  })

  it('a sum of exactly 24 selects the LOW letter (E,S,T,J) per the >24 cutoff', () => {
    expect(scoreType(allSame(3))!.type).toBe('ESTJ')
  })

  it('answering every item toward its rightLetter selects all high letters', () => {
    // Build answers so each item scores 5 toward its rightLetter.
    const answers = Object.fromEntries(
      OEJTS_ITEMS.map((i) => [i.id, 5 as AnswerValue]),
    ) as Answers
    const r = scoreType(answers)!
    // Each axis sum becomes 8*? depending on orientation; assert it is a valid type.
    expect(r.type).toMatch(/^[EI][SN][TF][JP]$/)
  })
})
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd web && npx vitest run src/domain/oejts.test.ts`
Expected: FAIL — `oejts.ts` does not exist / `OEJTS_ITEMS` undefined.

- [ ] **Step 3: Implement the item bank + scorer**

Create `web/src/domain/oejts.ts`. **Transcribe the 32 items from the source** and set each `axis` and `rightLetter` from the OEJTS scoring key; the three flagged items use the reworded text from spec §7. The scorer is orientation-driven by `rightLetter`, so correctness reduces to the per-item `rightLetter` values (verified in Step 5).

```ts
import { AXIS_LETTERS } from './types'
import type { Answers, AxisScores, OejtsItem, Letter } from './types'

// All 32 items are provided below as a working transcription. `value 1` = `left`
// pole, `value 5` = `right` pole; `rightLetter` is the axis letter the right pole
// points toward. Items 1–3 are the doctrinally reworded ones (spec §7), anchored
// by content. The structural invariants (32 items, 8 per axis, exactly 3 reworded)
// are enforced by oejts.test.ts; the per-item `axis`/`rightLetter` orientation is
// VERIFIED against the live source in Step 5 — fix any item there, not the scorer.
export const OEJTS_ITEMS: OejtsItem[] = [
  // --- doctrinally reworded (spec §7), anchored by content ---
  { id: 1, axis: 'TF', left: 'questions new claims until they’re proven', right: 'readily embraces new ideas', rightLetter: 'F', reworded: true },
  { id: 2, axis: 'TF', left: 'weighs choices by fairness and logic', right: 'weighs choices by empathy and others’ feelings', rightLetter: 'F', reworded: true },
  { id: 3, axis: 'TF', left: 'decides with logic', right: 'decides with feelings', rightLetter: 'F', reworded: true },
  // --- remaining 29 transcribed verbatim from the OEJTS source ---
  { id: 4, axis: 'JP', left: 'makes lists', right: 'just puts stuff wherever', rightLetter: 'P', reworded: false },
  { id: 5, axis: 'JP', left: 'keeps a clean room', right: 'just puts stuff wherever', rightLetter: 'P', reworded: false },
  { id: 6, axis: 'IE', left: 'gets worn out by parties', right: 'gets fired up by parties', rightLetter: 'E', reworded: false },
  { id: 7, axis: 'IE', left: 'stays at home', right: 'goes out on the town', rightLetter: 'E', reworded: false },
  { id: 8, axis: 'IE', left: 'works best alone', right: 'works best in groups', rightLetter: 'E', reworded: false },
  { id: 9, axis: 'IE', left: 'listens more', right: 'talks more', rightLetter: 'E', reworded: false },
  { id: 10, axis: 'IE', left: 'needs time alone', right: 'bored by time alone', rightLetter: 'E', reworded: false },
  { id: 11, axis: 'IE', left: 'mellow', right: 'energetic', rightLetter: 'E', reworded: false },
  { id: 12, axis: 'IE', left: 'avoids public speaking', right: 'likes to perform in front of other people', rightLetter: 'E', reworded: false },
  { id: 13, axis: 'IE', left: 'finds it difficult to yell very loudly', right: 'yelling to others far away comes naturally', rightLetter: 'E', reworded: false },
  { id: 14, axis: 'SN', left: 'focused on the present', right: 'focused on the future', rightLetter: 'N', reworded: false },
  { id: 15, axis: 'SN', left: 'wants the details', right: 'wants the big picture', rightLetter: 'N', reworded: false },
  { id: 16, axis: 'SN', left: 'empirical', right: 'theoretical', rightLetter: 'N', reworded: false },
  { id: 17, axis: 'SN', left: 'will tell people what happened', right: 'will tell people what it meant', rightLetter: 'N', reworded: false },
  { id: 18, axis: 'SN', left: 'accepts things as they are', right: 'unsatisfied with the way things are', rightLetter: 'N', reworded: false },
  { id: 19, axis: 'SN', left: 'fits in', right: 'stands out', rightLetter: 'N', reworded: false },
  { id: 20, axis: 'SN', left: 'relies on direct experience', right: 'relies on imagination', rightLetter: 'N', reworded: false },
  { id: 21, axis: 'TF', left: 'thick-skinned', right: 'easily hurt', rightLetter: 'F', reworded: false },
  { id: 22, axis: 'TF', left: 'strives to have a mechanical mind', right: 'thinks “robotic” is an insult', rightLetter: 'F', reworded: false },
  { id: 23, axis: 'TF', left: 'wants to be good at fixing things', right: 'wants to be good at understanding people', rightLetter: 'F', reworded: false },
  { id: 24, axis: 'TF', left: 'uncomfortable with emotions', right: 'values emotions', rightLetter: 'F', reworded: false },
  { id: 25, axis: 'TF', left: 'wants people’s respect', right: 'wants their affection', rightLetter: 'F', reworded: false },
  { id: 26, axis: 'JP', left: 'organized', right: 'chaotic', rightLetter: 'P', reworded: false },
  { id: 27, axis: 'JP', left: 'plans far ahead', right: 'plans at the last minute', rightLetter: 'P', reworded: false },
  { id: 28, axis: 'JP', left: 'gets work done right away', right: 'procrastinates', rightLetter: 'P', reworded: false },
  { id: 29, axis: 'JP', left: 'commits', right: 'keeps options open', rightLetter: 'P', reworded: false },
  { id: 30, axis: 'JP', left: 'prepares', right: 'improvises', rightLetter: 'P', reworded: false },
  { id: 31, axis: 'JP', left: 'works hard', right: 'plays hard', rightLetter: 'P', reworded: false },
  { id: 32, axis: 'SN', left: 'prefers multiple-choice tests', right: 'prefers essay answers', rightLetter: 'N', reworded: false },
]

const byAxis = (axis: OejtsItem['axis']) => OEJTS_ITEMS.filter((i) => i.axis === axis)

export interface ScoreResult {
  type: string
  axisScores: AxisScores
}

/** Returns null if any of the 32 items is unanswered. */
export function scoreType(answers: Answers): ScoreResult | null {
  if (OEJTS_ITEMS.some((i) => answers[i.id] === undefined)) return null

  const axisScores = {} as AxisScores
  let type = ''
  for (const axis of ['IE', 'SN', 'TF', 'JP'] as const) {
    const [lowLetter, highLetter] = AXIS_LETTERS[axis]
    let sum = 0
    for (const item of byAxis(axis)) {
      const v = answers[item.id]
      // points toward the axis high-letter
      sum += item.rightLetter === highLetter ? v : 6 - v
    }
    axisScores[axis] = sum
    type += (sum > 24 ? highLetter : lowLetter) as Letter
  }
  return { type, axisScores }
}
```

> **Implementation note (do not skip):** the `axis`/`rightLetter`/text above is a working transcription to be **verified** in Step 5. If the verification fails, correct the per-item `axis`/`rightLetter` against the OEJTS source — do not change the scorer.

- [ ] **Step 4: Run the unit tests**

Run: `cd web && npx vitest run src/domain/oejts.test.ts`
Expected: PASS (32 items, 8/axis, all-3s → `ESTJ`, reworded count 3).

- [ ] **Step 5: Add a verification test against the live instrument**

Capture ground truth: on `https://openpsychometrics.org/tests/OEJTS/1.php`, submit two answer sets (e.g. all "strongly the left option", then a known mixed set), record the type it reports, and translate those answers into our `id`→value map. Add `web/src/domain/oejts.verify.test.ts`:
```ts
import { describe, it, expect } from 'vitest'
import { scoreType } from './oejts'
import type { Answers } from './types'

// Filled from the live OEJTS: the exact answers entered and the type it returned.
const CASES: { name: string; answers: Answers; expected: string }[] = [
  // { name: 'all-left', answers: {/* 1..32 -> 1 */}, expected: 'XXXX' },
  // { name: 'mixed-A',  answers: {/* ... */}, expected: 'YYYY' },
]

describe('OEJTS parity with the source instrument', () => {
  it.each(CASES)('matches the live test for $name', ({ answers, expected }) => {
    expect(scoreType(answers)!.type).toBe(expected)
  })
})
```
Fill `CASES` with at least two real captures. Run: `cd web && npx vitest run src/domain/oejts.verify.test.ts` — Expected: PASS. If a case mismatches, fix the offending items' `axis`/`rightLetter` (an inverted `rightLetter` flips one letter).

- [ ] **Step 6: Commit**

```bash
git add web/src/domain/oejts.ts web/src/domain/oejts.test.ts web/src/domain/oejts.verify.test.ts
git commit -m "feat(domain): OEJTS item bank + type scoring (with parity check)"
```

---

## Task 4: Se rank + Se strength

**Files:**
- Create: `web/src/domain/seRank.ts`, `web/src/domain/seRank.test.ts`

- [ ] **Step 1: Write the failing test**

Create `web/src/domain/seRank.test.ts`:
```ts
import { describe, it, expect } from 'vitest'
import { seRank, seStrength } from './seRank'
import type { AxisScores } from './types'

describe('seRank', () => {
  it('ranks dominant-Se types highest (1) and demon-Se types lowest (8)', () => {
    expect(seRank('ESTP')).toBe(1)
    expect(seRank('ESFP')).toBe(1)
    expect(seRank('ENFP')).toBe(8)
    expect(seRank('ENTP')).toBe(8)
  })

  it('covers all 16 types with ranks 1..8 (two types each)', () => {
    const types = ['ESTP','ESFP','ISTP','ISFP','ENFJ','ENTJ','INFJ','INTJ','ISTJ','ISFJ','ESTJ','ESFJ','INFP','INTP','ENFP','ENTP']
    const counts: Record<number, number> = {}
    for (const t of types) counts[seRank(t)] = (counts[seRank(t)] ?? 0) + 1
    expect(Object.keys(counts).map(Number).sort((a,b)=>a-b)).toEqual([1,2,3,4,5,6,7,8])
    expect(Object.values(counts).every((c) => c === 2)).toBe(true)
  })
})

describe('seStrength', () => {
  const mk = (IE: number, SN: number): AxisScores => ({ IE, SN, TF: 24, JP: 24 })
  it('is higher for more extraverted + more sensing (E high IE, S low SN)', () => {
    // high=E means larger IE sum is more E; low SN sum is more S
    expect(seStrength(mk(40, 8))).toBeGreaterThan(seStrength(mk(24, 24)))
    expect(seStrength(mk(8, 40))).toBeLessThan(seStrength(mk(24, 24)))
  })
})
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd web && npx vitest run src/domain/seRank.test.ts`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

Create `web/src/domain/seRank.ts`:
```ts
import type { AxisScores } from './types'

const SE_RANK: Record<string, number> = {
  ESTP: 1, ESFP: 1,
  ISTP: 2, ISFP: 2,
  ENFJ: 3, ENTJ: 3,
  INFJ: 4, INTJ: 4,
  ISTJ: 5, ISFJ: 5,
  ESTJ: 6, ESFJ: 6,
  INFP: 7, INTP: 7,
  ENFP: 8, ENTP: 8,
}

export function seRank(type: string): number {
  const r = SE_RANK[type]
  if (r === undefined) throw new Error(`Unknown type: ${type}`)
  return r
}

/**
 * Tiebreak only. Strong extraverted sensing = more Extraverted + more Sensing.
 * With AXIS_LETTERS high-letters E and N: E-ness = IE - 24, S-ness = 24 - SN.
 */
export function seStrength(axisScores: AxisScores): number {
  const eNess = axisScores.IE - 24
  const sNess = 24 - axisScores.SN
  return eNess + sNess
}
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd web && npx vitest run src/domain/seRank.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/domain/seRank.ts web/src/domain/seRank.test.ts
git commit -m "feat(domain): Se rank table + Se-strength tiebreak"
```

---

## Task 5: Reveal timer

**Files:**
- Create: `web/src/domain/timer.ts`, `web/src/domain/timer.test.ts`

- [ ] **Step 1: Write the failing test**

Create `web/src/domain/timer.test.ts`:
```ts
import { describe, it, expect } from 'vitest'
import { computeT } from './timer'

const MIN = 60_000

describe('computeT', () => {
  const start = 1_000_000

  it('is N at the instant of session start', () => {
    expect(computeT(start, 30, start)).toBe(30)
  })

  it('counts down whole minutes remaining (ceil)', () => {
    expect(computeT(start, 30, start + 10 * MIN)).toBe(20)
    expect(computeT(start, 30, start + 10.5 * MIN)).toBe(20) // 19.5 -> ceil 20
  })

  it('never goes below 0', () => {
    expect(computeT(start, 30, start + 45 * MIN)).toBe(0)
  })

  it('honors an adjustable N', () => {
    expect(computeT(start, 10, start + 3 * MIN)).toBe(7)
  })
})
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd web && npx vitest run src/domain/timer.test.ts`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

Create `web/src/domain/timer.ts`:
```ts
/** Minutes remaining until reveal: T = max(0, ceil(N - minutesSinceStart)). */
export function computeT(startedAtMs: number, timerMinutes: number, nowMs: number): number {
  const elapsedMin = (nowMs - startedAtMs) / 60_000
  return Math.max(0, Math.ceil(timerMinutes - elapsedMin))
}
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd web && npx vitest run src/domain/timer.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/domain/timer.ts web/src/domain/timer.test.ts
git commit -m "feat(domain): reveal-timer countdown"
```

---

## Task 6: 16personalities URL

**Files:**
- Create: `web/src/domain/personalityUrl.ts`, `web/src/domain/personalityUrl.test.ts`

- [ ] **Step 1: Write the failing test**

Create `web/src/domain/personalityUrl.test.ts`:
```ts
import { describe, it, expect } from 'vitest'
import { personalityUrl } from './personalityUrl'

describe('personalityUrl', () => {
  it('builds a lowercase 16personalities link', () => {
    expect(personalityUrl('INTJ')).toBe('https://www.16personalities.com/intj-personality')
    expect(personalityUrl('esfp')).toBe('https://www.16personalities.com/esfp-personality')
  })
})
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd web && npx vitest run src/domain/personalityUrl.test.ts`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

Create `web/src/domain/personalityUrl.ts`:
```ts
export function personalityUrl(type: string): string {
  return `https://www.16personalities.com/${type.toLowerCase()}-personality`
}
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd web && npx vitest run src/domain/personalityUrl.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/domain/personalityUrl.ts web/src/domain/personalityUrl.test.ts
git commit -m "feat(domain): 16personalities URL builder"
```

---

## Task 7: Group assignment (freeze + latecomer)

**Files:**
- Create: `web/src/domain/grouping.ts`, `web/src/domain/grouping.test.ts`

Rules (spec §8): at the freeze, completed takers are sorted by `(seRank asc, seStrength desc, id asc)` and the top `ceil(n/2)` go to **scavenger**, the rest to **games**; still-testing takers fill whichever group is smaller (tie → scavenger); takers with `groupOverride` keep their group and are not moved but still count toward balance. Latecomers after the freeze go to the smaller group (tie → scavenger).

- [ ] **Step 1: Write the failing test**

Create `web/src/domain/grouping.test.ts`:
```ts
import { describe, it, expect } from 'vitest'
import { freezeGroups, assignLatecomer } from './grouping'
import type { TakerForGrouping } from './types'

const t = (o: Partial<TakerForGrouping> & { id: string }): TakerForGrouping => ({
  completed: true, seRank: 4, seStrength: 0, group: null, groupOverride: false, ...o,
})

describe('freezeGroups', () => {
  it('puts the top half (by Se rank) of completed takers in scavenger; ceil on odd', () => {
    const takers = [
      t({ id: 'a', seRank: 1 }),
      t({ id: 'b', seRank: 2 }),
      t({ id: 'c', seRank: 7 }),
    ]
    const g = freezeGroups(takers)
    expect(g.a).toBe('scavenger')
    expect(g.b).toBe('scavenger') // ceil(3/2)=2 -> top two
    expect(g.c).toBe('games')
  })

  it('breaks Se-rank ties by higher seStrength, then id', () => {
    const takers = [
      t({ id: 'low', seRank: 3, seStrength: 1 }),
      t({ id: 'high', seRank: 3, seStrength: 9 }),
    ]
    const g = freezeGroups(takers)
    expect(g.high).toBe('scavenger')
    expect(g.low).toBe('games')
  })

  it('assigns still-testing takers to the smaller group (tie -> scavenger)', () => {
    const takers = [
      t({ id: 'c1', seRank: 1 }),                  // scavenger
      t({ id: 'c2', seRank: 8 }),                  // games
      t({ id: 'x', completed: false }),            // tie 1-1 -> scavenger
      t({ id: 'y', completed: false }),            // now 2-1 -> games
    ]
    const g = freezeGroups(takers)
    expect(g.x).toBe('scavenger')
    expect(g.y).toBe('games')
  })

  it('keeps overridden takers in their group and does not move them', () => {
    const takers = [
      t({ id: 'pinned', seRank: 1, group: 'games', groupOverride: true }),
      t({ id: 'a', seRank: 2 }),
      t({ id: 'b', seRank: 3 }),
    ]
    const g = freezeGroups(takers)
    expect(g.pinned).toBe('games')
  })
})

describe('assignLatecomer', () => {
  it('returns the smaller group, tie -> scavenger', () => {
    expect(assignLatecomer({ scavenger: 3, games: 5 })).toBe('scavenger')
    expect(assignLatecomer({ scavenger: 5, games: 3 })).toBe('games')
    expect(assignLatecomer({ scavenger: 4, games: 4 })).toBe('scavenger')
  })
})
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd web && npx vitest run src/domain/grouping.test.ts`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

Create `web/src/domain/grouping.ts`:
```ts
import type { Group, TakerForGrouping } from './types'

export interface GroupCounts { scavenger: number; games: number }

export function assignLatecomer(counts: GroupCounts): Group {
  return counts.scavenger <= counts.games ? 'scavenger' : 'games'
}

/** Computes the frozen group for every taker. Returns id -> group. */
export function freezeGroups(takers: TakerForGrouping[]): Record<string, Group> {
  const result: Record<string, Group> = {}
  const counts: GroupCounts = { scavenger: 0, games: 0 }

  // 1) overrides keep their group and count toward balance
  for (const o of takers) {
    if (o.groupOverride && o.group) {
      result[o.id] = o.group
      counts[o.group]++
    }
  }

  // 2) completed, non-overridden: Se-rank split, top half -> scavenger
  const completed = takers
    .filter((t) => t.completed && !t.groupOverride)
    .sort(
      (a, b) =>
        (a.seRank ?? 99) - (b.seRank ?? 99) ||
        (b.seStrength ?? 0) - (a.seStrength ?? 0) ||
        (a.id < b.id ? -1 : 1),
    )
  const scavengerTarget = Math.ceil(completed.length / 2)
  completed.forEach((t, i) => {
    const g: Group = i < scavengerTarget ? 'scavenger' : 'games'
    result[t.id] = g
    counts[g]++
  })

  // 3) still-testing, non-overridden: fill the smaller group
  const incomplete = takers
    .filter((t) => !t.completed && !t.groupOverride)
    .sort((a, b) => (a.id < b.id ? -1 : 1))
  for (const t of incomplete) {
    const g = assignLatecomer(counts)
    result[t.id] = g
    counts[g]++
  }

  return result
}
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd web && npx vitest run src/domain/grouping.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/domain/grouping.ts web/src/domain/grouping.test.ts
git commit -m "feat(domain): freeze-at-reveal group assignment + latecomer balancing"
```

---

## Task 8: Firebase init + emulator wiring

**Files:**
- Create: `web/src/firebase.ts`, `web/firebase.json`, `web/.firebaserc`, `web/firestore.indexes.json`

- [ ] **Step 1: Write the SDK init module**

Create `web/src/firebase.ts`:
```ts
import { initializeApp } from 'firebase/app'
import { getAuth, connectAuthEmulator } from 'firebase/auth'
import { getFirestore, connectFirestoreEmulator } from 'firebase/firestore'

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FB_API_KEY,
  authDomain: import.meta.env.VITE_FB_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FB_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FB_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FB_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FB_APP_ID,
}

export const app = initializeApp(firebaseConfig)
export const auth = getAuth(app)
export const db = getFirestore(app)

// In dev with VITE_USE_EMULATOR=1, point at local emulators.
if (import.meta.env.VITE_USE_EMULATOR === '1') {
  connectAuthEmulator(auth, 'http://localhost:9099', { disableWarnings: true })
  connectFirestoreEmulator(db, 'localhost', 8080)
}
```

- [ ] **Step 2: Create Firebase config files**

Create `web/firebase.json`:
```json
{
  "hosting": {
    "public": "dist",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
    "rewrites": [{ "source": "**", "destination": "/index.html" }]
  },
  "firestore": {
    "rules": "firestore.rules",
    "indexes": "firestore.indexes.json"
  },
  "emulators": {
    "auth": { "port": 9099 },
    "firestore": { "port": 8080 },
    "ui": { "enabled": true }
  }
}
```

Create `web/.firebaserc` (replace with the real project id):
```json
{ "projects": { "default": "lcms-young-adults" } }
```

Create `web/firestore.indexes.json`:
```json
{
  "indexes": [
    {
      "collectionGroup": "takers",
      "queryScope": "COLLECTION",
      "fields": [
        { "fieldPath": "sessionId", "order": "ASCENDING" },
        { "fieldPath": "sharing", "order": "ASCENDING" }
      ]
    }
  ],
  "fieldOverrides": []
}
```

- [ ] **Step 3: Commit**

```bash
git add web/src/firebase.ts web/firebase.json web/.firebaserc web/firestore.indexes.json
git commit -m "feat: firebase SDK init + emulator wiring + config"
```

---

## Task 9: Firestore document shapes + taker data layer

**Files:**
- Create: `web/src/data/takers.ts`, `web/test/emulator.ts`, `web/src/data/takers.test.ts`

- [ ] **Step 1: Write the emulator harness**

Create `web/test/emulator.ts`:
```ts
import { initializeTestEnvironment, RulesTestEnvironment } from '@firebase/rules-unit-testing'
import { readFileSync } from 'node:fs'

let testEnv: RulesTestEnvironment | null = null

export async function getTestEnv(): Promise<RulesTestEnvironment> {
  if (!testEnv) {
    testEnv = await initializeTestEnvironment({
      projectId: 'demo-lya',
      firestore: {
        host: 'localhost',
        port: 8080,
        rules: readFileSync(new URL('../firestore.rules', import.meta.url), 'utf8'),
      },
    })
  }
  return testEnv
}
```

- [ ] **Step 2: Write the failing taker test**

Create `web/src/data/takers.test.ts`:
```ts
import { describe, it, expect, beforeEach, afterAll } from 'vitest'
import { getTestEnv } from '../../test/emulator'
import { getDoc, doc } from 'firebase/firestore'
import { upsertTaker, recordAnswer, completeTaker, normalizeUsername } from './takers'

describe('takers data layer (emulator)', () => {
  beforeEach(async () => { (await getTestEnv()).clearFirestore() })
  afterAll(async () => { await (await getTestEnv()).cleanup() })

  it('normalizes usernames to a stable key', () => {
    expect(normalizeUsername('  Donovan ')).toBe('donovan')
  })

  it('creates then resumes a taker by username', async () => {
    const env = await getTestEnv()
    await env.withSecurityRulesDisabled(async (ctx) => {
      const db = ctx.firestore()
      await upsertTaker(db, 'Donovan')
      await recordAnswer(db, 'Donovan', 4, 5)
      const snap = await getDoc(doc(db, 'takers', 'donovan'))
      expect(snap.exists()).toBe(true)
      expect(snap.data()!.username).toBe('Donovan')
      expect(snap.data()!.answers['4']).toBe(5)
      expect(snap.data()!.completed).toBe(false)
    })
  })

  it('completing a taker stamps type, axisScores, seRank', async () => {
    const env = await getTestEnv()
    await env.withSecurityRulesDisabled(async (ctx) => {
      const db = ctx.firestore()
      await upsertTaker(db, 'Mae')
      await completeTaker(db, 'Mae', {
        type: 'ESTP', axisScores: { IE: 40, SN: 8, TF: 12, JP: 30 }, seRank: 1, seStrength: 32,
      })
      const snap = await getDoc(doc(db, 'takers', 'mae'))
      expect(snap.data()!.completed).toBe(true)
      expect(snap.data()!.type).toBe('ESTP')
      expect(snap.data()!.seRank).toBe(1)
    })
  })
})
```

- [ ] **Step 3: Run to confirm failure**

Run from `web/`: `firebase emulators:exec --only firestore "npx vitest run src/data/takers.test.ts"`
Expected: FAIL — `./takers` module missing.

- [ ] **Step 4: Implement the taker data layer**

Create `web/src/data/takers.ts`:
```ts
import {
  Firestore, doc, getDoc, setDoc, updateDoc, serverTimestamp,
} from 'firebase/firestore'
import type { AnswerValue, AxisScores, Group } from '../domain/types'

export function normalizeUsername(raw: string): string {
  return raw.trim().toLowerCase()
}

export interface TakerDoc {
  username: string
  answers: Record<string, AnswerValue>
  completed: boolean
  type: string | null
  axisScores: AxisScores | null
  seRank: number | null
  seStrength: number | null
  sharing: boolean
  sessionId: string | null
  group: Group | null
  groupOverride: boolean
}

const takerRef = (db: Firestore, username: string) =>
  doc(db, 'takers', normalizeUsername(username))

/** Creates the taker if absent; never overwrites an existing record. */
export async function upsertTaker(db: Firestore, username: string): Promise<void> {
  const ref = takerRef(db, username)
  const snap = await getDoc(ref)
  if (snap.exists()) return
  await setDoc(ref, {
    username: username.trim(),
    answers: {},
    completed: false,
    type: null,
    axisScores: null,
    seRank: null,
    seStrength: null,
    sharing: false,
    sessionId: null,
    group: null,
    groupOverride: false,
    createdAt: serverTimestamp(),
    updatedAt: serverTimestamp(),
  } satisfies Record<string, unknown>)
}

export async function recordAnswer(
  db: Firestore, username: string, itemId: number, value: AnswerValue,
): Promise<void> {
  await updateDoc(takerRef(db, username), {
    [`answers.${itemId}`]: value,
    updatedAt: serverTimestamp(),
  })
}

export interface CompletePayload {
  type: string
  axisScores: AxisScores
  seRank: number
  seStrength: number
}

export async function completeTaker(
  db: Firestore, username: string, p: CompletePayload,
): Promise<void> {
  await updateDoc(takerRef(db, username), {
    completed: true,
    type: p.type,
    axisScores: p.axisScores,
    seRank: p.seRank,
    seStrength: p.seStrength,
    completedAt: serverTimestamp(),
    updatedAt: serverTimestamp(),
  })
}

export async function setSharing(db: Firestore, username: string, sharing: boolean): Promise<void> {
  await updateDoc(takerRef(db, username), { sharing, updatedAt: serverTimestamp() })
}

export async function getTaker(db: Firestore, username: string): Promise<TakerDoc | null> {
  const snap = await getDoc(takerRef(db, username))
  return snap.exists() ? (snap.data() as TakerDoc) : null
}
```

- [ ] **Step 5: Run to confirm pass**

Run from `web/`: `firebase emulators:exec --only firestore "npx vitest run src/data/takers.test.ts"`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add web/src/data/takers.ts web/test/emulator.ts web/src/data/takers.test.ts
git commit -m "feat(data): taker CRUD (create/resume, answers, complete, sharing)"
```

---

## Task 10: Sessions data layer

**Files:**
- Create: `web/src/data/sessions.ts`, `web/src/data/sessions.test.ts`

Behavior (spec §5, §9): at most one `active` session; `startSession` is rejected if one is active. `endSession` stamps `endedAt` and flips status. New takers after end are session-less (assigning `sessionId` happens at submit time — see UI plan; here we expose `getActiveSession`).

- [ ] **Step 1: Write the failing test**

Create `web/src/data/sessions.test.ts`:
```ts
import { describe, it, expect, beforeEach, afterAll } from 'vitest'
import { getTestEnv } from '../../test/emulator'
import { startSession, endSession, getActiveSession, archiveSession } from './sessions'

describe('sessions data layer (emulator)', () => {
  beforeEach(async () => { (await getTestEnv()).clearFirestore() })
  afterAll(async () => { await (await getTestEnv()).cleanup() })

  it('starts a session and finds it as active', async () => {
    const env = await getTestEnv()
    await env.withSecurityRulesDisabled(async (ctx) => {
      const db = ctx.firestore()
      const id = await startSession(db, { name: 'Personality Day', timerMinutes: 30, createdBy: 'd@x.org' })
      const active = await getActiveSession(db)
      expect(active?.id).toBe(id)
      expect(active?.timerMinutes).toBe(30)
    })
  })

  it('refuses a second active session', async () => {
    const env = await getTestEnv()
    await env.withSecurityRulesDisabled(async (ctx) => {
      const db = ctx.firestore()
      await startSession(db, { name: 'A', timerMinutes: 30, createdBy: 'd@x.org' })
      await expect(
        startSession(db, { name: 'B', timerMinutes: 30, createdBy: 'd@x.org' }),
      ).rejects.toThrow(/active session/i)
    })
  })

  it('ending then archiving clears active and hides it', async () => {
    const env = await getTestEnv()
    await env.withSecurityRulesDisabled(async (ctx) => {
      const db = ctx.firestore()
      const id = await startSession(db, { name: 'A', timerMinutes: 30, createdBy: 'd@x.org' })
      await endSession(db, id)
      expect(await getActiveSession(db)).toBeNull()
      await archiveSession(db, id)
    })
  })
})
```

- [ ] **Step 2: Run to confirm failure**

Run from `web/`: `firebase emulators:exec --only firestore "npx vitest run src/data/sessions.test.ts"`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

Create `web/src/data/sessions.ts`:
```ts
import {
  Firestore, collection, addDoc, doc, updateDoc, getDocs, query, where, limit,
  serverTimestamp,
} from 'firebase/firestore'

export type SessionStatus = 'active' | 'ended' | 'archived'

export interface SessionDoc {
  id: string
  name: string
  status: SessionStatus
  timerMinutes: number
  startedAt: number | null
  endedAt: number | null
  groupsFrozenAt: number | null
  createdBy: string
}

export interface StartSessionInput {
  name: string
  timerMinutes: number
  createdBy: string
}

export async function getActiveSession(db: Firestore): Promise<SessionDoc | null> {
  const q = query(collection(db, 'sessions'), where('status', '==', 'active'), limit(1))
  const snap = await getDocs(q)
  if (snap.empty) return null
  const d = snap.docs[0]
  return { id: d.id, ...(d.data() as Omit<SessionDoc, 'id'>) }
}

export async function startSession(db: Firestore, input: StartSessionInput): Promise<string> {
  if (await getActiveSession(db)) throw new Error('There is already an active session')
  const ref = await addDoc(collection(db, 'sessions'), {
    name: input.name,
    status: 'active' as SessionStatus,
    timerMinutes: input.timerMinutes,
    startedAt: serverTimestamp(),
    endedAt: null,
    groupsFrozenAt: null,
    createdBy: input.createdBy,
  })
  return ref.id
}

export async function endSession(db: Firestore, id: string): Promise<void> {
  await updateDoc(doc(db, 'sessions', id), { status: 'ended', endedAt: serverTimestamp() })
}

export async function archiveSession(db: Firestore, id: string): Promise<void> {
  await updateDoc(doc(db, 'sessions', id), { status: 'archived' })
}

export async function renameSession(db: Firestore, id: string, name: string): Promise<void> {
  await updateDoc(doc(db, 'sessions', id), { name })
}

export async function setTimerMinutes(db: Firestore, id: string, timerMinutes: number): Promise<void> {
  await updateDoc(doc(db, 'sessions', id), { timerMinutes })
}
```

- [ ] **Step 4: Run to confirm pass**

Run from `web/`: `firebase emulators:exec --only firestore "npx vitest run src/data/sessions.test.ts"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/data/sessions.ts web/src/data/sessions.test.ts
git commit -m "feat(data): session lifecycle (start/end/archive, single-active guard)"
```

---

## Task 11: Transactional group freeze

**Files:**
- Create: `web/src/data/freeze.ts`, `web/src/data/freeze.test.ts`

Wraps `freezeGroups` (Task 7) in a Firestore transaction: reads all takers for the session, computes assignments, writes each taker's `group`, and stamps `sessions.groupsFrozenAt`. Idempotent — a second call after frozen is a no-op.

- [ ] **Step 1: Write the failing test**

Create `web/src/data/freeze.test.ts`:
```ts
import { describe, it, expect, beforeEach, afterAll } from 'vitest'
import { getTestEnv } from '../../test/emulator'
import { doc, getDoc, setDoc } from 'firebase/firestore'
import { freezeSessionGroups } from './freeze'

async function seed(db: any, sessionId: string) {
  await setDoc(doc(db, 'sessions', sessionId), {
    name: 'A', status: 'active', timerMinutes: 30, startedAt: 1, endedAt: null,
    groupsFrozenAt: null, createdBy: 'd@x.org',
  })
  const mk = (id: string, seRank: number, completed = true) =>
    setDoc(doc(db, 'takers', id), {
      username: id, answers: {}, completed, type: 'ESTP', axisScores: { IE: 24, SN: 24, TF: 24, JP: 24 },
      seRank, seStrength: 0, sharing: false, sessionId, group: null, groupOverride: false,
    })
  await Promise.all([mk('a', 1), mk('b', 2), mk('c', 7), mk('d', 8)])
}

describe('freezeSessionGroups (emulator)', () => {
  beforeEach(async () => { (await getTestEnv()).clearFirestore() })
  afterAll(async () => { await (await getTestEnv()).cleanup() })

  it('writes groups and stamps groupsFrozenAt', async () => {
    const env = await getTestEnv()
    await env.withSecurityRulesDisabled(async (ctx) => {
      const db = ctx.firestore()
      await seed(db, 's1')
      await freezeSessionGroups(db, 's1')
      const grp = async (id: string) => (await getDoc(doc(db, 'takers', id))).data()!.group
      expect(await grp('a')).toBe('scavenger')
      expect(await grp('b')).toBe('scavenger')
      expect(await grp('c')).toBe('games')
      expect(await grp('d')).toBe('games')
      const s = await getDoc(doc(db, 'sessions', 's1'))
      expect(s.data()!.groupsFrozenAt).not.toBeNull()
    })
  })

  it('is a no-op if already frozen', async () => {
    const env = await getTestEnv()
    await env.withSecurityRulesDisabled(async (ctx) => {
      const db = ctx.firestore()
      await seed(db, 's1')
      await freezeSessionGroups(db, 's1')
      const first = (await getDoc(doc(db, 'sessions', 's1'))).data()!.groupsFrozenAt
      await freezeSessionGroups(db, 's1')
      const second = (await getDoc(doc(db, 'sessions', 's1'))).data()!.groupsFrozenAt
      expect(second).toEqual(first)
    })
  })
})
```

- [ ] **Step 2: Run to confirm failure**

Run from `web/`: `firebase emulators:exec --only firestore "npx vitest run src/data/freeze.test.ts"`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

Create `web/src/data/freeze.ts`:
```ts
import {
  Firestore, runTransaction, doc, collection, query, where, getDocs, serverTimestamp,
} from 'firebase/firestore'
import { freezeGroups } from '../domain/grouping'
import type { TakerForGrouping } from '../domain/types'

/** Computes and persists the frozen group split for a session. Idempotent. */
export async function freezeSessionGroups(db: Firestore, sessionId: string): Promise<void> {
  // Read takers outside the txn (collection reads aren't transactional); the txn
  // guards the frozen flag so concurrent callers don't double-write.
  const takersSnap = await getDocs(
    query(collection(db, 'takers'), where('sessionId', '==', sessionId)),
  )
  const takers: TakerForGrouping[] = takersSnap.docs.map((d) => {
    const t = d.data()
    return {
      id: d.id, completed: t.completed, seRank: t.seRank ?? undefined,
      seStrength: t.seStrength ?? undefined, group: t.group ?? null,
      groupOverride: t.groupOverride ?? false,
    }
  })

  const assignments = freezeGroups(takers)

  await runTransaction(db, async (txn) => {
    const sessionRef = doc(db, 'sessions', sessionId)
    const sessionSnap = await txn.get(sessionRef)
    if (!sessionSnap.exists()) throw new Error('Session not found')
    if (sessionSnap.data().groupsFrozenAt) return // already frozen -> no-op

    for (const [id, group] of Object.entries(assignments)) {
      txn.update(doc(db, 'takers', id), { group })
    }
    txn.update(sessionRef, { groupsFrozenAt: serverTimestamp() })
  })
}
```

- [ ] **Step 4: Run to confirm pass**

Run from `web/`: `firebase emulators:exec --only firestore "npx vitest run src/data/freeze.test.ts"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/data/freeze.ts web/src/data/freeze.test.ts
git commit -m "feat(data): transactional, idempotent group freeze"
```

---

## Task 12: Admin allowlist + auth

**Files:**
- Create: `web/src/data/admins.ts`, `web/src/auth/adminAuth.ts`, `web/src/auth/takerAuth.ts`, `web/src/data/admins.test.ts`

- [ ] **Step 1: Write the failing test for the allowlist**

Create `web/src/data/admins.test.ts`:
```ts
import { describe, it, expect, beforeEach, afterAll } from 'vitest'
import { getTestEnv } from '../../test/emulator'
import { isAdminEmail, addAdmin, removeAdmin } from './admins'

describe('admins allowlist (emulator)', () => {
  beforeEach(async () => { (await getTestEnv()).clearFirestore() })
  afterAll(async () => { await (await getTestEnv()).cleanup() })

  it('add / check / remove an admin email (case-insensitive)', async () => {
    const env = await getTestEnv()
    await env.withSecurityRulesDisabled(async (ctx) => {
      const db = ctx.firestore()
      expect(await isAdminEmail(db, 'donovan@lcmsyoungadults.org')).toBe(false)
      await addAdmin(db, 'Donovan@lcmsyoungadults.org')
      expect(await isAdminEmail(db, 'donovan@lcmsyoungadults.org')).toBe(true)
      await removeAdmin(db, 'donovan@lcmsyoungadults.org')
      expect(await isAdminEmail(db, 'donovan@lcmsyoungadults.org')).toBe(false)
    })
  })
})
```

- [ ] **Step 2: Run to confirm failure**

Run from `web/`: `firebase emulators:exec --only firestore "npx vitest run src/data/admins.test.ts"`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement the allowlist data layer**

Create `web/src/data/admins.ts`:
```ts
import { Firestore, doc, getDoc, setDoc, deleteDoc } from 'firebase/firestore'

// One doc per admin, id = lowercased email. Simple to check and to rule-guard.
const key = (email: string) => email.trim().toLowerCase()

export async function isAdminEmail(db: Firestore, email: string): Promise<boolean> {
  const snap = await getDoc(doc(db, 'admins', key(email)))
  return snap.exists()
}

export async function addAdmin(db: Firestore, email: string): Promise<void> {
  await setDoc(doc(db, 'admins', key(email)), { email: email.trim() })
}

export async function removeAdmin(db: Firestore, email: string): Promise<void> {
  await deleteDoc(doc(db, 'admins', key(email)))
}
```

- [ ] **Step 4: Run to confirm pass**

Run from `web/`: `firebase emulators:exec --only firestore "npx vitest run src/data/admins.test.ts"`
Expected: PASS.

- [ ] **Step 5: Implement the auth helpers (no test — thin SDK wrappers)**

Create `web/src/auth/takerAuth.ts`:
```ts
import { signInAnonymously, onAuthStateChanged, User } from 'firebase/auth'
import { auth } from '../firebase'

/** Ensures every taker device is an (anonymous) authenticated client. */
export function ensureAnonymous(): Promise<User> {
  return new Promise((resolve, reject) => {
    const unsub = onAuthStateChanged(auth, (user) => {
      unsub()
      if (user) return resolve(user)
      signInAnonymously(auth).then((c) => resolve(c.user)).catch(reject)
    })
  })
}
```

Create `web/src/auth/adminAuth.ts`:
```ts
import { GoogleAuthProvider, signInWithPopup, signOut, User } from 'firebase/auth'
import { auth, db } from '../firebase'
import { isAdminEmail } from '../data/admins'

export async function signInWithGoogle(): Promise<User> {
  const cred = await signInWithPopup(auth, new GoogleAuthProvider())
  return cred.user
}

export function signOutAdmin(): Promise<void> {
  return signOut(auth)
}

/** True only if the signed-in user's email is on the allowlist. */
export async function isAdmin(user: User | null): Promise<boolean> {
  if (!user?.email) return false
  return isAdminEmail(db, user.email)
}
```

- [ ] **Step 6: Commit**

```bash
git add web/src/data/admins.ts web/src/data/admins.test.ts web/src/auth/takerAuth.ts web/src/auth/adminAuth.ts
git commit -m "feat(auth): admin allowlist + Google sign-in + anonymous taker auth"
```

---

## Task 13: Firestore security rules

**Files:**
- Create: `web/firestore.rules`, `web/src/data/rules.test.ts`

Trust model (spec §3): any signed-in client (incl. anonymous) may read/write `takers` (username-only by design). `sessions` and `admins` are readable by signed-in clients but writable only by allowlisted admins. An admin is a signed-in user whose lowercased email has a doc in `admins`.

- [ ] **Step 1: Write the failing rules test**

Create `web/src/data/rules.test.ts`:
```ts
import { describe, it, expect, beforeEach, afterAll } from 'vitest'
import { getTestEnv } from '../../test/emulator'
import { assertFails, assertSucceeds } from '@firebase/rules-unit-testing'
import { doc, getDoc, setDoc } from 'firebase/firestore'

describe('security rules (emulator)', () => {
  beforeEach(async () => {
    const env = await getTestEnv()
    await env.clearFirestore()
    await env.withSecurityRulesDisabled(async (ctx) => {
      await setDoc(doc(ctx.firestore(), 'admins', 'admin@x.org'), { email: 'admin@x.org' })
    })
  })
  afterAll(async () => { await (await getTestEnv()).cleanup() })

  it('anonymous user can write a taker but not a session', async () => {
    const env = await getTestEnv()
    const anon = env.authenticatedContext('anon1', {}) // no email = not admin
    const db = anon.firestore()
    await assertSucceeds(setDoc(doc(db, 'takers', 'bob'), { username: 'bob', completed: false }))
    await assertFails(setDoc(doc(db, 'sessions', 's1'), { name: 'x', status: 'active' }))
  })

  it('non-admin signed-in user cannot write admins', async () => {
    const env = await getTestEnv()
    const u = env.authenticatedContext('u2', { email: 'random@x.org' })
    await assertFails(setDoc(doc(u.firestore(), 'admins', 'evil@x.org'), { email: 'evil@x.org' }))
  })

  it('allowlisted admin can write a session and admins', async () => {
    const env = await getTestEnv()
    const admin = env.authenticatedContext('a1', { email: 'admin@x.org' })
    const db = admin.firestore()
    await assertSucceeds(setDoc(doc(db, 'sessions', 's1'), { name: 'x', status: 'active' }))
    await assertSucceeds(setDoc(doc(db, 'admins', 'new@x.org'), { email: 'new@x.org' }))
  })

  it('unauthenticated client is denied everywhere', async () => {
    const env = await getTestEnv()
    const db = env.unauthenticatedContext().firestore()
    await assertFails(getDoc(doc(db, 'takers', 'bob')))
  })
})
```

- [ ] **Step 2: Run to confirm failure**

Run from `web/`: `firebase emulators:exec --only firestore "npx vitest run src/data/rules.test.ts"`
Expected: FAIL — no `firestore.rules`, so writes that should fail may succeed / reads error differently.

- [ ] **Step 3: Implement the rules**

Create `web/firestore.rules`:
```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    function signedIn() { return request.auth != null; }

    function isAdmin() {
      return signedIn()
        && request.auth.token.email != null
        && exists(/databases/$(database)/documents/admins/$(request.auth.token.email.lower()));
    }

    // Takers: username-only trust model — any signed-in client may read/write.
    match /takers/{username} {
      allow read, write: if signedIn();
    }

    // Sessions: anyone signed-in may read (takers need timer/active state);
    // only allowlisted admins may write.
    match /sessions/{id} {
      allow read: if signedIn();
      allow write: if isAdmin();
    }

    // Admins allowlist: readable by signed-in (to self-check); writable by admins only.
    match /admins/{email} {
      allow read: if signedIn();
      allow write: if isAdmin();
    }
  }
}
```

> **Note:** `request.auth.token.email.lower()` requires the email to be present in the token. Anonymous users have no email, so `isAdmin()` is false for them. The very first admin (`donovan@lcmsyoungadults.org`) is seeded once via the emulator/console or a one-off privileged script (see Task 14), because the rules require an existing admin to create one.

- [ ] **Step 4: Run to confirm pass**

Run from `web/`: `firebase emulators:exec --only firestore "npx vitest run src/data/rules.test.ts"`
Expected: PASS — all four assertions hold.

- [ ] **Step 5: Commit**

```bash
git add web/firestore.rules web/src/data/rules.test.ts
git commit -m "feat(security): firestore rules enforcing taker/admin trust model"
```

---

## Task 14: Seed the first admin + full test sweep + deploy config check

**Files:**
- Create: `web/scripts/seed-admin.md` (instructions)

- [ ] **Step 1: Document the one-time first-admin seed**

Create `web/scripts/seed-admin.md`:
```markdown
# Seeding the first admin

The security rules require an existing admin to create another, so the first
one is seeded manually (once):

**Production:** Firebase Console → Firestore → create collection `admins` →
add a document with **ID** = `donovan@lcmsyoungadults.org` (lowercase) and a
field `email: "donovan@lcmsyoungadults.org"`.

After that, sign in at `/admin` with that Google account and use the in-app
"Manage admins" UI (admin UI plan) to add/remove others.
```

- [ ] **Step 2: Run the entire unit suite (no emulator)**

Run from `web/`: `npx vitest run src/domain`
Expected: PASS — all domain tests green.

- [ ] **Step 3: Run the entire emulator suite**

Run from `web/`: `firebase emulators:exec --only firestore,auth "npx vitest run src/data"`
Expected: PASS — takers, sessions, freeze, admins, rules.

- [ ] **Step 4: Verify a production build still compiles**

Run from `web/`: `npm run build`
Expected: clean build (the `main.tsx` shell + domain/data/auth modules typecheck).

- [ ] **Step 5: Commit**

```bash
git add web/scripts/seed-admin.md
git commit -m "docs: first-admin seeding + foundation test sweep green"
```

---

## Self-review (completed during planning)

- **Spec coverage:** §3 stack/trust → Tasks 1, 8, 13; §5 data model → Tasks 9–12; §7 OEJTS + doctrinal rewordings → Task 3; §8 Se rank/strength/freeze/timer → Tasks 4, 5, 7, 11; §9 sessions lifecycle → Task 10; admin allowlist/auth → Task 12. **UI (§4, §6, §10) is intentionally deferred to the two UI plans.**
- **Type consistency:** `Group`, `Axis`, `AxisScores`, `TakerForGrouping` defined once in `types.ts` and reused; `freezeGroups`/`assignLatecomer`/`scoreType`/`seRank`/`seStrength`/`computeT`/`personalityUrl` signatures match across tasks.
- **Known follow-ups for the UI plans:** assigning `sessionId` at submit time; live `useT`/`useSession`/`useSharedList` hooks; the post-freeze latecomer write-path (uses `assignLatecomer`); the mid-test "you're in {group}" banner; the admin override/recompute and delete-with-`DELETE` flows.

## Next plans (to be written)

- **Plan 2 — Test-taker UI:** routing, username landing, test screen (progress bar, slider, autosave, resume), sharing prompt, result screen (live T countdown, reveal banner, shared list with clean teal type-links, opt in/out), the mid-test persistent banner, and assigning `sessionId` at submit.
- **Plan 3 — Admin UI:** Google sign-in gate, session list + CRUD, live roster, start/end/reveal-now/recompute, archive, delete-with-`DELETE` confirm, manage-admins.
- **Plan 4 (small) — Theme + deploy:** brochure design-system CSS/components and the hosting + rules deploy.
