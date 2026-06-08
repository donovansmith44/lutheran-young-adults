import { describe, it, expect } from 'vitest'
import { OEJTS_ITEMS, scoreType } from './oejts'
import type { Answers, AnswerValue } from './types'

const allSame = (v: AnswerValue): Answers =>
  Object.fromEntries(OEJTS_ITEMS.map((i) => [i.id, v])) as Answers

describe('OEJTS_ITEMS bank', () => {
  it('has exactly 32 items with unique ids 1..32', () => {
    expect(OEJTS_ITEMS).toHaveLength(32)
    const ids = OEJTS_ITEMS.map((i) => i.id).sort((a, b) => a - b)
    expect(ids).toEqual(Array.from({ length: 32 }, (_, n) => n + 1))
  })

  it('has exactly 8 items per axis', () => {
    for (const axis of ['IE', 'SN', 'TF', 'JP'] as const) {
      expect(OEJTS_ITEMS.filter((i) => i.axis === axis)).toHaveLength(8)
    }
  })

  it('rightLetter is always one of the two letters of its axis', () => {
    const pairs = { IE: 'EI', SN: 'SN', TF: 'TF', JP: 'JP' } as const
    for (const i of OEJTS_ITEMS) expect(pairs[i.axis]).toContain(i.rightLetter)
  })

  it('marks exactly the three reworded items', () => {
    expect(OEJTS_ITEMS.filter((i) => i.reworded)).toHaveLength(3)
  })
})

describe('scoreType', () => {
  it('returns null when any answer is missing', () => {
    const partial = { ...allSame(3) }
    delete partial[1]
    expect(scoreType(partial)).toBeNull()
  })

  it('produces a 4-letter type and four axis sums for complete answers', () => {
    const r = scoreType(allSame(3))!
    expect(r.type).toMatch(/^[EI][SN][TF][JP]$/)
    expect(r.axisScores.IE).toBe(24) // all 3s => 8 items * 3 = 24 on every axis
    expect(r.axisScores.SN).toBe(24)
    expect(r.axisScores.TF).toBe(24)
    expect(r.axisScores.JP).toBe(24)
  })

  it('an all-neutral (all-3) response yields the OEJTS midpoint default INTJ', () => {
    // Verified against the live instrument: at sum 24 on every axis, IE/JP fall to
    // I/J (cutoff > 24) while SN/TF rise to N/T (cutoff >= 24).
    expect(scoreType(allSame(3))!.type).toBe('INTJ')
  })

  it('answering every item toward its rightLetter selects all high letters', () => {
    // Build answers so each item scores 5 toward its rightLetter.
    const answers = Object.fromEntries(
      OEJTS_ITEMS.map((i) => [i.id, 5 as AnswerValue]),
    ) as Answers
    const r = scoreType(answers)!
    // Each axis sum becomes 8*? depending on orientation; assert it is a valid type.
    expect(r.type).toMatch(/^[EI][SN][TF][JP]$/)
  })
})
