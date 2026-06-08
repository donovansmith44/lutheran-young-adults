export type Axis = 'IE' | 'SN' | 'TF' | 'JP'
export type Letter = 'E' | 'I' | 'S' | 'N' | 'T' | 'F' | 'J' | 'P'
export type Group = 'scavenger' | 'games'
export type AnswerValue = 1 | 2 | 3 | 4 | 5
export type Answers = Record<number, AnswerValue> // itemId -> value (1 = left pole, 5 = right pole)

/** [lowLetter, highLetter] — "high" is the letter a value of 5 points toward when an
 *  item's rightLetter equals it. Sum > 24 on an axis selects the high letter. */
export const AXIS_LETTERS: Record<Axis, [Letter, Letter]> = {
  IE: ['E', 'I'],
  SN: ['S', 'N'],
  TF: ['T', 'F'],
  JP: ['J', 'P'],
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
