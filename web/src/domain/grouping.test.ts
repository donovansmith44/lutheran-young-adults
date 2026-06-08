import { describe, it, expect } from 'vitest'
import { freezeGroups, assignLatecomer } from './grouping'
import type { TakerForGrouping } from './types'

const t = (o: Partial<TakerForGrouping> & { id: string }): TakerForGrouping => ({
  completed: true, seRank: 4, seStrength: 0, group: null, groupOverride: false, ...o,
})

describe('freezeGroups', () => {
  it('puts the top half (by Se rank) of completed takers in scavenger; ceil on odd', () => {
    const takers = [
      t({ id: 'a', seRank: 1 }),
      t({ id: 'b', seRank: 2 }),
      t({ id: 'c', seRank: 7 }),
    ]
    const g = freezeGroups(takers)
    expect(g.a).toBe('scavenger')
    expect(g.b).toBe('scavenger') // ceil(3/2)=2 -> top two
    expect(g.c).toBe('games')
  })

  it('breaks Se-rank ties by higher seStrength, then id', () => {
    const takers = [
      t({ id: 'low', seRank: 3, seStrength: 1 }),
      t({ id: 'high', seRank: 3, seStrength: 9 }),
    ]
    const g = freezeGroups(takers)
    expect(g.high).toBe('scavenger')
    expect(g.low).toBe('games')
  })

  it('assigns still-testing takers to the smaller group (tie -> scavenger)', () => {
    const takers = [
      t({ id: 'c1', seRank: 1 }),                  // scavenger
      t({ id: 'c2', seRank: 8 }),                  // games
      t({ id: 'x', completed: false }),            // tie 1-1 -> scavenger
      t({ id: 'y', completed: false }),            // now 2-1 -> games
    ]
    const g = freezeGroups(takers)
    expect(g.x).toBe('scavenger')
    expect(g.y).toBe('games')
  })

  it('keeps overridden takers in their group and does not move them', () => {
    const takers = [
      t({ id: 'pinned', seRank: 1, group: 'games', groupOverride: true }),
      t({ id: 'a', seRank: 2 }),
      t({ id: 'b', seRank: 3 }),
    ]
    const g = freezeGroups(takers)
    expect(g.pinned).toBe('games')
  })
})

describe('assignLatecomer', () => {
  it('returns the smaller group, tie -> scavenger', () => {
    expect(assignLatecomer({ scavenger: 3, games: 5 })).toBe('scavenger')
    expect(assignLatecomer({ scavenger: 5, games: 3 })).toBe('games')
    expect(assignLatecomer({ scavenger: 4, games: 4 })).toBe('scavenger')
  })
})
