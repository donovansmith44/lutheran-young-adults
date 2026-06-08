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
