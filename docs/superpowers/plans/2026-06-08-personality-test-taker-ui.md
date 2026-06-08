# Personality Test — Test-Taker UI Implementation Plan (Plan 2 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the test-taker experience on top of the foundation: the shared brochure design system, live-data hooks, the username landing, the test screen (progress bar + slider + autosave + resume), the sharing prompt, the result screen (live T countdown, group reveal, clean shared list with opt in/out), and the mid-test persistent reveal banner.

**Architecture:** React screens under `web/src/routes/`, reusable presentational components under `web/src/ui/`, and Firestore-subscription hooks under `web/src/hooks/`. All domain logic and data access come from Plan 1 modules. Submit orchestration (compute type, set sessionId at submit time, latecomer grouping) lives in `web/src/data/submit.ts`. Behavior is tested with @testing-library/react against mocked data modules; submit orchestration is tested against the Firebase emulator.

**Tech Stack:** React 18 + TS + Vite, react-router-dom v6, Firebase Firestore (onSnapshot), Vitest + @testing-library/react.

**Prerequisite:** Plan 1 (`2026-06-08-personality-test-foundation.md`) complete and green. **Depends on:** `domain/oejts.ts`, `domain/seRank.ts`, `domain/timer.ts`, `domain/personalityUrl.ts`, `domain/grouping.ts`, `data/takers.ts`, `data/sessions.ts`, `data/freeze.ts`, `firebase.ts`, `auth/takerAuth.ts`.

**Spec:** `docs/superpowers/specs/2026-06-08-personality-test-app-design.md` (§4, §6, §10)

---

## File structure (added by this plan)

```
web/src/
  ui/
    theme.css            # palette + fonts + base tokens
    Button.tsx
    ProgressBar.tsx
    Slider.tsx           # 5-point OEJTS choice
    RevealBanner.tsx     # persistent mid-test banner
    SharedList.tsx       # session sharers, clean teal type-links
  hooks/
    useNow.ts            # ticking clock for the countdown
    useActiveSession.ts  # subscribe the active session
    useTaker.ts          # subscribe one taker doc
    useSharedList.ts     # subscribe session sharers
  data/
    submit.ts            # submitTest(): set sessionId, complete, latecomer group
    submit.test.ts
  routes/
    TestApp.tsx          # router + flow state machine for /personality-test
    Landing.tsx
    Question.tsx
    SharingPrompt.tsx
    Result.tsx
  App.tsx                # top-level routes (modified)
  main.tsx               # mount + import theme.css (modified)
```

---

## Task 1: Design-system theme + base components

**Files:**
- Create: `web/src/ui/theme.css`, `web/src/ui/Button.tsx`, `web/src/ui/ProgressBar.tsx`
- Create test: `web/src/ui/ProgressBar.test.tsx`
- Modify: `web/src/main.tsx`

- [ ] **Step 1: Add the fonts + theme tokens**

Create `web/src/ui/theme.css`:
```css
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800&family=Cormorant+Garamond:ital@0;1&display=swap');

:root {
  --teal: #01404f;
  --pink: #fad5cd;
  --pink-deep: #f5bbb0;
  --cream: #fff8f2;
  --white: #fff;
  --font-ui: 'Montserrat', system-ui, sans-serif;
  --font-serif: 'Cormorant Garamond', Georgia, serif;
  --radius: 16px;
  --shadow: 0 10px 30px rgba(1, 64, 79, 0.18);
}

* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: var(--font-ui);
  color: var(--teal);
  background: var(--cream);
}
.serif { font-family: var(--font-serif); font-style: italic; }
.screen {
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  text-align: center;
  gap: 1rem;
}
.card {
  background: var(--white);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 1.5rem;
  width: min(28rem, 100%);
}
a.clean { color: var(--teal); text-decoration: none; font-weight: 700; }
a.clean:hover { text-decoration: none; opacity: 0.8; }
```

- [ ] **Step 2: Import the theme at the app root**

In `web/src/main.tsx`, add as the first import:
```ts
import './ui/theme.css'
```

- [ ] **Step 3: Write the ProgressBar test first**

Create `web/src/ui/ProgressBar.test.tsx`:
```tsx
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { ProgressBar } from './ProgressBar'

describe('ProgressBar', () => {
  it('shows "Question X of N" and a bar filled to the right fraction', () => {
    render(<ProgressBar current={18} total={32} />)
    expect(screen.getByText('Question 18 of 32')).toBeInTheDocument()
    const fill = screen.getByTestId('progress-fill')
    expect(fill).toHaveStyle({ width: `${(18 / 32) * 100}%` })
  })
})
```

- [ ] **Step 4: Run to confirm failure**

Run: `cd web && npx vitest run src/ui/ProgressBar.test.tsx`
Expected: FAIL — module missing.

- [ ] **Step 5: Implement ProgressBar and Button**

Create `web/src/ui/ProgressBar.tsx`:
```tsx
export function ProgressBar({ current, total }: { current: number; total: number }) {
  const pct = (current / total) * 100
  return (
    <div style={{ width: '100%' }}>
      <div style={{ height: 6, background: 'var(--pink-deep)', borderRadius: 3, overflow: 'hidden' }}>
        <div data-testid="progress-fill" style={{ width: `${pct}%`, height: '100%', background: 'var(--teal)' }} />
      </div>
      <div style={{ marginTop: 8, fontSize: '.7rem', letterSpacing: '.12em', textTransform: 'uppercase', opacity: 0.65 }}>
        Question {current} of {total}
      </div>
    </div>
  )
}
```

Create `web/src/ui/Button.tsx`:
```tsx
import { ButtonHTMLAttributes } from 'react'

export function Button({ children, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      style={{
        background: 'var(--teal)', color: 'var(--cream)', border: 'none',
        borderRadius: 999, padding: '.7rem 1.4rem', fontWeight: 600, fontSize: '.95rem',
        cursor: 'pointer', opacity: props.disabled ? 0.5 : 1, ...(props.style ?? {}),
      }}
    >
      {children}
    </button>
  )
}
```

- [ ] **Step 6: Run to confirm pass**

Run: `cd web && npx vitest run src/ui/ProgressBar.test.tsx`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add web/src/ui/theme.css web/src/ui/Button.tsx web/src/ui/ProgressBar.tsx web/src/ui/ProgressBar.test.tsx web/src/main.tsx
git commit -m "feat(ui): brochure design-system theme + ProgressBar + Button"
```

---

## Task 2: The 5-point Slider component

**Files:**
- Create: `web/src/ui/Slider.tsx`, `web/src/ui/Slider.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `web/src/ui/Slider.test.tsx`:
```tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { Slider } from './Slider'

describe('Slider', () => {
  it('renders both poles and 5 choices, and reports the chosen value', () => {
    const onChange = vi.fn()
    render(<Slider left="not me" right="very me" value={undefined} onChange={onChange} />)
    expect(screen.getByText('not me')).toBeInTheDocument()
    expect(screen.getByText('very me')).toBeInTheDocument()
    const choices = screen.getAllByRole('radio')
    expect(choices).toHaveLength(5)
    fireEvent.click(choices[4])
    expect(onChange).toHaveBeenCalledWith(5)
  })

  it('marks the current value as selected', () => {
    render(<Slider left="a" right="b" value={3} onChange={() => {}} />)
    expect(screen.getAllByRole('radio')[2]).toHaveAttribute('aria-checked', 'true')
  })
})
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd web && npx vitest run src/ui/Slider.test.tsx`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

Create `web/src/ui/Slider.tsx`:
```tsx
import type { AnswerValue } from '../domain/types'

interface Props {
  left: string
  right: string
  value: AnswerValue | undefined
  onChange: (v: AnswerValue) => void
}

const SIZES = [26, 20, 16, 20, 26]

export function Slider({ left, right, value, onChange }: Props) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '1.5rem .25rem .6rem' }}>
        {([1, 2, 3, 4, 5] as AnswerValue[]).map((v, i) => {
          const selected = value === v
          return (
            <button
              key={v}
              role="radio"
              aria-checked={selected}
              aria-label={`Choice ${v}`}
              onClick={() => onChange(v)}
              style={{
                width: SIZES[i], height: SIZES[i], borderRadius: '50%',
                border: '2px solid var(--teal)',
                background: selected ? 'var(--teal)' : 'transparent',
                opacity: i === 2 ? 0.7 : 1, cursor: 'pointer', padding: 0,
              }}
            />
          )
        })}
      </div>
      <div className="serif" style={{ display: 'flex', justifyContent: 'space-between', opacity: 0.8, fontSize: '.9rem' }}>
        <span>{left}</span>
        <span>{right}</span>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd web && npx vitest run src/ui/Slider.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/ui/Slider.tsx web/src/ui/Slider.test.tsx
git commit -m "feat(ui): 5-point OEJTS slider"
```

---

## Task 3: Live-data hooks

**Files:**
- Create: `web/src/hooks/useNow.ts`, `web/src/hooks/useActiveSession.ts`, `web/src/hooks/useTaker.ts`, `web/src/hooks/useSharedList.ts`
- Create test: `web/src/hooks/useNow.test.tsx`

- [ ] **Step 1: Write the failing test for useNow**

Create `web/src/hooks/useNow.test.tsx`:
```tsx
import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useNow } from './useNow'

describe('useNow', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('advances on the given interval', () => {
    const { result } = renderHook(() => useNow(1000))
    const first = result.current
    act(() => { vi.advanceTimersByTime(1000) })
    expect(result.current).toBeGreaterThan(first)
  })
})
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd web && npx vitest run src/hooks/useNow.test.tsx`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement the hooks**

Create `web/src/hooks/useNow.ts`:
```ts
import { useEffect, useState } from 'react'

/** Returns Date.now(), re-rendering every `intervalMs`. */
export function useNow(intervalMs = 1000): number {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), intervalMs)
    return () => clearInterval(id)
  }, [intervalMs])
  return now
}
```

Create `web/src/hooks/useActiveSession.ts`:
```ts
import { useEffect, useState } from 'react'
import { collection, onSnapshot, query, where, limit } from 'firebase/firestore'
import { db } from '../firebase'
import type { SessionDoc } from '../data/sessions'

export function useActiveSession(): { session: SessionDoc | null; loading: boolean } {
  const [session, setSession] = useState<SessionDoc | null>(null)
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    const q = query(collection(db, 'sessions'), where('status', '==', 'active'), limit(1))
    return onSnapshot(q, (snap) => {
      setSession(snap.empty ? null : { id: snap.docs[0].id, ...(snap.docs[0].data() as Omit<SessionDoc, 'id'>) })
      setLoading(false)
    })
  }, [])
  return { session, loading }
}
```

Create `web/src/hooks/useTaker.ts`:
```ts
import { useEffect, useState } from 'react'
import { doc, onSnapshot } from 'firebase/firestore'
import { db } from '../firebase'
import { normalizeUsername, TakerDoc } from '../data/takers'

export function useTaker(username: string | null): TakerDoc | null {
  const [taker, setTaker] = useState<TakerDoc | null>(null)
  useEffect(() => {
    if (!username) { setTaker(null); return }
    return onSnapshot(doc(db, 'takers', normalizeUsername(username)), (snap) => {
      setTaker(snap.exists() ? (snap.data() as TakerDoc) : null)
    })
  }, [username])
  return taker
}
```

Create `web/src/hooks/useSharedList.ts`:
```ts
import { useEffect, useState } from 'react'
import { collection, onSnapshot, query, where } from 'firebase/firestore'
import { db } from '../firebase'

export interface SharedEntry { username: string; type: string }

/** Live list of sharers in a session. Empty when sessionId is null. */
export function useSharedList(sessionId: string | null): SharedEntry[] {
  const [list, setList] = useState<SharedEntry[]>([])
  useEffect(() => {
    if (!sessionId) { setList([]); return }
    const q = query(
      collection(db, 'takers'),
      where('sessionId', '==', sessionId),
      where('sharing', '==', true),
    )
    return onSnapshot(q, (snap) => {
      setList(
        snap.docs
          .map((d) => d.data())
          .filter((t) => t.completed && t.type)
          .map((t) => ({ username: t.username as string, type: t.type as string })),
      )
    })
  }, [sessionId])
  return list
}
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd web && npx vitest run src/hooks/useNow.test.tsx`
Expected: PASS. (The Firestore hooks are thin subscription wrappers exercised via the screens in later tasks.)

- [ ] **Step 5: Commit**

```bash
git add web/src/hooks
git commit -m "feat(hooks): live clock + session/taker/shared-list subscriptions"
```

---

## Task 4: Submit orchestration (sessionId at submit + latecomer grouping)

**Files:**
- Create: `web/src/data/submit.ts`, `web/src/data/submit.test.ts`

Behavior (spec §6, §8): on submit, compute type → seRank/seStrength, bind the taker to the **session active at submit time** (or null = session-less), persist completion, and **if that session is already frozen**, immediately assign the taker to the smaller group (`assignLatecomer`). If not frozen, leave `group` null (it's set at the freeze).

- [ ] **Step 1: Write the failing test**

Create `web/src/data/submit.test.ts`:
```ts
import { describe, it, expect, beforeEach, afterAll } from 'vitest'
import { getTestEnv } from '../../test/emulator'
import { doc, getDoc, setDoc } from 'firebase/firestore'
import { submitTest } from './submit'
import type { Answers, AnswerValue } from '../domain/types'
import { OEJTS_ITEMS } from '../domain/oejts'

const answersAll = (v: AnswerValue): Answers =>
  Object.fromEntries(OEJTS_ITEMS.map((i) => [i.id, v])) as Answers

describe('submitTest (emulator)', () => {
  beforeEach(async () => { (await getTestEnv()).clearFirestore() })
  afterAll(async () => { await (await getTestEnv()).cleanup() })

  it('binds to the active session, stamps type/seRank, leaves group null when unfrozen', async () => {
    const env = await getTestEnv()
    await env.withSecurityRulesDisabled(async (ctx) => {
      const db = ctx.firestore()
      await setDoc(doc(db, 'takers', 'mae'), { username: 'Mae', answers: answersAll(3), completed: false })
      await setDoc(doc(db, 'sessions', 's1'), { status: 'active', timerMinutes: 30, groupsFrozenAt: null })
      await submitTest(db, 'Mae', answersAll(3), 's1')
      const t = (await getDoc(doc(db, 'takers', 'mae'))).data()!
      expect(t.completed).toBe(true)
      expect(t.type).toMatch(/^[EI][SN][TF][JP]$/)
      expect(t.sessionId).toBe('s1')
      expect(t.group).toBeNull()
    })
  })

  it('latecomer in a frozen session is placed into the smaller group', async () => {
    const env = await getTestEnv()
    await env.withSecurityRulesDisabled(async (ctx) => {
      const db = ctx.firestore()
      await setDoc(doc(db, 'sessions', 's1'), { status: 'active', timerMinutes: 30, groupsFrozenAt: 1 })
      // existing: 2 scavenger, 1 games -> latecomer should go to games
      await setDoc(doc(db, 'takers', 'a'), { username: 'a', sessionId: 's1', completed: true, group: 'scavenger', sharing: false })
      await setDoc(doc(db, 'takers', 'b'), { username: 'b', sessionId: 's1', completed: true, group: 'scavenger', sharing: false })
      await setDoc(doc(db, 'takers', 'c'), { username: 'c', sessionId: 's1', completed: true, group: 'games', sharing: false })
      await setDoc(doc(db, 'takers', 'late'), { username: 'Late', answers: answersAll(3), completed: false })
      await submitTest(db, 'Late', answersAll(3), 's1')
      expect((await getDoc(doc(db, 'takers', 'late'))).data()!.group).toBe('games')
    })
  })

  it('session-less submit (null session) completes with no group', async () => {
    const env = await getTestEnv()
    await env.withSecurityRulesDisabled(async (ctx) => {
      const db = ctx.firestore()
      await setDoc(doc(db, 'takers', 'solo'), { username: 'Solo', answers: answersAll(3), completed: false })
      await submitTest(db, 'Solo', answersAll(3), null)
      const t = (await getDoc(doc(db, 'takers', 'solo'))).data()!
      expect(t.completed).toBe(true)
      expect(t.sessionId).toBeNull()
      expect(t.group).toBeNull()
    })
  })
})
```

- [ ] **Step 2: Run to confirm failure**

Run from `web/`: `firebase emulators:exec --only firestore "npx vitest run src/data/submit.test.ts"`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

Create `web/src/data/submit.ts`:
```ts
import {
  Firestore, doc, getDoc, updateDoc, collection, query, where, getDocs, serverTimestamp,
} from 'firebase/firestore'
import { scoreType } from '../domain/oejts'
import { seRank, seStrength } from '../domain/seRank'
import { assignLatecomer, GroupCounts } from '../domain/grouping'
import { normalizeUsername } from './takers'
import type { Answers, Group } from '../domain/types'

async function countGroups(db: Firestore, sessionId: string): Promise<GroupCounts> {
  const snap = await getDocs(query(collection(db, 'takers'), where('sessionId', '==', sessionId)))
  const counts: GroupCounts = { scavenger: 0, games: 0 }
  snap.docs.forEach((d) => {
    const g = d.data().group as Group | null
    if (g === 'scavenger' || g === 'games') counts[g]++
  })
  return counts
}

/** Completes a taker: binds session, scores, and assigns a latecomer group if frozen. */
export async function submitTest(
  db: Firestore, username: string, answers: Answers, activeSessionId: string | null,
): Promise<void> {
  const result = scoreType(answers)
  if (!result) throw new Error('Test is incomplete')

  let group: Group | null = null
  if (activeSessionId) {
    const sessionSnap = await getDoc(doc(db, 'sessions', activeSessionId))
    if (sessionSnap.exists() && sessionSnap.data().groupsFrozenAt) {
      group = assignLatecomer(await countGroups(db, activeSessionId))
    }
  }

  await updateDoc(doc(db, 'takers', normalizeUsername(username)), {
    completed: true,
    type: result.type,
    axisScores: result.axisScores,
    seRank: seRank(result.type),
    seStrength: seStrength(result.axisScores),
    sessionId: activeSessionId,
    group,
    completedAt: serverTimestamp(),
    updatedAt: serverTimestamp(),
  })
}
```

- [ ] **Step 4: Run to confirm pass**

Run from `web/`: `firebase emulators:exec --only firestore "npx vitest run src/data/submit.test.ts"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/data/submit.ts web/src/data/submit.test.ts
git commit -m "feat(data): submit orchestration — session binding + latecomer grouping"
```

---

## Task 5: Landing screen (username entry + resume)

**Files:**
- Create: `web/src/routes/Landing.tsx`, `web/src/routes/Landing.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `web/src/routes/Landing.test.tsx`:
```tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { Landing } from './Landing'

describe('Landing', () => {
  it('requires a non-empty username and reports it trimmed', () => {
    const onBegin = vi.fn()
    render(<Landing onBegin={onBegin} />)
    const begin = screen.getByRole('button', { name: /begin/i })
    fireEvent.click(begin)
    expect(onBegin).not.toHaveBeenCalled() // empty -> ignored
    fireEvent.change(screen.getByPlaceholderText(/username/i), { target: { value: '  Donovan ' } })
    fireEvent.click(begin)
    expect(onBegin).toHaveBeenCalledWith('Donovan')
  })
})
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd web && npx vitest run src/routes/Landing.test.tsx`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

Create `web/src/routes/Landing.tsx`:
```tsx
import { useState } from 'react'
import { Button } from '../ui/Button'

export function Landing({ onBegin }: { onBegin: (username: string) => void }) {
  const [name, setName] = useState('')
  const submit = () => {
    const trimmed = name.trim()
    if (trimmed) onBegin(trimmed)
  }
  return (
    <div className="screen" style={{ background: 'linear-gradient(160deg, var(--pink) 0%, var(--cream) 70%)' }}>
      <div className="card">
        <h1 style={{ margin: '0 0 1rem', fontWeight: 800 }}>Personality Test</h1>
        <input
          placeholder="enter a username…"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && submit()}
          style={{ width: '100%', border: '1.5px solid var(--pink-deep)', borderRadius: 14, padding: '.7rem .9rem', marginBottom: '1rem', fontSize: '.95rem' }}
        />
        <Button onClick={submit} style={{ width: '100%' }}>Begin →</Button>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd web && npx vitest run src/routes/Landing.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/routes/Landing.tsx web/src/routes/Landing.test.tsx
git commit -m "feat(ui): username landing screen"
```

---

## Task 6: Question screen (progress + slider + autosave + resume)

**Files:**
- Create: `web/src/routes/Question.tsx`, `web/src/routes/Question.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `web/src/routes/Question.test.tsx`:
```tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { Question } from './Question'
import { OEJTS_ITEMS } from '../domain/oejts'

describe('Question', () => {
  it('renders the item at the resume index and autosaves on answer', () => {
    const onAnswer = vi.fn()
    render(<Question index={17} item={OEJTS_ITEMS[17]} total={32} onAnswer={onAnswer} value={undefined} />)
    expect(screen.getByText('Question 18 of 32')).toBeInTheDocument()
    fireEvent.click(screen.getAllByRole('radio')[4])
    expect(onAnswer).toHaveBeenCalledWith(OEJTS_ITEMS[17].id, 5)
  })
})
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd web && npx vitest run src/routes/Question.test.tsx`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

Create `web/src/routes/Question.tsx`:
```tsx
import { ProgressBar } from '../ui/ProgressBar'
import { Slider } from '../ui/Slider'
import type { AnswerValue, OejtsItem } from '../domain/types'

interface Props {
  index: number              // 0-based
  total: number
  item: OejtsItem
  value: AnswerValue | undefined
  onAnswer: (itemId: number, value: AnswerValue) => void
}

export function Question({ index, total, item, value, onAnswer }: Props) {
  return (
    <div className="screen">
      <div className="card" style={{ textAlign: 'left' }}>
        <ProgressBar current={index + 1} total={total} />
        <p style={{ fontSize: '1.05rem', fontWeight: 600, lineHeight: 1.35, margin: '1.2rem 0 0' }}>
          {item.left} <span style={{ opacity: 0.5 }}>↔</span> {item.right}
        </p>
        <Slider left={item.left} right={item.right} value={value} onChange={(v) => onAnswer(item.id, v)} />
      </div>
    </div>
  )
}
```

> **Note:** advancing to the next item is handled by the parent `TestApp` (Task 8): when `onAnswer` fires it persists via `recordAnswer` and moves to the next unanswered index, so answering both autosaves and advances.

- [ ] **Step 4: Run to confirm pass**

Run: `cd web && npx vitest run src/routes/Question.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/routes/Question.tsx web/src/routes/Question.test.tsx
git commit -m "feat(ui): question screen (progress + slider)"
```

---

## Task 7: Sharing prompt + RevealBanner + SharedList + Result screen

**Files:**
- Create: `web/src/routes/SharingPrompt.tsx`, `web/src/ui/RevealBanner.tsx`, `web/src/ui/SharedList.tsx`, `web/src/routes/Result.tsx`
- Create tests: `web/src/routes/Result.test.tsx`, `web/src/ui/SharedList.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `web/src/ui/SharedList.test.tsx`:
```tsx
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { SharedList } from './SharedList'

describe('SharedList', () => {
  it('renders each sharer with a clean (underline-free) teal type link', () => {
    render(<SharedList entries={[{ username: 'maria', type: 'ENFP' }]} />)
    const link = screen.getByRole('link', { name: 'ENFP' })
    expect(link).toHaveAttribute('href', 'https://www.16personalities.com/enfp-personality')
    expect(link).toHaveClass('clean')
    expect(screen.getByText('maria')).toBeInTheDocument()
  })
})
```

Create `web/src/routes/Result.test.tsx`:
```tsx
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Result } from './Result'

const base = {
  username: 'Donovan', type: 'INTJ', sharing: true,
  entries: [], onToggleShare: () => {},
}

describe('Result', () => {
  it('shows the "check back in T minutes" copy while T > 0', () => {
    render(<Result {...base} t={12} group={null} />)
    expect(screen.getByText(/Donovan, your answers to the test questions indicate that you are an INTJ!/)).toBeInTheDocument()
    expect(screen.getByText(/Check back in 12 minutes/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /read more/i })).toHaveAttribute(
      'href', 'https://www.16personalities.com/intj-personality',
    )
  })

  it('reveals the scavenger group when T = 0', () => {
    render(<Result {...base} t={0} group="scavenger" />)
    expect(screen.getByText(/You're in the scavenger hunt group!/)).toBeInTheDocument()
  })

  it('reveals the games group when T = 0', () => {
    render(<Result {...base} t={0} group="games" />)
    expect(screen.getByText(/You're in the games group!/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd web && npx vitest run src/routes/Result.test.tsx src/ui/SharedList.test.tsx`
Expected: FAIL — modules missing.

- [ ] **Step 3: Implement the pieces**

Create `web/src/ui/SharedList.tsx`:
```tsx
import { personalityUrl } from '../domain/personalityUrl'
import type { SharedEntry } from '../hooks/useSharedList'

export function SharedList({ entries }: { entries: SharedEntry[] }) {
  if (entries.length === 0) return null
  return (
    <div style={{ background: 'rgba(1,64,79,.06)', border: '1px solid rgba(1,64,79,.12)', borderRadius: 12, padding: '.7rem .8rem', width: '100%', textAlign: 'left', marginTop: '.6rem' }}>
      <div style={{ opacity: 0.7, marginBottom: '.3rem', fontSize: '.8rem' }}>Shared in this session</div>
      {entries.map((e) => (
        <div key={e.username} style={{ display: 'flex', justifyContent: 'space-between', padding: '.2rem 0', fontSize: '.85rem' }}>
          <span>User: {e.username}</span>
          <span>Test Result: <a className="clean" href={personalityUrl(e.type)} target="_blank" rel="noreferrer">{e.type}</a></span>
        </div>
      ))}
    </div>
  )
}
```

Create `web/src/ui/RevealBanner.tsx`:
```tsx
import type { Group } from '../domain/types'

const LABEL: Record<Group, string> = { scavenger: 'Scavenger Hunt', games: 'Games' }

/** Persistent top banner shown to a mid-test taker once their group is set. */
export function RevealBanner({ group }: { group: Group }) {
  return (
    <div style={{ position: 'sticky', top: 0, zIndex: 10, background: 'var(--teal)', color: 'var(--cream)', padding: '.6rem .8rem', textAlign: 'center', fontWeight: 600, fontSize: '.85rem' }}>
      ⏱ Time's up — you're in the <span style={{ color: 'var(--pink)' }}>{LABEL[group]}</span> group. Finish your test for your full result.
    </div>
  )
}
```

Create `web/src/routes/SharingPrompt.tsx`:
```tsx
import { Button } from '../ui/Button'

export function SharingPrompt({ onChoose }: { onChoose: (share: boolean) => void }) {
  return (
    <div className="screen" style={{ background: 'linear-gradient(160deg, var(--pink) 0%, var(--cream) 75%)' }}>
      <div className="card">
        <p style={{ fontSize: '1rem', lineHeight: 1.4 }}>
          Share your result with others in this session who have also taken the test and shared theirs?
        </p>
        <div style={{ display: 'flex', gap: '.8rem', justifyContent: 'center', marginTop: '1rem' }}>
          <Button onClick={() => onChoose(true)}>Yes, share</Button>
          <Button onClick={() => onChoose(false)} style={{ background: 'transparent', color: 'var(--teal)', border: '1.5px solid var(--teal)' }}>No, keep private</Button>
        </div>
      </div>
    </div>
  )
}
```

Create `web/src/routes/Result.tsx`:
```tsx
import { personalityUrl } from '../domain/personalityUrl'
import { SharedList } from '../ui/SharedList'
import type { Group } from '../domain/types'
import type { SharedEntry } from '../hooks/useSharedList'

interface Props {
  username: string
  type: string
  t: number
  group: Group | null
  sharing: boolean
  entries: SharedEntry[]
  onToggleShare: (next: boolean) => void
}

export function Result({ username, type, t, group, sharing, entries, onToggleShare }: Props) {
  return (
    <div className="screen" style={{ background: 'linear-gradient(160deg, var(--pink) 0%, var(--cream) 75%)' }}>
      <div className="card" style={{ background: 'transparent', boxShadow: 'none' }}>
        <p className="serif" style={{ fontSize: '1.05rem', opacity: 0.85, margin: 0 }}>
          {username}, your answers to the test questions indicate that you are an
        </p>
        <div style={{ fontSize: '2.7rem', fontWeight: 800, letterSpacing: '.08em', margin: '.3rem 0' }}>{type}</div>

        {t > 0 ? (
          <p style={{ margin: '.4rem 0' }}>Check back in {t} minute{t === 1 ? '' : 's'} to find out what activity group you'll participate in</p>
        ) : group ? (
          <div style={{ background: 'var(--teal)', color: 'var(--cream)', borderRadius: 999, padding: '.3rem .9rem', display: 'inline-block', fontWeight: 700, margin: '.4rem 0' }}>
            You're in the {group === 'scavenger' ? 'scavenger hunt' : 'games'} group!
          </div>
        ) : null}

        <p style={{ marginTop: '.6rem' }}>
          To read more, click here:{' '}
          <a className="clean" href={personalityUrl(type)} target="_blank" rel="noreferrer">Read more about {type} →</a>
        </p>

        <label style={{ display: 'flex', gap: '.5rem', justifyContent: 'center', alignItems: 'center', marginTop: '.8rem', fontSize: '.85rem', cursor: 'pointer' }}>
          <input type="checkbox" checked={sharing} onChange={(e) => onToggleShare(e.target.checked)} />
          Share my result with this session
        </label>

        {sharing && <SharedList entries={entries} />}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd web && npx vitest run src/routes/Result.test.tsx src/ui/SharedList.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/routes/SharingPrompt.tsx web/src/ui/RevealBanner.tsx web/src/ui/SharedList.tsx web/src/routes/Result.tsx web/src/routes/Result.test.tsx web/src/ui/SharedList.test.tsx
git commit -m "feat(ui): sharing prompt, reveal banner, shared list, result screen"
```

---

## Task 8: TestApp flow + routing wiring

**Files:**
- Create: `web/src/routes/TestApp.tsx`
- Modify: `web/src/App.tsx`
- Install: `react-router-dom`

This is the state machine that strings the screens together. It: ensures anonymous auth; on username submit upserts the taker and resumes at the first unanswered item; autosaves each answer; shows the sharing prompt after the last item; submits; then shows the result with a live T countdown and reveal. It also triggers the freeze fallback when T reaches 0, and shows the `RevealBanner` if the group is assigned while still testing.

- [ ] **Step 1: Install the router**

Run: `cd web && npm install react-router-dom`

- [ ] **Step 2: Implement TestApp**

Create `web/src/routes/TestApp.tsx`:
```tsx
import { useEffect, useMemo, useState } from 'react'
import { db } from '../firebase'
import { ensureAnonymous } from '../auth/takerAuth'
import { OEJTS_ITEMS } from '../domain/oejts'
import { computeT } from '../domain/timer'
import { upsertTaker, recordAnswer, setSharing } from '../data/takers'
import { submitTest } from '../data/submit'
import { freezeSessionGroups } from '../data/freeze'
import { useActiveSession } from '../hooks/useActiveSession'
import { useTaker } from '../hooks/useTaker'
import { useSharedList } from '../hooks/useSharedList'
import { useNow } from '../hooks/useNow'
import { Landing } from './Landing'
import { Question } from './Question'
import { SharingPrompt } from './SharingPrompt'
import { Result } from './Result'
import { RevealBanner } from '../ui/RevealBanner'
import type { AnswerValue } from '../domain/types'

export function TestApp() {
  const [username, setUsername] = useState<string | null>(null)
  const [phase, setPhase] = useState<'landing' | 'test' | 'sharing' | 'result'>('landing')
  const { session } = useActiveSession()
  const taker = useTaker(username)
  const now = useNow(1000)

  useEffect(() => { ensureAnonymous() }, [])

  const firstUnanswered = useMemo(() => {
    if (!taker) return 0
    const idx = OEJTS_ITEMS.findIndex((i) => taker.answers?.[i.id] === undefined)
    return idx === -1 ? OEJTS_ITEMS.length : idx
  }, [taker])

  const onBegin = async (name: string) => {
    setUsername(name)
    await upsertTaker(db, name)
    setPhase('test')
  }

  // Resume completed takers straight to the result.
  useEffect(() => {
    if (taker?.completed && phase === 'test') setPhase('result')
  }, [taker?.completed, phase])

  const onAnswer = async (itemId: number, value: AnswerValue) => {
    if (!username) return
    await recordAnswer(db, username, itemId, value)
    if (firstUnanswered + 1 >= OEJTS_ITEMS.length) setPhase('sharing')
  }

  const onChooseShare = async (share: boolean) => {
    if (!username) return
    await setSharing(db, username, share)
    await submitTest(db, username, taker!.answers, session?.id ?? null)
    setPhase('result')
  }

  // T countdown + freeze fallback
  const t = session?.startedAt
    ? computeT(Number(session.startedAt) * 0 + sessionStartMs(session), session.timerMinutes, now)
    : 0
  useEffect(() => {
    if (session && !session.groupsFrozenAt && t === 0 && session.status === 'active') {
      freezeSessionGroups(db, session.id).catch(() => {})
    }
  }, [session?.id, session?.groupsFrozenAt, t, session?.status])

  const entries = useSharedList(taker?.sessionId ?? null)

  if (phase === 'landing' || !username) return <Landing onBegin={onBegin} />

  if (phase === 'test' && taker) {
    const idx = Math.min(firstUnanswered, OEJTS_ITEMS.length - 1)
    return (
      <>
        {taker.group && t === 0 && <RevealBanner group={taker.group} />}
        <Question
          index={idx}
          total={OEJTS_ITEMS.length}
          item={OEJTS_ITEMS[idx]}
          value={taker.answers?.[OEJTS_ITEMS[idx].id]}
          onAnswer={onAnswer}
        />
      </>
    )
  }

  if (phase === 'sharing') return <SharingPrompt onChoose={onChooseShare} />

  if (phase === 'result' && taker) {
    return (
      <Result
        username={taker.username}
        type={taker.type ?? ''}
        t={t}
        group={taker.group}
        sharing={taker.sharing}
        entries={entries}
        onToggleShare={(next) => setSharing(db, username, next)}
      />
    )
  }
  return null
}

/** Firestore Timestamp -> ms. */
function sessionStartMs(session: { startedAt: unknown }): number {
  const s = session.startedAt as { toMillis?: () => number } | number | null
  if (s && typeof s === 'object' && 'toMillis' in s && s.toMillis) return s.toMillis()
  return typeof s === 'number' ? s : Date.now()
}
```

> **Implementation note:** the `t` line above is written awkwardly to highlight the Timestamp→ms conversion — simplify to `const startMs = session ? sessionStartMs(session) : 0; const t = session ? computeT(startMs, session.timerMinutes, now) : 0`. Keep the `sessionStartMs` helper; Firestore returns a `Timestamp`, not a number.

- [ ] **Step 3: Wire routes**

Replace `web/src/App.tsx`:
```tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { TestApp } from './routes/TestApp'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/personality-test" element={<TestApp />} />
        <Route path="*" element={<Navigate to="/personality-test" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
```

- [ ] **Step 4: Typecheck + build**

Run: `cd web && npm run build`
Expected: clean build. Fix any type errors (notably the `t`/`sessionStartMs` simplification from the note).

- [ ] **Step 5: Manual smoke test against emulators**

Run two terminals from `web/`:
```bash
# terminal 1
firebase emulators:start --only firestore,auth
# terminal 2 (with VITE_USE_EMULATOR=1 in .env.local)
npm run dev
```
Visit `http://localhost:5173/personality-test`. Verify: username → 32 questions advance + autosave → sharing prompt → result with "check back" copy. Use the Emulator UI to create an `active` session and confirm the countdown + reveal.

- [ ] **Step 6: Commit**

```bash
git add web/src/routes/TestApp.tsx web/src/App.tsx web/package.json web/package-lock.json
git commit -m "feat(ui): wire test-taker flow (resume, autosave, submit, reveal)"
```

---

## Self-review (completed during planning)

- **Spec coverage:** §4 routes (`/personality-test`) → Task 8; §6 flow (username/resume, autosave, sharing prompt, exact result copy, shared list, opt in/out) → Tasks 5–8; §8 reveal timer + banner + latecomer → Tasks 3, 4, 7, 8; §10 look & feel → Tasks 1, 2, 7. The exact result string and "scavenger hunt"/"games" wording are asserted in `Result.test.tsx`.
- **Type consistency:** `Group`, `AnswerValue`, `OejtsItem`, `SharedEntry`, `SessionDoc`, `TakerDoc` reused from Plan 1 / hooks; `submitTest`, `recordAnswer`, `setSharing`, `freezeSessionGroups`, `computeT`, `personalityUrl` signatures match their definitions.
- **Known gap handed to Plan 3:** the admin "reveal now"/recompute/override/delete flows and the manage-admins UI. The taker client only triggers the freeze *fallback* when T hits 0.

## Next: Plan 3 — Admin UI (`2026-06-08-personality-test-admin-ui.md`).
