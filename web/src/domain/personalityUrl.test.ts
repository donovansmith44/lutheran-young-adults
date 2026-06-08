import { describe, it, expect } from 'vitest'
import { personalityUrl } from './personalityUrl'

describe('personalityUrl', () => {
  it('builds a lowercase 16personalities link', () => {
    expect(personalityUrl('INTJ')).toBe('https://www.16personalities.com/intj-personality')
    expect(personalityUrl('esfp')).toBe('https://www.16personalities.com/esfp-personality')
  })
})
