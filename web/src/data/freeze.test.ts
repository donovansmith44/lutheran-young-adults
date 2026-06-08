import { describe, it, expect, beforeEach, afterAll } from 'vitest'
import { getTestEnv } from '../../test/emulator'
import { doc, getDoc, setDoc } from 'firebase/firestore'
import { freezeSessionGroups } from './freeze'

async function seed(db: any, sessionId: string) {
  await setDoc(doc(db, 'sessions', sessionId), {
    name: 'A', status: 'active', timerMinutes: 30, startedAt: 1, endedAt: null,
    groupsFrozenAt: null, createdBy: 'd@x.org',
  })
  const mk = (id: string, seRank: number, completed = true) =>
    setDoc(doc(db, 'takers', id), {
      username: id, answers: {}, completed, type: 'ESTP', axisScores: { IE: 24, SN: 24, TF: 24, JP: 24 },
      seRank, seStrength: 0, sharing: false, sessionId, group: null, groupOverride: false,
    })
  await Promise.all([mk('a', 1), mk('b', 2), mk('c', 7), mk('d', 8)])
}

describe('freezeSessionGroups (emulator)', () => {
  beforeEach(async () => { (await getTestEnv()).clearFirestore() })
  afterAll(async () => { await (await getTestEnv()).cleanup() })

  it('writes groups and stamps groupsFrozenAt', async () => {
    const env = await getTestEnv()
    await env.withSecurityRulesDisabled(async (ctx) => {
      const db = ctx.firestore()
      await seed(db, 's1')
      await freezeSessionGroups(db, 's1')
      const grp = async (id: string) => (await getDoc(doc(db, 'takers', id))).data()!.group
      expect(await grp('a')).toBe('scavenger')
      expect(await grp('b')).toBe('scavenger')
      expect(await grp('c')).toBe('games')
      expect(await grp('d')).toBe('games')
      const s = await getDoc(doc(db, 'sessions', 's1'))
      expect(s.data()!.groupsFrozenAt).not.toBeNull()
    })
  })

  it('is a no-op if already frozen', async () => {
    const env = await getTestEnv()
    await env.withSecurityRulesDisabled(async (ctx) => {
      const db = ctx.firestore()
      await seed(db, 's1')
      await freezeSessionGroups(db, 's1')
      const first = (await getDoc(doc(db, 'sessions', 's1'))).data()!.groupsFrozenAt
      await freezeSessionGroups(db, 's1')
      const second = (await getDoc(doc(db, 'sessions', 's1'))).data()!.groupsFrozenAt
      expect(second).toEqual(first)
    })
  })
})
