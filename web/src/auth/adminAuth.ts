import { GoogleAuthProvider, signInWithPopup, signOut } from 'firebase/auth'
import type { User } from 'firebase/auth'
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
