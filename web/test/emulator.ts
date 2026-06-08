import { initializeTestEnvironment, RulesTestEnvironment } from '@firebase/rules-unit-testing'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

let testEnv: RulesTestEnvironment | null = null

// Vitest runs from the web/ project root, where firestore.rules lives. (Reading via
// new URL(import.meta.url) breaks under Vitest on Windows, where import.meta.url is
// not a file: URL — so resolve against cwd instead.)
export async function getTestEnv(): Promise<RulesTestEnvironment> {
  if (!testEnv) {
    testEnv = await initializeTestEnvironment({
      projectId: 'demo-lya',
      firestore: {
        host: 'localhost',
        port: 8080,
        rules: readFileSync(resolve(process.cwd(), 'firestore.rules'), 'utf8'),
      },
    })
  }
  return testEnv
}
