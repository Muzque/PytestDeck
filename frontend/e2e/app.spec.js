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
    
    const calcFileRow = page.locator('.node-row:has-text("test_calculator.py")')
    await calcFileRow.locator('.node-checkbox').click()

    // Click Run Selected button
    const runBtn = page.locator('.btn-primary')
    await expect(runBtn).toBeVisible()
    await runBtn.click()

    // Verify terminal output tab displays process status log
    const terminal = page.locator('.terminal-wrapper')
    await expect(terminal).toBeVisible()

    // Wait for execution completion (Stop button appears then disappears)
    const stopBtn = page.locator('.btn-danger')
    await expect(stopBtn).toBeVisible({ timeout: 5000 })
    await expect(calcFileRow).toHaveClass(/row-has-running/)
    await expect(stopBtn).not.toBeVisible({ timeout: 30000 })
    await expect(runBtn).toBeVisible()
    await expect(calcFileRow).toHaveClass(/row-has-passed/)

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
    await expect(page.locator('.history-item .history-duration')).toBeVisible()
    await expect(page.locator('.history-item .history-duration')).toHaveText(/^(<1ms|\d+ms|\d+\.\d{2}s)$/)
  })

  test('should display raw JSON report tab after execution', async ({ page }) => {
    await page.waitForSelector('.tree-container', { timeout: 60000 })
    await page.locator('.node-row:has-text("test_calculator.py") .node-checkbox').click()
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
    const rootDirRow = page.locator('.node-row:has(.type-badge.directory)').first()
    
    // Start test execution
    await page.click('.btn-primary')
    
    // Stop button should appear and tree checkboxes should be locked while running
    const stopBtn = page.locator('.btn-danger')
    await expect(stopBtn).toBeVisible({ timeout: 10000 })
    await expect(rootDirRow).toHaveClass(/row-has-running/)
    await expect(rootDirRow.locator('.node-checkbox')).toBeDisabled()
    await stopBtn.click()

    // Run button should become visible again and running state / checkbox lock cleared
    await expect(page.locator('.btn-primary')).toBeVisible({ timeout: 10000 })
    await expect(rootDirRow).not.toHaveClass(/row-has-running/)
    await expect(rootDirRow.locator('.node-checkbox')).toBeEnabled()
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

    // Wait for and select a test method
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

  test('should display clear all history button in run options with warning and trigger clearing', async ({ page }) => {
    await page.waitForSelector('.tree-container', { timeout: 60000 })

    // Verify clear history button is NOT present in the main toolbar
    await expect(page.locator('.explorer-toolbar #btn-clear-history')).not.toBeVisible()

    // Open Run Options modal
    await page.click('#btn-run-options')
    await expect(page.locator('.ro-card')).toBeVisible()

    // Verify Danger Zone and warning message are visible
    await expect(page.locator('.ro-danger-section')).toBeVisible()
    await expect(page.locator('.ro-danger-warning')).toContainText('Clearing test history permanently removes all stored test outcomes')

    const clearHistoryBtn = page.locator('#btn-clear-history')
    await expect(clearHistoryBtn).toBeVisible()

    await clearHistoryBtn.click()

    // Verify feedback message appears
    await expect(page.locator('.ro-history-cleared-msg')).toBeVisible()

    // Close modal
    await page.click('.ro-close')

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

  test('should append acceptance steps and stream logger output in terminal during behave run', async ({ page }) => {
    await page.waitForSelector('.tree-container', { timeout: 60000 })

    // Switch to Acceptance suite (index 2)
    const select = page.locator('.suite-select')
    await select.selectOption({ index: 2 })
    await page.waitForSelector('.tree-container', { timeout: 60000 })

    // Find streaming_logger.feature node row and select its checkbox
    const fileRow = page.locator('.node-row:has-text("streaming_logger.feature")')
    await expect(fileRow).toBeVisible({ timeout: 15000 })
    await fileRow.locator('.node-checkbox').click()

    // Click Run Selected
    const runBtn = page.locator('.btn-primary')
    await expect(runBtn).toBeVisible()
    await runBtn.click()

    // Wait for execution completion
    const stopBtn = page.locator('.btn-danger')
    await expect(stopBtn).toBeVisible({ timeout: 5000 }).catch(() => {})
    await expect(stopBtn).not.toBeVisible({ timeout: 30000 })
    await expect(runBtn).toBeVisible()

    // Check terminal output contains all sequential steps and live logs
    const terminalText = await page.locator('.terminal-wrapper .xterm-rows').innerText()
    expect(terminalText).toContain('Given a step that initializes calculation logger')
    expect(terminalText).toContain('When a step logs multiple progress messages with delays')
    expect(terminalText).toContain('Then a final step verifies that all previous logs remain visible')
    expect(terminalText).toContain('Starting calculation step 1')
    expect(terminalText).toContain('Processing batch 1')
  })

  test('should show running color on selected DirectoryTree nodes and parents while executing and restore on stop', async ({ page }) => {
    await page.waitForSelector('.tree-container', { timeout: 60000 })

    const rootDirRow = page.locator('.node-row:has(.type-badge.directory)').first()
    const calcFileRow = page.locator('.node-row:has-text("test_calculator.py")')
    const slowFileRow = page.locator('.node-row:has-text("test_slow_and_classes.py")')

    await expect(calcFileRow).toBeVisible()
    await expect(slowFileRow).toBeVisible()

    // 1. Click Run Selected (0) (unselected Run All) and verify all files in active suite enter running state
    await page.locator('.btn-primary').click()
    const stopBtn = page.locator('.btn-danger')
    await expect(stopBtn).toBeVisible({ timeout: 5000 })
    await expect(rootDirRow).toHaveClass(/row-has-running/)
    await expect(slowFileRow).toHaveClass(/row-has-running/)
    await expect(rootDirRow.locator('.rollup-chip.running')).toBeVisible()

    // Simulate browser window regaining focus mid-run; verify running state is NOT overwritten
    await page.evaluate(() => window.dispatchEvent(new Event('focus')))
    await expect(slowFileRow).toHaveClass(/row-has-running/)
    await expect(rootDirRow).toHaveClass(/row-has-running/)

    // Clicking a row while running should NOT toggle selection
    await calcFileRow.click()
    await expect(calcFileRow).not.toHaveClass(/is-selected/)

    await expect(stopBtn).not.toBeVisible({ timeout: 30000 })

    // Both collapsed files now have previous run result colors
    await expect(calcFileRow).toHaveClass(/row-has-passed/)
    await expect(slowFileRow).toHaveClass(/row-has-/)

    // 2. Select ONLY test_slow_and_classes.py and run it
    await slowFileRow.locator('.node-checkbox').click()
    await page.locator('.btn-primary').click()

    // While executing:
    // - Selected collapsed file row shows row-has-running (not previous row-has-passed/failed)
    // - Expanded parent directory row shows row-has-running
    // - Unselected file (test_calculator.py) keeps row-has-passed and is not running
    await expect(stopBtn).toBeVisible({ timeout: 5000 })
    await expect(slowFileRow.locator('.node-checkbox')).toBeDisabled()
    await expect(calcFileRow.locator('.node-checkbox')).toBeDisabled()
    await expect(page.locator('#btn-clear-selection')).toBeDisabled()
    await expect(slowFileRow).toHaveClass(/row-has-running/)
    await expect(slowFileRow).not.toHaveClass(/row-has-passed|row-has-failed/)
    await expect(rootDirRow).toHaveClass(/row-has-running/)
    await expect(calcFileRow).toHaveClass(/row-has-passed/)
    await expect(calcFileRow).not.toHaveClass(/row-has-running/)

    // Expand slowFileRow while running to verify expanded file, class, and function nodes show running color,
    // and that earlier tests transition to passed on the fly while slow tests are still running
    await slowFileRow.locator('.toggle-icon').click()
    await expect(slowFileRow).toHaveClass(/row-has-running/)
    const classRow = page.locator('.node-row:has-text("TestClassWithSlowSetup")')
    const fastFuncRow = page.locator('.node-row:has-text("test_query_fast_one")')
    const slowFuncRow = page.locator('.node-row:has-text("test_long_running_pipeline")')
    await expect(slowFuncRow).toHaveClass(/row-outcome-running/)

    // While test_long_running_pipeline is still running, earlier test_query_fast_one updates to passed on the fly
    await expect(fastFuncRow).toHaveClass(/row-outcome-passed/, { timeout: 5000 })
    await expect(slowFuncRow).toHaveClass(/row-outcome-running/)
    await expect(slowFileRow).toHaveClass(/row-has-running/)

    // Wait for completion and verify running colors are replaced by finished outcomes
    await expect(stopBtn).not.toBeVisible({ timeout: 30000 })
    await expect(slowFileRow.locator('.node-checkbox')).toBeEnabled()
    await expect(calcFileRow.locator('.node-checkbox')).toBeEnabled()
    await expect(page.locator('#btn-clear-selection')).toBeEnabled()
    await expect(rootDirRow).not.toHaveClass(/row-has-running/)
    await expect(slowFileRow).not.toHaveClass(/row-has-running/)
    await expect(classRow).not.toHaveClass(/row-has-running/)
    await expect(slowFuncRow).toHaveClass(/row-outcome-passed/)

    // Collapse slowFileRow back and verify it has its rollup outcome color
    await slowFileRow.locator('.toggle-icon').click()
    await expect(slowFileRow).toHaveClass(/row-has-/)

    // 3. Start running again and click Stop mid-run; verify running state restores previous outcome
    await page.locator('.btn-primary').click()
    await expect(stopBtn).toBeVisible({ timeout: 5000 })
    await expect(slowFileRow.locator('.node-checkbox')).toBeDisabled()
    await expect(slowFileRow).toHaveClass(/row-has-running/)
    await stopBtn.click()

    await expect(page.locator('.btn-primary')).toBeVisible({ timeout: 10000 })
    await expect(slowFileRow.locator('.node-checkbox')).toBeEnabled()
    await expect(slowFileRow).not.toHaveClass(/row-has-running/)
    await expect(rootDirRow).not.toHaveClass(/row-has-running/)
    await expect(slowFileRow).toHaveClass(/row-has-/)
  })

  test('should update live running state and rollup chips across Integration and Acceptance suites', async ({ page }) => {
    await page.waitForSelector('.tree-container', { timeout: 60000 })

    // 1. Switch to Integration Tests (which prints === banners and multi-line log_cli logs)
    const suiteSelect = page.locator('.suite-select')
    await suiteSelect.selectOption({ index: 1 })

    const apiFileRow = page.locator('.node-row:has-text("test_app_api.py")')
    await expect(apiFileRow).toBeVisible({ timeout: 15000 })

    // Expand test_app_api.py so class and methods are visible
    await apiFileRow.locator('.toggle-icon').click()
    const apiClassRow = page.locator('.node-row:has-text("TestCalculatorApiService")')
    const lastApiMethodRow = page.locator('.node-row:has-text("test_divide_by_zero_error_message")')
    await expect(apiClassRow).toBeVisible()
    await expect(lastApiMethodRow).toBeVisible()

    // Select test_app_api.py and run
    await apiFileRow.locator('.node-checkbox').click()
    await page.locator('.btn-primary').click()

    const stopBtn = page.locator('.btn-danger')
    await expect(stopBtn).toBeVisible({ timeout: 5000 })
    await expect(apiFileRow).toHaveClass(/row-has-running/)
    await expect(apiClassRow).toHaveClass(/row-has-running/)
    await expect(lastApiMethodRow).toHaveClass(/row-outcome-running/)

    // Wait for completion and verify TestCalculatorApiService methods updated despite === batch log banners
    await expect(stopBtn).not.toBeVisible({ timeout: 30000 })
    await expect(apiFileRow).not.toHaveClass(/row-has-running/)
    await expect(apiClassRow).not.toHaveClass(/row-has-running/)
    await expect(lastApiMethodRow).toHaveClass(/row-outcome-passed/)

    // 2. Switch to Acceptance Tests and run with Run Selected (0) (unselected Run All)
    await suiteSelect.selectOption({ index: 2 })
    const featureFileRow = page.locator('.node-row:has-text("streaming_logger.feature")')
    await expect(featureFileRow).toBeVisible({ timeout: 15000 })
    await featureFileRow.locator('.toggle-icon').click()

    const slowScenarioRow = page.locator('.node-row:has-text("Sequential steps with live logging progression")')
    await expect(slowScenarioRow).toBeVisible()

    await page.locator('.btn-primary').click()
    await expect(stopBtn).toBeVisible({ timeout: 5000 })
    await expect(featureFileRow).toHaveClass(/row-has-running/)
    await expect(slowScenarioRow).toHaveClass(/row-outcome-running/)

    await expect(stopBtn).not.toBeVisible({ timeout: 30000 })
    await expect(featureFileRow).not.toHaveClass(/row-has-running/)
    await expect(slowScenarioRow).toHaveClass(/row-outcome-passed/)
  })

  test('should copy Terminal Output selection with Ctrl+C and Cmd+C without overwriting clipboard when unselected', async ({ page, context }) => {
    await context.grantPermissions(['clipboard-read', 'clipboard-write'])
    await page.waitForSelector('.tree-container', { timeout: 60000 })

    // Run test_calculator.py so Terminal Output has multi-line logs
    const calcFileRow = page.locator('.node-row:has-text("test_calculator.py")')
    await calcFileRow.locator('.node-checkbox').click()
    await page.locator('.btn-primary').click()

    const stopBtn = page.locator('.btn-danger')
    await expect(stopBtn).toBeVisible({ timeout: 5000 })
    await expect(stopBtn).not.toBeVisible({ timeout: 30000 })

    const xtermScreen = page.locator('.terminal-container .xterm-screen')
    await expect(xtermScreen).toBeVisible()

    // Seed clipboard with a sentinel value
    await page.evaluate(() => navigator.clipboard.writeText('INITIAL_CLIPBOARD_SENTINEL'))

    // 1. Focus terminal without selecting text (single click) and press Ctrl+C -> clipboard must NOT be overwritten
    const box = await xtermScreen.boundingBox()
    await page.mouse.click(box.x + 20, box.y + 15)
    await page.keyboard.press('Control+c')
    const afterEmptyCtrlC = await page.evaluate(() => navigator.clipboard.readText())
    expect(afterEmptyCtrlC).toBe('INITIAL_CLIPBOARD_SENTINEL')

    // 2. Drag-select a partial range on the first visible line in Terminal Output and press Ctrl+C
    await page.mouse.move(box.x + 10, box.y + 12)
    await page.mouse.down()
    await page.mouse.move(box.x + 180, box.y + 12, { steps: 10 })
    await page.mouse.up()

    await page.keyboard.press('Control+c')
    const ctrlCCopied = await page.evaluate(() => navigator.clipboard.readText())
    expect(ctrlCCopied).not.toBe('INITIAL_CLIPBOARD_SENTINEL')
    expect(ctrlCCopied.trim().length).toBeGreaterThan(0)
    expect(ctrlCCopied).not.toContain('\n')

    // 3. Reset clipboard sentinel, re-select text in Terminal Output, and press Cmd+C (Meta+c)
    await page.evaluate(() => navigator.clipboard.writeText('SECOND_CLIPBOARD_SENTINEL'))
    await page.mouse.move(box.x + 10, box.y + 12)
    await page.mouse.down()
    await page.mouse.move(box.x + 180, box.y + 12, { steps: 10 })
    await page.mouse.up()

    await page.keyboard.press('Meta+c')
    const cmdCCopied = await page.evaluate(() => navigator.clipboard.readText())
    expect(cmdCCopied).toBe(ctrlCCopied)

    // 4. Click Copy Output toolbar button -> copies the entire terminal output, not just the partial selection
    await page.locator('.btn-copy-terminal').click()
    const fullOutputCopied = await page.evaluate(() => navigator.clipboard.readText())
    expect(fullOutputCopied.length).toBeGreaterThan(ctrlCCopied.length)
    expect(fullOutputCopied).toContain('test_calculator.py')
    expect(fullOutputCopied).toContain('passed')
  })

  test('should show run duration for each Execution History row across pytest and behave runs', async ({ page }) => {
    await page.waitForSelector('.tree-container', { timeout: 60000 })

    // 1. Run test_calculator.py in Unit Tests (pytest)
    const calcFileRow = page.locator('.node-row:has-text("test_calculator.py")')
    await calcFileRow.locator('.node-checkbox').click()
    await page.locator('.btn-primary').click()

    const stopBtn = page.locator('.btn-danger')
    await expect(stopBtn).toBeVisible({ timeout: 5000 })
    await expect(stopBtn).not.toBeVisible({ timeout: 30000 })

    // Read summary.report.duration from JSON Report tab and compute expected formatted string
    await page.click('button:has-text("JSON Report")')
    const jsonText = await page.locator('.json-code').innerText()
    const parsedReport = JSON.parse(jsonText)
    const reportDuration = Number(parsedReport.duration)
    const expectedPytestDuration =
      reportDuration < 0.001
        ? '<1ms'
        : reportDuration < 1.0
          ? `${Math.round(reportDuration * 1000)}ms`
          : `${reportDuration.toFixed(2)}s`

    // Verify Execution History row shows the exact formatted duration from summary.report.duration
    await page.click('button:has-text("Execution History")')
    const historyItems = page.locator('.history-item')
    await expect(historyItems).toHaveCount(1)
    await expect(historyItems.nth(0).locator('.history-duration')).toHaveText(expectedPytestDuration)

    // 2. Switch to Acceptance Tests (behave) and run calculator.feature
    const suiteSelect = page.locator('.suite-select')
    await suiteSelect.selectOption({ index: 2 })
    const featureRow = page.locator('.node-row:has-text("calculator.feature")')
    await expect(featureRow).toBeVisible({ timeout: 15000 })
    await featureRow.locator('.node-checkbox').click()
    await page.locator('.btn-primary').click()

    await expect(stopBtn).toBeVisible({ timeout: 5000 }).catch(() => {})
    await expect(stopBtn).not.toBeVisible({ timeout: 30000 })

    // Switch back to Execution History and verify:
    // - Both history rows are present
    // - Newest row (index 0, behave) displays its formatted duration parsed from Took Xmin Y.ZZZs
    // - Earlier row (index 1, pytest) still preserves its original expectedPytestDuration
    await page.click('button:has-text("Execution History")')
    await expect(historyItems).toHaveCount(2)
    await expect(historyItems.nth(0).locator('.history-duration')).toBeVisible()
    await expect(historyItems.nth(0).locator('.history-duration')).toHaveText(/^(<1ms|\d+ms|\d+\.\d{2}s)$/)
    await expect(historyItems.nth(1).locator('.history-duration')).toHaveText(expectedPytestDuration)
  })
})
