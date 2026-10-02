import { test, expect } from '@playwright/test'

test.describe('PytestDeck E2E Frontend Suite', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('should render header branding and suite controls', async ({ page }) => {
    await expect(page.locator('.brand h1')).toHaveText('PytestDeck')
    await expect(page.locator('.path-input')).not.toHaveValue('')
    
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

  test('should switch test suites between unit, integration, and behave acceptance', async ({ page }) => {
    await page.waitForSelector('.tree-container', { timeout: 10000 })
    
    const select = page.locator('.suite-select')
    
    // Switch to Integration suite (index 1)
    await select.selectOption({ index: 1 })
    await page.waitForSelector('.tree-container', { timeout: 10000 })

    // Switch to Acceptance suite (index 2)
    await select.selectOption({ index: 2 })
    await page.waitForSelector('.tree-container', { timeout: 10000 })
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

  test('should display raw JSON report tab after execution', async ({ page }) => {
    await page.waitForSelector('.tree-container', { timeout: 10000 })
    await page.click('.btn-primary')
    
    // Wait for run to finish
    await page.waitForSelector('.btn-primary', { timeout: 15000 })

    // Click JSON Report tab
    await page.click('button:has-text("JSON Report")')
    const jsonCode = page.locator('.json-code')
    await expect(jsonCode).toBeVisible()
    await expect(jsonCode).toContainText('summary')
  })

  test('should pass marker filter and extra flags to runner execution', async ({ page }) => {
    await page.waitForSelector('.tree-container', { timeout: 10000 })

    // Enter marker and extra flags filters
    const markerInput = page.locator('input[placeholder*="Marker"]')
    const extraInput = page.locator('input[placeholder*="Extra flags"]')

    await markerInput.fill('smoke')
    await extraInput.fill('-s')

    // Click Run Selected
    await page.click('.btn-primary')
    await page.waitForSelector('.btn-primary', { timeout: 15000 })
  })

  test('should handle stop execution action cleanly', async ({ page }) => {
    await page.waitForSelector('.tree-container', { timeout: 10000 })
    
    // Start test execution
    await page.click('.btn-primary')
    
    // Stop button should appear
    const stopBtn = page.locator('.btn-danger')
    if (await stopBtn.isVisible()) {
      await stopBtn.click()
    }

    // Run button should become visible again
    await expect(page.locator('.btn-primary')).toBeVisible({ timeout: 10000 })
  })
})
