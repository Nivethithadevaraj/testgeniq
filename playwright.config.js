const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './playwright',

  reporter: [
    ['list'],
    ['json', { outputFile: 'artifacts/playwright.json' }]
  ],

  use: {
    baseURL: 'http://127.0.0.1:8000',
    extraHTTPHeaders: {
      'Content-Type': 'application/json'
    }
  },

  timeout: 30000,

  expect: {
    timeout: 5000
  }
});