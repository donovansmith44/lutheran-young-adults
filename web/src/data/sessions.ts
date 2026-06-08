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
