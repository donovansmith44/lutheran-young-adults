export type Axis = 'IE' | 'SN' | 'TF' | 'JP'
export type Letter = 'E' | 'I' | 'S' | 'N' | 'T' | 'F' | 'J' | 'P'
export type Group = 'scavenger' | 'games'
export type AnswerValue = 1 | 2 | 3 | 4 | 5
export type Answers = Record<number, AnswerValue> // itemId -> value (1 = left pole, 5 = right pole)

/** Per-axis decision rule, calibrated against the live OEJTS instrument.
 *  `high` is the letter an axis selects when its high-oriented 8-item sum (range
 *  8–40, midpoint 24) clears the midpoint; `low` is selected otherwise. The cutoff
 *  is asymmetric across axes (verified by oejts.verify.test.ts against the source):
 *    - IE/JP select `high` only when sum > 24 (a tie of 24 → low: I / J)
 *    - SN/TF select `high` when sum >= 24 (a tie of 24 → high: N / T)
 *  so an all-neutral response yields the OEJTS default type INTJ. */
export interface AxisRule {
  high: Letter
  low: Letter
  strict: boolean // true: high iff sum > 24; false: high iff sum >= 24
}

export const AXIS_LETTERS: Record<Axis, AxisRule> = {
  IE: { high: 'E', low: 'I', strict: true },
  SN: { high: 'N', low: 'S', strict: false },
  TF: { high: 'T', low: 'F', strict: false },
  JP: { high: 'P', low: 'J', strict: true },
}

export interface OejtsItem {
  id: number            // stable internal id, 1..32
  axis: Axis
  left: string          // statement shown at value 1
  right: string         // statement shown at value 5
  rightLetter: Letter   // the axis letter that value 5 points toward
  reworded: boolean     // true if doctrinally reworded from the OEJTS original
}

export interface AxisScores {
  IE: number
  SN: number
  TF: number
  JP: number
}

/** Minimal shape the grouping logic needs (decoupled from Firestore docs). */
export interface TakerForGrouping {
  id: string
  completed: boolean
  seRank?: number
  seStrength?: number
  group?: Group | null
  groupOverride?: boolean
}
