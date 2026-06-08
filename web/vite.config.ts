/// <reference types="vitest/config" />
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./test/setup.ts'],
    // domain tests need no DOM; emulator tests are opt-in via filename.
    // Run test files sequentially: the emulator-backed data tests share one
    // Firestore emulator, and each file's clearFirestore() in beforeEach would
    // otherwise wipe a concurrently-running file's data mid-test.
    fileParallelism: false,
  },
})
