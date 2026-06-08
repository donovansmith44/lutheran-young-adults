import { AXIS_LETTERS } from './types'
import type { Answers, AxisScores, OejtsItem, Letter } from './types'

// The 32 items mirror the live Open Extended Jungian Type Scales (OEJTS) instrument
// 1:1 — `id N` corresponds to the source's question N. `value 1` = `left` pole,
// `value 5` = `right` pole; `rightLetter` is the axis letter the right pole points
// toward. Every item's `axis` and `rightLetter`, and the per-axis cutoff rule in
// AXIS_LETTERS, were reverse-engineered from and verified against the live scorer
// (see oejts.verify.test.ts). Items 2, 22, 26 are doctrinally reworded (spec §7,
// user-approved); each rewording preserves the original pole orientation, so scoring
// is identical to the source.
export const OEJTS_ITEMS: OejtsItem[] = [
  { id: 1, axis: 'JP', left: 'makes lists', right: 'relies on memory', rightLetter: 'P', reworded: false },
  { id: 2, axis: 'TF', left: 'questions new claims until they’re proven', right: 'readily embraces new ideas', rightLetter: 'F', reworded: true },
  { id: 3, axis: 'IE', left: 'bored by time alone', right: 'needs time alone', rightLetter: 'I', reworded: false },
  { id: 4, axis: 'SN', left: 'accepts things as they are', right: 'unsatisfied with the way things are', rightLetter: 'N', reworded: false },
  { id: 5, axis: 'JP', left: 'keeps a clean room', right: 'just puts stuff wherever', rightLetter: 'P', reworded: false },
  { id: 6, axis: 'TF', left: 'thinks “robotic” is an insult', right: 'strives to have a mechanical mind', rightLetter: 'T', reworded: false },
  { id: 7, axis: 'IE', left: 'energetic', right: 'mellow', rightLetter: 'I', reworded: false },
  { id: 8, axis: 'SN', left: 'prefers to take multiple-choice tests', right: 'prefers essay answers', rightLetter: 'N', reworded: false },
  { id: 9, axis: 'JP', left: 'chaotic', right: 'organized', rightLetter: 'J', reworded: false },
  { id: 10, axis: 'TF', left: 'easily hurt', right: 'thick-skinned', rightLetter: 'T', reworded: false },
  { id: 11, axis: 'IE', left: 'works best in groups', right: 'works best alone', rightLetter: 'I', reworded: false },
  { id: 12, axis: 'SN', left: 'focused on the present', right: 'focused on the future', rightLetter: 'N', reworded: false },
  { id: 13, axis: 'JP', left: 'plans far ahead', right: 'plans at the last minute', rightLetter: 'P', reworded: false },
  { id: 14, axis: 'TF', left: 'wants people’s respect', right: 'wants their love', rightLetter: 'F', reworded: false },
  { id: 15, axis: 'IE', left: 'gets worn out by parties', right: 'gets fired up by parties', rightLetter: 'E', reworded: false },
  { id: 16, axis: 'SN', left: 'fits in', right: 'stands out', rightLetter: 'N', reworded: false },
  { id: 17, axis: 'JP', left: 'keeps options open', right: 'commits', rightLetter: 'J', reworded: false },
  { id: 18, axis: 'TF', left: 'wants to be good at fixing things', right: 'wants to be good at fixing people', rightLetter: 'F', reworded: false },
  { id: 19, axis: 'IE', left: 'talks more', right: 'listens more', rightLetter: 'I', reworded: false },
  { id: 20, axis: 'SN', left: 'when describing an event, will tell people what happened', right: 'when describing an event, will tell people what it meant', rightLetter: 'N', reworded: false },
  { id: 21, axis: 'JP', left: 'gets work done right away', right: 'procrastinates', rightLetter: 'P', reworded: false },
  { id: 22, axis: 'TF', left: 'decides with feelings', right: 'decides with logic', rightLetter: 'T', reworded: true },
  { id: 23, axis: 'IE', left: 'stays at home', right: 'goes out on the town', rightLetter: 'E', reworded: false },
  { id: 24, axis: 'SN', left: 'wants the big picture', right: 'wants the details', rightLetter: 'S', reworded: false },
  { id: 25, axis: 'JP', left: 'improvises', right: 'prepares', rightLetter: 'J', reworded: false },
  { id: 26, axis: 'TF', left: 'weighs choices by logic and consistency', right: 'weighs choices by values and harmony', rightLetter: 'F', reworded: true },
  { id: 27, axis: 'IE', left: 'finds it difficult to yell very loudly', right: 'yelling to others when they are far away comes naturally', rightLetter: 'E', reworded: false },
  { id: 28, axis: 'SN', left: 'theoretical', right: 'empirical', rightLetter: 'S', reworded: false },
  { id: 29, axis: 'JP', left: 'works hard', right: 'plays hard', rightLetter: 'P', reworded: false },
  { id: 30, axis: 'TF', left: 'uncomfortable with emotions', right: 'values emotions', rightLetter: 'F', reworded: false },
  { id: 31, axis: 'IE', left: 'likes to perform in front of other people', right: 'avoids public speaking', rightLetter: 'I', reworded: false },
  { id: 32, axis: 'SN', left: 'likes to know “who?”, “what?”, “when?”', right: 'likes to know “why?”', rightLetter: 'N', reworded: false },
]

const byAxis = (axis: OejtsItem['axis']) => OEJTS_ITEMS.filter((i) => i.axis === axis)

export interface ScoreResult {
  type: string
  axisScores: AxisScores
}

/** Returns null if any of the 32 items is unanswered. */
export function scoreType(answers: Answers): ScoreResult | null {
  if (OEJTS_ITEMS.some((i) => answers[i.id] === undefined)) return null

  const axisScores = {} as AxisScores
  let type = ''
  for (const axis of ['IE', 'SN', 'TF', 'JP'] as const) {
    const { high, low, strict } = AXIS_LETTERS[axis]
    let sum = 0
    for (const item of byAxis(axis)) {
      const v = answers[item.id]
      // orient every item toward the axis high-letter (E / N / T / P)
      sum += item.rightLetter === high ? v : 6 - v
    }
    axisScores[axis] = sum
    const selectHigh = strict ? sum > 24 : sum >= 24
    type += (selectHigh ? high : low) as Letter
  }
  return { type, axisScores }
}
