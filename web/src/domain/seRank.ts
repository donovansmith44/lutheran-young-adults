import type { AxisScores } from './types'

const SE_RANK: Record<string, number> = {
  ESTP: 1, ESFP: 1,
  ISTP: 2, ISFP: 2,
  ENFJ: 3, ENTJ: 3,
  INFJ: 4, INTJ: 4,
  ISTJ: 5, ISFJ: 5,
  ESTJ: 6, ESFJ: 6,
  INFP: 7, INTP: 7,
  ENFP: 8, ENTP: 8,
}

export function seRank(type: string): number {
  const r = SE_RANK[type]
  if (r === undefined) throw new Error(`Unknown type: ${type}`)
  return r
}

/**
 * Tiebreak only. Strong extraverted sensing = more Extraverted + more Sensing.
 * axisScores are oriented toward the high-letters E and N (see oejts.ts), so
 * E-ness = IE - 24 and S-ness = 24 - SN.
 */
export function seStrength(axisScores: AxisScores): number {
  const eNess = axisScores.IE - 24
  const sNess = 24 - axisScores.SN
  return eNess + sNess
}
