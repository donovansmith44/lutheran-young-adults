import type { Group, TakerForGrouping } from './types'

export interface GroupCounts { scavenger: number; games: number }

export function assignLatecomer(counts: GroupCounts): Group {
  return counts.scavenger <= counts.games ? 'scavenger' : 'games'
}

/** Computes the frozen group for every taker. Returns id -> group. */
export function freezeGroups(takers: TakerForGrouping[]): Record<string, Group> {
  const result: Record<string, Group> = {}
  const counts: GroupCounts = { scavenger: 0, games: 0 }

  // 1) overrides keep their group and count toward balance
  for (const o of takers) {
    if (o.groupOverride && o.group) {
      result[o.id] = o.group
      counts[o.group]++
    }
  }

  // 2) completed, non-overridden: Se-rank split, top half -> scavenger
  const completed = takers
    .filter((t) => t.completed && !t.groupOverride)
    .sort(
      (a, b) =>
        (a.seRank ?? 99) - (b.seRank ?? 99) ||
        (b.seStrength ?? 0) - (a.seStrength ?? 0) ||
        (a.id < b.id ? -1 : 1),
    )
  const scavengerTarget = Math.ceil(completed.length / 2)
  completed.forEach((t, i) => {
    const g: Group = i < scavengerTarget ? 'scavenger' : 'games'
    result[t.id] = g
    counts[g]++
  })

  // 3) still-testing, non-overridden: fill the smaller group
  const incomplete = takers
    .filter((t) => !t.completed && !t.groupOverride)
    .sort((a, b) => (a.id < b.id ? -1 : 1))
  for (const t of incomplete) {
    const g = assignLatecomer(counts)
    result[t.id] = g
    counts[g]++
  }

  return result
}
