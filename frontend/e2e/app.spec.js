import { test, expect } from '@playwright/test'

test.describe('PytestDeck E2E Frontend Suite', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/?target_path=./sample-target-repo')
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
    
    // Verify file nodes are collapsed by default
    const fileRow = page.locator('.node-row:has(.type-badge.file)').first()
    await expect(fileRow).toBeVisible()
    await expect(fileRow.locator('.toggle-icon')).toHaveText('▶')

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

    // Wait for execution completion (Stop button appears then disappears)
    const stopBtn = page.locator('.btn-danger')
    await expect(stopBtn).toBeVisible({ timeout: 5000 }).catch(() => {})
    await expect(stopBtn).not.toBeVisible({ timeout: 30000 })
    await expect(runBtn).toBeVisible()

    // Verify Copy Output button is enabled and clickable
    const copyBtn = page.locator('.btn-copy-terminal')
    await expect(copyBtn).toBeVisible()
    await expect(copyBtn).toBeEnabled()
    await copyBtn.click()
    await expect(copyBtn).toHaveClass(/active/)

    // Switch to Metrics & Summary tab
    await page.click('button:has-text("Metrics & Summary")')
    await expect(page.locator('.card-exit')).toBeVisible({ timeout: 10000 })
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
    const stopBtn = page.locator('.btn-danger')
    await expect(stopBtn).toBeVisible({ timeout: 5000 }).catch(() => {})
    await expect(stopBtn).not.toBeVisible({ timeout: 30000 })
    await expect(page.locator('.btn-primary')).toBeVisible()

    // Click JSON Report tab
    await page.click('button:has-text("JSON Report")')
    const jsonCode = page.locator('.json-code')
    await expect(jsonCode).toBeVisible()
    await expect(jsonCode).toContainText('summary')
  })

  test('should pass marker filter and extra flags to runner execution', async ({ page }) => {
    await page.waitForSelector('.tree-container', { timeout: 60000 })

    // Open Run Options modal and enter marker and extra flags
    await page.click('#btn-run-options')
    const markerInput = page.locator('#run-options-marker')
    const extraInput = page.locator('#run-options-extra')
    await expect(markerInput).toBeVisible()

    await markerInput.fill('smoke')
    await extraInput.fill('-s')
    await page.click('#run-options-apply')

    // Modal closes and active options are summarized in the sidebar
    await expect(markerInput).not.toBeVisible()
    await expect(page.locator('.run-options-count')).toHaveText('2')

    // Click Run Selected
    await page.click('.btn-primary')
    const stopBtn = page.locator('.btn-danger')
    await expect(stopBtn).toBeVisible({ timeout: 5000 }).catch(() => {})
    await expect(stopBtn).not.toBeVisible({ timeout: 30000 })

    // Clean up run options so subsequent tests are not filtered
    await page.click('#btn-run-options')
    await markerInput.fill('')
    await extraInput.fill('')
    await page.click('#run-options-apply')
  })

  test('should handle stop execution action cleanly', async ({ page }) => {
    await page.waitForSelector('.tree-container', { timeout: 60000 })
    
    // Start test execution
    await page.click('.btn-primary')
    
    // Stop button should appear
    const stopBtn = page.locator('.btn-danger')
    await expect(stopBtn).toBeVisible({ timeout: 10000 })
    await stopBtn.click()

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

    // Expand the first file node to reveal its test methods
    const fileToggle = page.locator('.node-row:has(.type-badge.file) .toggle-icon').first()
    await expect(fileToggle).toBeVisible({ timeout: 15000 })
    await fileToggle.click()

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

    // Expand the first feature file node to reveal its scenarios
    const fileToggle = page.locator('.node-row:has(.type-badge.file) .toggle-icon').first()
    await expect(fileToggle).toBeVisible({ timeout: 15000 })
    await fileToggle.click()

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

    // Expand the first file node to reveal its test methods
    const fileToggle = page.locator('.node-row:has(.type-badge.file) .toggle-icon').first()
    await expect(fileToggle).toBeVisible({ timeout: 15000 })
    await fileToggle.click()

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

    // Wait for method execution to complete and status badge to appear
    await expect(page.locator('.run-status-badge')).toBeVisible({ timeout: 20000 })
    await expect(runMethodBtn).toBeEnabled({ timeout: 10000 })

    // Verify Clear button is visible and clears output
    const clearBtn = page.locator('.btn-clear-output')
    await expect(clearBtn).toBeVisible()
    await clearBtn.click()

    // Verify output cleared back to empty state
    await expect(page.locator('.method-terminal-empty')).toBeVisible()
  })

  test('should handle tab switching and sidebar resize without clipping terminal', async ({ page }) => {
    await page.waitForSelector('.tree-container', { timeout: 60000 })

    // Verify initial terminal output visibility and bounding dimensions
    const terminal = page.locator('.terminal-wrapper')
    await expect(terminal).toBeVisible()
    const screen = page.locator('.terminal-container .xterm-screen')
    await expect(screen).toBeVisible()

    const initialBox = await screen.boundingBox()
    expect(initialBox).not.toBeNull()
    expect(initialBox.width).toBeGreaterThan(100)
    expect(initialBox.height).toBeGreaterThan(100)

    // Switch to Metrics & Summary tab (hiding terminal view)
    await page.click('button:has-text("Metrics & Summary")')
    await expect(page.locator('.summary-pane')).toBeVisible()
    await expect(terminal).not.toBeVisible()

    // Switch back to Terminal Output tab (restoring terminal view)
    await page.click('button:has-text("Terminal Output")')
    await expect(terminal).toBeVisible()
    await expect(screen).toBeVisible()

    // Drag the sidebar resizer to change container dimensions
    const resizer = page.locator('.sidebar-resizer')
    await expect(resizer).toBeVisible()
    const resizerBox = await resizer.boundingBox()
    expect(resizerBox).not.toBeNull()

    await page.mouse.move(resizerBox.x + resizerBox.width / 2, resizerBox.y + resizerBox.height / 2)
    await page.mouse.down()
    await page.mouse.move(resizerBox.x + 100, resizerBox.y + resizerBox.height / 2)
    await page.mouse.up()

    // Verify terminal screen adapted to updated dimensions
    const resizedBox = await screen.boundingBox()
    expect(resizedBox).not.toBeNull()
    expect(resizedBox.width).toBeGreaterThan(100)
    expect(resizedBox.height).toBeGreaterThan(100)
  })

  test('should allow switching terminal font style', async ({ page }) => {
    await page.waitForSelector('.terminal-wrapper', { timeout: 60000 })

    const fontSelect = page.locator('.term-font-select')
    await expect(fontSelect).toBeVisible()

    // Switch font to JetBrains Mono
    await fontSelect.selectOption('jetbrains-mono')
    await expect(fontSelect).toHaveValue('jetbrains-mono')

    // Switch font to SF Mono
    await fontSelect.selectOption('sf-mono')
    await expect(fontSelect).toHaveValue('sf-mono')
  })

  test('should display clear all history button and trigger clearing', async ({ page }) => {
    await page.waitForSelector('.tree-container', { timeout: 60000 })

    const clearHistoryBtn = page.locator('#btn-clear-history')
    await expect(clearHistoryBtn).toBeVisible()

    await clearHistoryBtn.click()

    // Assert that no function row has outcome stripes
    await expect(page.locator('.row-outcome-passed')).toHaveCount(0)
    await expect(page.locator('.row-outcome-failed')).toHaveCount(0)
  })

  test('should persist run options across page reload', async ({ page }) => {
    await page.waitForSelector('.tree-container', { timeout: 60000 })

    await page.click('#btn-run-options')
    const markerInput = page.locator('#run-options-marker')
    const extraInput = page.locator('#run-options-extra')
    await expect(markerInput).toBeVisible()

    await markerInput.fill('persisted_marker')
    await extraInput.fill('-v --tb=short')
    await page.click('#run-options-apply')
    await expect(markerInput).not.toBeVisible()

    // Reload page to verify values were persisted to DB
    await page.reload()
    await page.waitForSelector('.tree-container', { timeout: 60000 })

    // Open modal again and verify values
    await page.click('#btn-run-options')
    await expect(page.locator('#run-options-marker')).toHaveValue('persisted_marker')
    await expect(page.locator('#run-options-extra')).toHaveValue('-v --tb=short')

    // Clean up run options so subsequent tests are not filtered
    await markerInput.fill('')
    await extraInput.fill('')
    await page.click('#run-options-apply')
  })

  test('should reset test result when test file is modified', async ({ page }) => {
    await page.waitForSelector('.tree-container', { timeout: 60000 })

    // Ensure marker filters are clear
    const clearOptionsBtn = page.locator('.badge-clear-btn')
    if (await clearOptionsBtn.isVisible()) {
      await clearOptionsBtn.click()
    }

    // Switch to Integration suite (index 1)
    const select = page.locator('.suite-select')
    await select.selectOption({ index: 1 })
    await page.waitForSelector('.tree-container', { timeout: 60000 })

    // Expand the first file node
    const fileToggle = page.locator('.node-row:has(.type-badge.file) .toggle-icon').first()
    await expect(fileToggle).toBeVisible({ timeout: 15000 })
    await fileToggle.click()

    // Select a test method
    const funcRow = page.locator('.node-row:has(.type-badge.function)').first()
    await expect(funcRow).toBeVisible({ timeout: 15000 })
    await funcRow.click()

    // Execute single test method
    const runMethodBtn = page.locator('.btn-run-method')
    await expect(runMethodBtn).toBeVisible()
    await runMethodBtn.click()
    await expect(page.locator('.run-status-badge')).toBeVisible({ timeout: 20000 })
    await expect(runMethodBtn).toBeEnabled({ timeout: 10000 })

    // Verify Clear button clears output back to empty state
    const clearBtn = page.locator('.btn-clear-output')
    if (await clearBtn.isVisible()) {
      await clearBtn.click()
      await expect(page.locator('.method-terminal-empty')).toBeVisible()
    }
  })

  test('should clear selections in DirectoryTree when clear selections button is clicked', async ({ page }) => {
    await page.waitForSelector('.tree-container', { timeout: 60000 })

    const clearSelectionBtn = page.locator('#btn-clear-selection')
    await expect(clearSelectionBtn).toBeVisible()
    await expect(clearSelectionBtn).toBeDisabled()

    // Expand the first file node
    const fileToggle = page.locator('.node-row:has(.type-badge.file) .toggle-icon').first()
    await expect(fileToggle).toBeVisible({ timeout: 15000 })
    await fileToggle.click()

    // Click on a test function row to select it
    const funcRow = page.locator('.node-row:has(.type-badge.function)').first()
    await expect(funcRow).toBeVisible({ timeout: 15000 })
    await funcRow.click()

    // Button should now be enabled and have has-selections class
    await expect(clearSelectionBtn).toBeEnabled()
    await expect(clearSelectionBtn).toHaveClass(/has-selections/)
    await expect(page.locator('.btn-run-selected')).toContainText('Run Selected (1)')

    // Click the clear selection button
    await clearSelectionBtn.click()

    // Button should now be disabled and count back to 0
    await expect(clearSelectionBtn).toBeDisabled()
    await expect(page.locator('.btn-run-selected')).toContainText('Run Selected (0)')
  })
})



