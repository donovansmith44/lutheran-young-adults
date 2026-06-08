import { describe, it, expect } from 'vitest'
import { computeT } from './timer'

const MIN = 60_000

describe('computeT', () => {
  const start = 1_000_000

  it('is N at the instant of session start', () => {
    expect(computeT(start, 30, start)).toBe(30)
  })

  it('counts down whole minutes remaining (ceil)', () => {
    expect(computeT(start, 30, start + 10 * MIN)).toBe(20)
    expect(computeT(start, 30, start + 10.5 * MIN)).toBe(20) // 19.5 -> ceil 20
  })

  it('never goes below 0', () => {
    expect(computeT(start, 30, start + 45 * MIN)).toBe(0)
  })

  it('honors an adjustable N', () => {
    expect(computeT(start, 10, start + 3 * MIN)).toBe(7)
  })
})
