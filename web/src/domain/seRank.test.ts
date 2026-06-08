import { describe, it, expect } from 'vitest'
import { seRank, seStrength } from './seRank'
import type { AxisScores } from './types'

describe('seRank', () => {
  it('ranks dominant-Se types highest (1) and demon-Se types lowest (8)', () => {
    expect(seRank('ESTP')).toBe(1)
    expect(seRank('ESFP')).toBe(1)
    expect(seRank('ENFP')).toBe(8)
    expect(seRank('ENTP')).toBe(8)
  })

  it('covers all 16 types with ranks 1..8 (two types each)', () => {
    const types = ['ESTP','ESFP','ISTP','ISFP','ENFJ','ENTJ','INFJ','INTJ','ISTJ','ISFJ','ESTJ','ESFJ','INFP','INTP','ENFP','ENTP']
    const counts: Record<number, number> = {}
    for (const t of types) counts[seRank(t)] = (counts[seRank(t)] ?? 0) + 1
    expect(Object.keys(counts).map(Number).sort((a,b)=>a-b)).toEqual([1,2,3,4,5,6,7,8])
    expect(Object.values(counts).every((c) => c === 2)).toBe(true)
  })
})

describe('seStrength', () => {
  const mk = (IE: number, SN: number): AxisScores => ({ IE, SN, TF: 24, JP: 24 })
  it('is higher for more extraverted + more sensing (E high IE, S low SN)', () => {
    // high=E means larger IE sum is more E; low SN sum is more S
    expect(seStrength(mk(40, 8))).toBeGreaterThan(seStrength(mk(24, 24)))
    expect(seStrength(mk(8, 40))).toBeLessThan(seStrength(mk(24, 24)))
  })
})
