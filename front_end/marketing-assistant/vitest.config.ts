// =============================================================================
// Vitest Configuration — Angular Unit Tests
// =============================================================================
//
// This configures Vitest to run Angular component and service tests.
// It replaces Karma/Jasmine — there is no karma.conf.js.
//
// Key settings:
//   - environment: 'jsdom'      Provides a browser-like DOM in Node.js so
//                                Angular components render without a real browser.
//   - include: ['src/**/*.spec.ts']  Standard Angular test file pattern.
//   - reporters: ['default', 'junit']  Human-readable output + machine-readable
//                                      JUnit XML for CI artifacts.
//   - testTimeout: 10000         10 seconds max per test (generous for cold starts).
//
// Uses JSDOM (installed via devDependencies in package.json).
// Uses uuid for ID generation in model classes.

import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
  test: {
    // Provide a browser-like DOM — Angular components need document, window, etc.
    environment: 'jsdom',

    // Include all .spec.ts files under src/ (standard Angular convention).
    include: ['src/**/*.spec.ts'],

    // Reporters:
    //   'default' — human-readable output in the terminal.
    //   'junit'   — machine-readable XML for GitHub Actions test summary.
    reporters: ['default', 'junit'],

    // 10 seconds per test. Cold module resolution in CI can be slow on the
    // first test; 10s gives enough headroom without hiding real hangs.
    testTimeout: 10000,
  },

  // Tell Vitest how to resolve bare imports the same way Angular's TypeScript
  // compiler does (paths from tsconfig.json).
  resolve: {
    alias: {
      '@app': path.resolve(__dirname, 'src/app'),
      '@environments': path.resolve(__dirname, 'src/environments'),
    },
  },
});
