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
