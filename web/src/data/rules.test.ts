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
