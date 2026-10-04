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
    await page.waitForSelector('.tree-container', { timeout: 60000 })
    
    const treeRows = page.locator('.node-row')
    await expect(treeRows.first()).toBeVisible()
    
    // Toggle first expandable node or select item
    const firstRow = treeRows.first()
    await firstRow.click()
  })

  test('should switch test suites between unit, integration, and behave acceptance', async ({ page }) => {
    await page.waitForSelector('.tree-container', { timeout: 60000 })
    
    const select = page.locator('.suite-select')
    
    // Switch to Integration suite (index 1)
    await select.selectOption({ index: 1 })
    await page.waitForSelector('.tree-container', { timeout: 60000 })

    // Switch to Acceptance suite (index 2)
    await select.selectOption({ index: 2 })
    await page.waitForSelector('.tree-container', { timeout: 60000 })
  })

  test('should run tests and update execution metrics & history', async ({ page }) => {
    await page.waitForSelector('.tree-container', { timeout: 60000 })
    
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
    await expect(page.locator('.card-exit .value')).not.toBeEmpty()

    // Switch to Execution History tab
    await page.click('button:has-text("Execution History")')
    await expect(page.locator('.history-item')).toHaveCount(1)
    await expect(page.locator('.history-status')).toBeVisible()
  })

  test('should display raw JSON report tab after execution', async ({ page }) => {
    await page.waitForSelector('.tree-container', { timeout: 60000 })
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
    await page.waitForSelector('.tree-container', { timeout: 60000 })

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
    await page.waitForSelector('.tree-container', { timeout: 60000 })
    
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

  test('should display Detail Info tab when a single test method is selected in Integration suite', async ({ page }) => {
    await page.waitForSelector('.tree-container', { timeout: 60000 })

    // Switch to Integration suite (index 1)
    const select = page.locator('.suite-select')
    await select.selectOption({ index: 1 })
    await page.waitForSelector('.tree-container', { timeout: 60000 })

    // Detail tab should not be visible before selecting a test
    await expect(page.locator('.tab-btn-detail')).not.toBeVisible()

    // Find and click the first test function row in the tree
    const funcRow = page.locator('.node-row:has(.type-badge.function)').first()
    await expect(funcRow).toBeVisible({ timeout: 15000 })
    await funcRow.click()

    // The Detail Info tab should appear and become active
    const detailTabBtn = page.locator('.tab-btn-detail')
    await expect(detailTabBtn).toBeVisible()
    await expect(detailTabBtn).toHaveClass(/active/)

    // Detail Info tab pane should display test information and docstring section
    await expect(page.locator('.detail-pane')).toBeVisible()
    await expect(page.locator('.detail-title')).toBeVisible()
    await expect(page.locator('.docstring-card')).toBeVisible()
  })

  test('should display Detail Info tab when a single scenario is selected in Behave acceptance suite', async ({ page }) => {
    await page.waitForSelector('.tree-container', { timeout: 60000 })

    // Switch to Acceptance suite (index 2)
    const select = page.locator('.suite-select')
    await select.selectOption({ index: 2 })
    await page.waitForSelector('.tree-container', { timeout: 60000 })

    // Detail tab should not be visible initially
    await expect(page.locator('.tab-btn-detail')).not.toBeVisible()

    // Find and click the first scenario function row
    const scenarioRow = page.locator('.node-row:has(.type-badge.function)').first()
    await expect(scenarioRow).toBeVisible({ timeout: 15000 })
    await scenarioRow.click()

    // The Detail Info tab should appear and become active
    const detailTabBtn = page.locator('.tab-btn-detail')
    await expect(detailTabBtn).toBeVisible()
    await expect(detailTabBtn).toHaveClass(/active/)

    // Verify detail pane displays scenario badge, title, and steps or docstring
    await expect(page.locator('.detail-pane')).toBeVisible()
    await expect(page.locator('.badge-scenario')).toBeVisible()
    await expect(page.locator('.detail-title')).toBeVisible()
    await expect(page.locator('.docstring-card')).toBeVisible()

    // Unselect and verify Detail tab disappears
    await scenarioRow.click()
    await expect(page.locator('.tab-btn-detail')).not.toBeVisible()
  })

  test('should display latest run output card and execute single test method with -s', async ({ page }) => {
    await page.waitForSelector('.tree-container', { timeout: 60000 })

    // Switch to Integration suite (index 1)
    const select = page.locator('.suite-select')
    await select.selectOption({ index: 1 })
    await page.waitForSelector('.tree-container', { timeout: 60000 })

    // Select a test method
    const funcRow = page.locator('.node-row:has(.type-badge.function)').first()
    await expect(funcRow).toBeVisible({ timeout: 15000 })
    await funcRow.click()

    // Verify Latest Run Output card is displayed
    const runOutputCard = page.locator('.run-output-card')
    await expect(runOutputCard).toBeVisible()

    // Click Run Test (-s) button
    const runMethodBtn = page.locator('.btn-run-method')
    await expect(runMethodBtn).toBeVisible()
    await runMethodBtn.click()

    // Wait for method execution to complete
    await expect(page.locator('.btn-run-method')).toBeEnabled({ timeout: 15000 })

    // Verify status badge appears
    await expect(page.locator('.run-status-badge')).toBeVisible()
  })
})



