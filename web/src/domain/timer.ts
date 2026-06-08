/** Minutes remaining until reveal: T = max(0, ceil(N - minutesSinceStart)). */
export function computeT(startedAtMs: number, timerMinutes: number, nowMs: number): number {
  const elapsedMin = (nowMs - startedAtMs) / 60_000
  return Math.max(0, Math.ceil(timerMinutes - elapsedMin))
}
