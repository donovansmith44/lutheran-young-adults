# Personality Test — Admin UI Implementation Plan (Plan 3 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `/admin` page — Google sign-in gated to the allowlist — for managing test sessions: start/end/rename/timer, a live roster, reveal-now / recompute / per-taker override, archive, delete (with a typed-`DELETE` guard), and managing the admin allowlist. Then deploy to Firebase Hosting.

**Architecture:** Admin-only data operations are added to `web/src/data/adminOps.ts` (group override + recompute) and reuse Plan 1's `sessions.ts`, `freeze.ts`, `admins.ts`. The admin screens live under `web/src/routes/admin/`, gated by an `AdminGate` that checks Firebase Auth + the allowlist. Live data uses Firestore `onSnapshot`. Behavior is tested with @testing-library/react (gate + delete-confirm + start-guard); data ops against the Firebase emulator.

**Tech Stack:** React 18 + TS + Vite, react-router-dom, Firebase Auth (Google) + Firestore, Vitest + @testing-library/react, firebase-tools (deploy).

**Prerequisite:** Plans 1 and 2 complete and green. **Depends on:** `data/sessions.ts`, `data/freeze.ts`, `data/admins.ts`, `data/grouping.ts`, `auth/adminAuth.ts`, `hooks/*`.

**Spec:** `docs/superpowers/specs/2026-06-08-personality-test-app-design.md` (§9, §3)

---

## File structure (added by this plan)

```
web/src/
  data/
    adminOps.ts          # setTakerGroupOverride() + recomputeSessionGroups()
    adminOps.test.ts
  hooks/
    useSessions.ts       # subscribe all sessions (admin)
    useRoster.ts         # subscribe takers for a session
    useIsAdmin.ts        # auth state + allowlist check
  routes/admin/
    AdminGate.tsx        # sign-in + allowlist gate
    AdminPage.tsx        # layout + tab switch
    SessionList.tsx      # list + start form + controls
    DeleteConfirm.tsx    # typed-DELETE modal
    Roster.tsx           # live taker table + override controls
    ManageAdmins.tsx     # allowlist add/remove
  App.tsx                # add /admin route (modified)
```

---

## Task 1: Admin data operations (override + recompute)

**Files:**
- Create: `web/src/data/adminOps.ts`, `web/src/data/adminOps.test.ts`

`setTakerGroupOverride` pins a taker to a group (`groupOverride = true`). `recomputeSessionGroups` re-runs the freeze split **even if already frozen**, honoring overrides (so a rebalance after latecomers respects manual pins).

- [ ] **Step 1: Write the failing test**

Create `web/src/data/adminOps.test.ts`:
```ts
import { describe, it, expect, beforeEach, afterAll } from 'vitest'
import { getTestEnv } from '../../test/emulator'
import { doc, getDoc, setDoc } from 'firebase/firestore'
import { setTakerGroupOverride, recomputeSessionGroups } from './adminOps'

describe('adminOps (emulator)', () => {
  beforeEach(async () => { (await getTestEnv()).clearFirestore() })
  afterAll(async () => { await (await getTestEnv()).cleanup() })

  it('override pins a taker and marks groupOverride', async () => {
    const env = await getTestEnv()
    await env.withSecurityRulesDisabled(async (ctx) => {
      const db = ctx.firestore()
      await setDoc(doc(db, 'takers', 'x'), { username: 'x', group: 'games', groupOverride: false })
      await setTakerGroupOverride(db, 'x', 'scavenger')
      const t = (await getDoc(doc(db, 'takers', 'x'))).data()!
      expect(t.group).toBe('scavenger')
      expect(t.groupOverride).toBe(true)
    })
  })

  it('recompute re-splits completed takers but keeps overrides', async () => {
    const env = await getTestEnv()
    await env.withSecurityRulesDisabled(async (ctx) => {
      const db = ctx.firestore()
      await setDoc(doc(db, 'sessions', 's1'), { status: 'active', timerMinutes: 30, groupsFrozenAt: 1 })
      const mk = (id: string, seRank: number, extra = {}) =>
        setDoc(doc(db, 'takers', id), { username: id, sessionId: 's1', completed: true, seRank, seStrength: 0, group: null, groupOverride: false, ...extra })
      await mk('a', 1)
      await mk('b', 2)
      await mk('pinned', 1, { group: 'games', groupOverride: true })
      await recomputeSessionGroups(db, 's1')
      const grp = async (id: string) => (await getDoc(doc(db, 'takers', id))).data()!.group
      expect(await grp('pinned')).toBe('games') // untouched
      expect(['scavenger', 'games']).toContain(await grp('a'))
      expect(['scavenger', 'games']).toContain(await grp('b'))
    })
  })
})
```

- [ ] **Step 2: Run to confirm failure**

Run from `web/`: `firebase emulators:exec --only firestore "npx vitest run src/data/adminOps.test.ts"`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

Create `web/src/data/adminOps.ts`:
```ts
import {
  Firestore, doc, updateDoc, collection, query, where, getDocs, serverTimestamp,
} from 'firebase/firestore'
import { freezeGroups } from '../domain/grouping'
import type { Group, TakerForGrouping } from '../domain/types'

export async function setTakerGroupOverride(db: Firestore, username: string, group: Group): Promise<void> {
  await updateDoc(doc(db, 'takers', username), { group, groupOverride: true })
}

/** Re-runs the split for a session (even if already frozen), honoring overrides. */
export async function recomputeSessionGroups(db: Firestore, sessionId: string): Promise<void> {
  const snap = await getDocs(query(collection(db, 'takers'), where('sessionId', '==', sessionId)))
  const takers: TakerForGrouping[] = snap.docs.map((d) => {
    const t = d.data()
    return {
      id: d.id, completed: t.completed, seRank: t.seRank ?? undefined,
      seStrength: t.seStrength ?? undefined, group: t.group ?? null,
      groupOverride: t.groupOverride ?? false,
    }
  })
  const assignments = freezeGroups(takers)
  await Promise.all(
    Object.entries(assignments).map(([id, group]) => updateDoc(doc(db, 'takers', id), { group })),
  )
  await updateDoc(doc(db, 'sessions', sessionId), { groupsFrozenAt: serverTimestamp() })
}

export async function deleteSession(db: Firestore, id: string): Promise<void> {
  // Delete the session doc; takers keep their sessionId for archival audit.
  const { deleteDoc } = await import('firebase/firestore')
  await deleteDoc(doc(db, 'sessions', id))
}
```

- [ ] **Step 4: Run to confirm pass**

Run from `web/`: `firebase emulators:exec --only firestore "npx vitest run src/data/adminOps.test.ts"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/data/adminOps.ts web/src/data/adminOps.test.ts
git commit -m "feat(data): admin group override + recompute + delete-session"
```

---

## Task 2: Admin hooks (sessions, roster, isAdmin)

**Files:**
- Create: `web/src/hooks/useSessions.ts`, `web/src/hooks/useRoster.ts`, `web/src/hooks/useIsAdmin.ts`

- [ ] **Step 1: Implement useSessions**

Create `web/src/hooks/useSessions.ts`:
```ts
import { useEffect, useState } from 'react'
import { collection, onSnapshot, orderBy, query } from 'firebase/firestore'
import { db } from '../firebase'
import type { SessionDoc } from '../data/sessions'

export function useSessions(): SessionDoc[] {
  const [sessions, setSessions] = useState<SessionDoc[]>([])
  useEffect(() => {
    const q = query(collection(db, 'sessions'), orderBy('startedAt', 'desc'))
    return onSnapshot(q, (snap) => {
      setSessions(snap.docs.map((d) => ({ id: d.id, ...(d.data() as Omit<SessionDoc, 'id'>) })))
    })
  }, [])
  return sessions
}
```

- [ ] **Step 2: Implement useRoster**

Create `web/src/hooks/useRoster.ts`:
```ts
import { useEffect, useState } from 'react'
import { collection, onSnapshot, query, where } from 'firebase/firestore'
import { db } from '../firebase'
import type { TakerDoc } from '../data/takers'

export interface RosterRow extends TakerDoc { id: string }

export function useRoster(sessionId: string | null): RosterRow[] {
  const [rows, setRows] = useState<RosterRow[]>([])
  useEffect(() => {
    if (!sessionId) { setRows([]); return }
    const q = query(collection(db, 'takers'), where('sessionId', '==', sessionId))
    return onSnapshot(q, (snap) => {
      setRows(snap.docs.map((d) => ({ id: d.id, ...(d.data() as TakerDoc) })))
    })
  }, [sessionId])
  return rows
}
```

- [ ] **Step 3: Implement useIsAdmin**

Create `web/src/hooks/useIsAdmin.ts`:
```ts
import { useEffect, useState } from 'react'
import { onAuthStateChanged, User } from 'firebase/auth'
import { auth } from '../firebase'
import { isAdmin } from '../auth/adminAuth'

export function useIsAdmin(): { user: User | null; admin: boolean; loading: boolean } {
  const [user, setUser] = useState<User | null>(null)
  const [admin, setAdmin] = useState(false)
  const [loading, setLoading] = useState(true)
  useEffect(() =>
    onAuthStateChanged(auth, async (u) => {
      setUser(u)
      setAdmin(await isAdmin(u))
      setLoading(false)
    }), [])
  return { user, admin, loading }
}
```

- [ ] **Step 4: Typecheck**

Run: `cd web && npx tsc -b`
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add web/src/hooks/useSessions.ts web/src/hooks/useRoster.ts web/src/hooks/useIsAdmin.ts
git commit -m "feat(hooks): admin sessions/roster/isAdmin subscriptions"
```

---

## Task 3: Admin gate

**Files:**
- Create: `web/src/routes/admin/AdminGate.tsx`, `web/src/routes/admin/AdminGate.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `web/src/routes/admin/AdminGate.test.tsx`:
```tsx
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'

vi.mock('../../hooks/useIsAdmin', () => ({ useIsAdmin: () => mockState }))
let mockState: { user: unknown; admin: boolean; loading: boolean }

import { AdminGate } from './AdminGate'

describe('AdminGate', () => {
  it('shows sign-in when not authenticated', () => {
    mockState = { user: null, admin: false, loading: false }
    render(<AdminGate><div>secret</div></AdminGate>)
    expect(screen.getByRole('button', { name: /sign in with google/i })).toBeInTheDocument()
    expect(screen.queryByText('secret')).not.toBeInTheDocument()
  })

  it('shows "not authorized" for a signed-in non-admin', () => {
    mockState = { user: { email: 'x@y.z' }, admin: false, loading: false }
    render(<AdminGate><div>secret</div></AdminGate>)
    expect(screen.getByText(/not authorized/i)).toBeInTheDocument()
    expect(screen.queryByText('secret')).not.toBeInTheDocument()
  })

  it('renders children for an allowlisted admin', () => {
    mockState = { user: { email: 'a@b.c' }, admin: true, loading: false }
    render(<AdminGate><div>secret</div></AdminGate>)
    expect(screen.getByText('secret')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd web && npx vitest run src/routes/admin/AdminGate.test.tsx`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

Create `web/src/routes/admin/AdminGate.tsx`:
```tsx
import { ReactNode } from 'react'
import { Button } from '../../ui/Button'
import { useIsAdmin } from '../../hooks/useIsAdmin'
import { signInWithGoogle, signOutAdmin } from '../../auth/adminAuth'

export function AdminGate({ children }: { children: ReactNode }) {
  const { user, admin, loading } = useIsAdmin()
  if (loading) return <div className="screen"><p className="serif">Loading…</p></div>
  if (!user) {
    return (
      <div className="screen">
        <div className="card">
          <h2>Admin</h2>
          <Button onClick={() => signInWithGoogle()}>Sign in with Google</Button>
        </div>
      </div>
    )
  }
  if (!admin) {
    return (
      <div className="screen">
        <div className="card">
          <p>Signed in as {user.email}, but you are <b>not authorized</b>.</p>
          <Button onClick={() => signOutAdmin()}>Sign out</Button>
        </div>
      </div>
    )
  }
  return <>{children}</>
}
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd web && npx vitest run src/routes/admin/AdminGate.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/routes/admin/AdminGate.tsx web/src/routes/admin/AdminGate.test.tsx
git commit -m "feat(admin): Google sign-in + allowlist gate"
```

---

## Task 4: Delete-confirm modal (typed DELETE)

**Files:**
- Create: `web/src/routes/admin/DeleteConfirm.tsx`, `web/src/routes/admin/DeleteConfirm.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `web/src/routes/admin/DeleteConfirm.test.tsx`:
```tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { DeleteConfirm } from './DeleteConfirm'

describe('DeleteConfirm', () => {
  it('enables delete only when the user types DELETE exactly', () => {
    const onConfirm = vi.fn()
    render(<DeleteConfirm name="Personality Day" onConfirm={onConfirm} onCancel={() => {}} />)
    const btn = screen.getByRole('button', { name: /^delete$/i })
    expect(btn).toBeDisabled()
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'delete' } })
    expect(btn).toBeDisabled() // case-sensitive
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'DELETE' } })
    expect(btn).toBeEnabled()
    fireEvent.click(btn)
    expect(onConfirm).toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd web && npx vitest run src/routes/admin/DeleteConfirm.test.tsx`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

Create `web/src/routes/admin/DeleteConfirm.tsx`:
```tsx
import { useState } from 'react'
import { Button } from '../../ui/Button'

interface Props { name: string; onConfirm: () => void; onCancel: () => void }

export function DeleteConfirm({ name, onConfirm, onCancel }: Props) {
  const [text, setText] = useState('')
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(1,64,79,.55)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
      <div className="card">
        <p>Are you sure you want to delete <b>{name}</b>? Type <b>DELETE</b> and press the button to confirm.</p>
        <input role="textbox" value={text} onChange={(e) => setText(e.target.value)}
          style={{ width: '100%', border: '1.5px solid var(--pink-deep)', borderRadius: 14, padding: '.6rem .8rem', margin: '.6rem 0' }} />
        <div style={{ display: 'flex', gap: '.6rem', justifyContent: 'flex-end' }}>
          <Button onClick={onCancel} style={{ background: 'transparent', color: 'var(--teal)', border: '1.5px solid var(--teal)' }}>Cancel</Button>
          <Button onClick={onConfirm} disabled={text !== 'DELETE'} style={{ background: '#a3322b' }}>Delete</Button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd web && npx vitest run src/routes/admin/DeleteConfirm.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/routes/admin/DeleteConfirm.tsx web/src/routes/admin/DeleteConfirm.test.tsx
git commit -m "feat(admin): typed-DELETE confirmation modal"
```

---

## Task 5: Session list + start form + controls

**Files:**
- Create: `web/src/routes/admin/SessionList.tsx`, `web/src/routes/admin/SessionList.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `web/src/routes/admin/SessionList.test.tsx`:
```tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { SessionList } from './SessionList'
import type { SessionDoc } from '../../data/sessions'

const active: SessionDoc = { id: 's1', name: 'Day', status: 'active', timerMinutes: 30, startedAt: 1, endedAt: null, groupsFrozenAt: null, createdBy: 'a@b.c' }

describe('SessionList', () => {
  it('disables Start while a session is active', () => {
    render(<SessionList sessions={[active]} onSelect={() => {}} selectedId="s1" />)
    expect(screen.getByRole('button', { name: /start session/i })).toBeDisabled()
  })

  it('enables Start when none is active and passes name + timer', () => {
    const onStart = vi.fn()
    render(<SessionList sessions={[]} onSelect={() => {}} selectedId={null} onStartOverride={onStart} />)
    fireEvent.change(screen.getByPlaceholderText(/session name/i), { target: { value: 'Personality Day' } })
    fireEvent.change(screen.getByLabelText(/timer/i), { target: { value: '20' } })
    fireEvent.click(screen.getByRole('button', { name: /start session/i }))
    expect(onStart).toHaveBeenCalledWith('Personality Day', 20)
  })
})
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd web && npx vitest run src/routes/admin/SessionList.test.tsx`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

Create `web/src/routes/admin/SessionList.tsx`:
```tsx
import { useState } from 'react'
import { db } from '../../firebase'
import { Button } from '../../ui/Button'
import { startSession, endSession, archiveSession } from '../../data/sessions'
import { freezeSessionGroups } from '../../data/freeze'
import { recomputeSessionGroups, deleteSession } from '../../data/adminOps'
import { DeleteConfirm } from './DeleteConfirm'
import { useIsAdmin } from '../../hooks/useIsAdmin'
import type { SessionDoc } from '../../data/sessions'

interface Props {
  sessions: SessionDoc[]
  selectedId: string | null
  onSelect: (id: string) => void
  // test seam: override the real startSession
  onStartOverride?: (name: string, timer: number) => void
}

export function SessionList({ sessions, selectedId, onSelect, onStartOverride }: Props) {
  const { user } = useIsAdmin()
  const [name, setName] = useState('')
  const [timer, setTimer] = useState(30)
  const [toDelete, setToDelete] = useState<SessionDoc | null>(null)
  const hasActive = sessions.some((s) => s.status === 'active')

  const start = () => {
    if (onStartOverride) return onStartOverride(name.trim(), Number(timer))
    startSession(db, { name: name.trim(), timerMinutes: Number(timer), createdBy: user?.email ?? '' })
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '.8rem' }}>
      <div className="card" style={{ width: '100%' }}>
        <h3 style={{ marginTop: 0 }}>Start a session</h3>
        <input placeholder="Session name" value={name} onChange={(e) => setName(e.target.value)}
          style={{ width: '100%', padding: '.5rem', borderRadius: 10, border: '1.5px solid var(--pink-deep)', marginBottom: '.5rem' }} />
        <label style={{ display: 'block', fontSize: '.8rem' }}>Timer (minutes)
          <input aria-label="timer minutes" type="number" value={timer} onChange={(e) => setTimer(Number(e.target.value))}
            style={{ width: '100%', padding: '.5rem', borderRadius: 10, border: '1.5px solid var(--pink-deep)' }} />
        </label>
        <Button onClick={start} disabled={hasActive || !name.trim()} style={{ marginTop: '.6rem' }}>Start session</Button>
        {hasActive && <p style={{ fontSize: '.75rem', opacity: 0.7 }}>End the active session before starting another.</p>}
      </div>

      {sessions.map((s) => (
        <div key={s.id} className="card" style={{ width: '100%', borderLeft: s.id === selectedId ? '4px solid var(--teal)' : undefined }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <button onClick={() => onSelect(s.id)} style={{ background: 'none', border: 'none', fontWeight: 700, cursor: 'pointer', color: 'var(--teal)' }}>
              {s.name} <span style={{ fontWeight: 400, opacity: 0.6, fontSize: '.8rem' }}>({s.status})</span>
            </button>
          </div>
          <div style={{ display: 'flex', gap: '.4rem', flexWrap: 'wrap', marginTop: '.5rem' }}>
            {s.status === 'active' && <Button onClick={() => freezeSessionGroups(db, s.id)}>Reveal now</Button>}
            <Button onClick={() => recomputeSessionGroups(db, s.id)}>Recompute</Button>
            {s.status === 'active' && <Button onClick={() => endSession(db, s.id)}>End</Button>}
            {s.status === 'ended' && <Button onClick={() => archiveSession(db, s.id)}>Archive</Button>}
            <Button onClick={() => setToDelete(s)} style={{ background: '#a3322b' }}>Delete</Button>
          </div>
        </div>
      ))}

      {toDelete && (
        <DeleteConfirm
          name={toDelete.name}
          onCancel={() => setToDelete(null)}
          onConfirm={() => { deleteSession(db, toDelete.id); setToDelete(null) }}
        />
      )}
    </div>
  )
}
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd web && npx vitest run src/routes/admin/SessionList.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/routes/admin/SessionList.tsx web/src/routes/admin/SessionList.test.tsx
git commit -m "feat(admin): session list, start form, reveal/recompute/end/archive/delete"
```

---

## Task 6: Live roster + per-taker override

**Files:**
- Create: `web/src/routes/admin/Roster.tsx`, `web/src/routes/admin/Roster.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `web/src/routes/admin/Roster.test.tsx`:
```tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { Roster } from './Roster'
import type { RosterRow } from '../../hooks/useRoster'

const rows: RosterRow[] = [
  { id: 'maria', username: 'maria', answers: {}, completed: true, type: 'ENFP', axisScores: null, seRank: 8, seStrength: 0, sharing: true, sessionId: 's1', group: 'games', groupOverride: false },
]

describe('Roster', () => {
  it('lists each taker with type, Se rank, group and an override control', () => {
    const onOverride = vi.fn()
    render(<Roster rows={rows} onOverride={onOverride} />)
    expect(screen.getByText('maria')).toBeInTheDocument()
    expect(screen.getByText('ENFP')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /move to scavenger/i }))
    expect(onOverride).toHaveBeenCalledWith('maria', 'scavenger')
  })
})
```

- [ ] **Step 2: Run to confirm failure**

Run: `cd web && npx vitest run src/routes/admin/Roster.test.tsx`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

Create `web/src/routes/admin/Roster.tsx`:
```tsx
import type { Group } from '../../domain/types'
import type { RosterRow } from '../../hooks/useRoster'

interface Props {
  rows: RosterRow[]
  onOverride: (username: string, group: Group) => void
}

export function Roster({ rows, onOverride }: Props) {
  return (
    <div className="card" style={{ width: '100%', overflowX: 'auto' }}>
      <h3 style={{ marginTop: 0 }}>Roster ({rows.length})</h3>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '.85rem' }}>
        <thead>
          <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--pink-deep)' }}>
            <th>User</th><th>Type</th><th>Se</th><th>Share</th><th>Group</th><th></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const other: Group = r.group === 'scavenger' ? 'games' : 'scavenger'
            return (
              <tr key={r.id} style={{ borderBottom: '1px solid rgba(1,64,79,.08)' }}>
                <td>{r.username}</td>
                <td>{r.completed ? r.type : <i style={{ opacity: 0.5 }}>testing…</i>}</td>
                <td>{r.seRank ?? '—'}</td>
                <td>{r.sharing ? '✓' : ''}</td>
                <td>{r.group ?? '—'}{r.groupOverride ? ' 📌' : ''}</td>
                <td>
                  <button onClick={() => onOverride(r.username, other)}
                    style={{ background: 'none', border: '1px solid var(--teal)', borderRadius: 999, padding: '.15rem .6rem', cursor: 'pointer', color: 'var(--teal)', fontSize: '.75rem' }}>
                    Move to {other === 'scavenger' ? 'scavenger' : 'games'}
                  </button>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 4: Run to confirm pass**

Run: `cd web && npx vitest run src/routes/admin/Roster.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/routes/admin/Roster.tsx web/src/routes/admin/Roster.test.tsx
git commit -m "feat(admin): live roster with per-taker group override"
```

---

## Task 7: Manage admins

**Files:**
- Create: `web/src/routes/admin/ManageAdmins.tsx`

- [ ] **Step 1: Implement (thin CRUD over the allowlist)**

Create `web/src/routes/admin/ManageAdmins.tsx`:
```tsx
import { useEffect, useState } from 'react'
import { collection, onSnapshot } from 'firebase/firestore'
import { db } from '../../firebase'
import { addAdmin, removeAdmin } from '../../data/admins'
import { Button } from '../../ui/Button'

export function ManageAdmins() {
  const [emails, setEmails] = useState<string[]>([])
  const [email, setEmail] = useState('')
  useEffect(() =>
    onSnapshot(collection(db, 'admins'), (snap) => setEmails(snap.docs.map((d) => d.id))), [])

  return (
    <div className="card" style={{ width: '100%' }}>
      <h3 style={{ marginTop: 0 }}>Admins</h3>
      <ul style={{ listStyle: 'none', padding: 0 }}>
        {emails.map((e) => (
          <li key={e} style={{ display: 'flex', justifyContent: 'space-between', padding: '.3rem 0' }}>
            <span>{e}</span>
            <button onClick={() => removeAdmin(db, e)} style={{ background: 'none', border: 'none', color: '#a3322b', cursor: 'pointer' }}>remove</button>
          </li>
        ))}
      </ul>
      <div style={{ display: 'flex', gap: '.5rem' }}>
        <input placeholder="email@domain" value={email} onChange={(e) => setEmail(e.target.value)}
          style={{ flex: 1, padding: '.5rem', borderRadius: 10, border: '1.5px solid var(--pink-deep)' }} />
        <Button onClick={() => { if (email.trim()) { addAdmin(db, email.trim()); setEmail('') } }}>Add</Button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Typecheck**

Run: `cd web && npx tsc -b`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add web/src/routes/admin/ManageAdmins.tsx
git commit -m "feat(admin): manage admin allowlist"
```

---

## Task 8: AdminPage assembly + route

**Files:**
- Create: `web/src/routes/admin/AdminPage.tsx`
- Modify: `web/src/App.tsx`

- [ ] **Step 1: Implement AdminPage**

Create `web/src/routes/admin/AdminPage.tsx`:
```tsx
import { useState } from 'react'
import { db } from '../../firebase'
import { AdminGate } from './AdminGate'
import { SessionList } from './SessionList'
import { Roster } from './Roster'
import { ManageAdmins } from './ManageAdmins'
import { useSessions } from '../../hooks/useSessions'
import { useRoster } from '../../hooks/useRoster'
import { setTakerGroupOverride } from '../../data/adminOps'

export function AdminPage() {
  const sessions = useSessions()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const rows = useRoster(selectedId)

  return (
    <AdminGate>
      <div style={{ maxWidth: 760, margin: '0 auto', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <h1>Session admin</h1>
        <SessionList sessions={sessions} selectedId={selectedId} onSelect={setSelectedId} />
        {selectedId && <Roster rows={rows} onOverride={(u, g) => setTakerGroupOverride(db, u, g)} />}
        <ManageAdmins />
      </div>
    </AdminGate>
  )
}
```

- [ ] **Step 2: Add the route**

In `web/src/App.tsx`, add the import and route:
```tsx
import { AdminPage } from './routes/admin/AdminPage'
// inside <Routes>, before the catch-all:
<Route path="/admin" element={<AdminPage />} />
```

- [ ] **Step 3: Build**

Run: `cd web && npm run build`
Expected: clean build.

- [ ] **Step 4: Manual smoke test**

With emulators + `npm run dev`, seed an admin in the Emulator UI (`admins/{your-emulator-email}`), sign in, start a session, take the test in another tab, confirm the roster updates live, reveal/recompute/override work, and delete requires typing `DELETE`.

- [ ] **Step 5: Commit**

```bash
git add web/src/routes/admin/AdminPage.tsx web/src/App.tsx
git commit -m "feat(admin): assemble admin page + /admin route"
```

---

## Task 9: Full sweep + deploy

**Files:**
- Modify: none (deploy)

- [ ] **Step 1: Run the entire test suite**

Run from `web/`:
```bash
npx vitest run src/domain src/ui src/hooks src/routes
firebase emulators:exec --only firestore,auth "npx vitest run src/data"
```
Expected: all green.

- [ ] **Step 2: Configure the real Firebase web app**

Fill `web/.env.local` with the production Firebase config (from the console). In the Firebase console, enable **Authentication → Google** and **Anonymous** sign-in providers, and add `lcmsyoungadults.org` (and the Hosting domain) to **Authorized domains**.

- [ ] **Step 3: Seed the first admin (one-time)**

In the console, create `admins/donovan@lcmsyoungadults.org` with `{ email: "donovan@lcmsyoungadults.org" }` (per `web/scripts/seed-admin.md`).

- [ ] **Step 4: Deploy rules + hosting**

Run from `web/`:
```bash
npm run build
firebase deploy --only firestore:rules,firestore:indexes,hosting
```
Expected: deploy succeeds; the printed Hosting URL serves `/personality-test` and `/admin`.

- [ ] **Step 5: Connect the custom domain**

In Firebase Console → Hosting → add custom domain `lcmsyoungadults.org` (and/or a subpath/sub­domain as desired); follow the DNS verification steps. Confirm `/personality-test` loads over the domain.

- [ ] **Step 6: Commit**

```bash
git add web/.env.example
git commit -m "chore: deploy config notes for personality-test app"
```

---

## Self-review (completed during planning)

- **Spec coverage:** §9 admin — Google gate (Task 3), start/end/rename/timer + single-active guard (Task 5 + Plan 1 §10), live roster (Task 6), reveal-now/recompute/override (Tasks 1, 5, 6), archive (Task 5), delete-with-`DELETE` (Tasks 4, 5), manage admins (Task 7); §3 access model enforced by rules (Plan 1) + gate (Task 3). Deploy + custom domain (Task 9).
- **Type consistency:** `Group`, `SessionDoc`, `TakerDoc`, `RosterRow`, `TakerForGrouping` reused; `setTakerGroupOverride`, `recomputeSessionGroups`, `deleteSession`, `startSession`, `endSession`, `archiveSession`, `freezeSessionGroups`, `isAdmin` signatures match definitions.
- **Note:** `renameSession`/`setTimerMinutes` exist in Plan 1's `sessions.ts`; wiring an inline rename/timer-edit into a session card is a small optional add not separately tasked — add it to `SessionList` if desired.

## Done
This completes the three-plan sequence (Foundation → Test-taker UI → Admin UI) for the Personality Test app. Marketing-site work is a separate, later spec.
