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
