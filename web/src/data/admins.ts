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
