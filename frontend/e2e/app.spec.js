import { test, expect } from '@playwright/test'

test.describe('PytestDeck E2E Frontend Suite', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('should render header branding and suite controls', async ({ page }) => {
    await expect(page.locator('.brand h1')).toHaveText('PytestDeck')
    await expect(page.locator('.path-input')).toHaveValue('/Users/xuandi/repo/PytestDeck')
    
    const select = page.locator('.suite-select')
    await expect(select).toBeVisible()
    await expect(select.locator('option')).toHaveCount(3)
  })

  test('should discover test tree and allow node selection', async ({ page }) => {
    await expect(page.locator('.deck-sidebar')).toBeVisible()
    await page.waitForSelector('.tree-container', { timeout: 10000 })
    
    const treeRows = page.locator('.node-row')
    await expect(treeRows.first()).toBeVisible()
    
    // Toggle first expandable node or select item
    const firstRow = treeRows.first()
    await firstRow.click()
  })

  test('should run tests and update execution metrics & history', async ({ page }) => {
    await page.waitForSelector('.tree-container', { timeout: 10000 })
    
    // Click Run Selected button
    const runBtn = page.locator('.btn-primary')
    await expect(runBtn).toBeVisible()
    await runBtn.click()

    // Verify terminal output tab displays process status log
    const terminal = page.locator('.terminal-wrapper')
    await expect(terminal).toBeVisible()

    // Wait for execution completion (Run button returns to non-running state)
    await expect(runBtn).toBeVisible({ timeout: 15000 })

    // Switch to Metrics & Summary tab
    await page.click('button:has-text("Metrics & Summary")')
    await expect(page.locator('.card-exit')).toBeVisible()
    await expect(page.locator('.card-exit .value')).toHaveText('0')

    // Switch to Execution History tab
    await page.click('button:has-text("Execution History")')
    await expect(page.locator('.history-item')).toHaveCount(1)
    await expect(page.locator('.history-status')).toHaveText('PASSED')
  })
})
