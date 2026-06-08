import { signInAnonymously, onAuthStateChanged } from 'firebase/auth'
import type { User } from 'firebase/auth'
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
