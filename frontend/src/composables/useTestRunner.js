import { ref, computed, watch, onMounted } from 'vue'

export function useTestRunner() {
  const targetPath = ref('')
  const activeSuite = ref('backend/tests/unit')
  const isDiscovering = ref(false)
  const isRunning = ref(false)
  const testTree = ref(null)
  const selectedNodes = ref(new Set())
  const activeTab = ref('live')

  const selectedTestDetail = ref(null)
  const isLoadingDetail = ref(false)

  const isDetailSuite = computed(() => {
    const s = (activeSuite.value || '').toLowerCase()
    return s.includes('integration') || s.includes('acceptance') || s.endsWith('.feature')
  })

  const findNodeById = (root, id) => {
    if (!root) return null
    if (root.id === id) return root
    if (root.children && root.children.length > 0) {
      for (const child of root.children) {
        const found = findNodeById(child, id)
        if (found) return found
      }
    }
    return null
  }

  const singleSelectedNode = computed(() => {
    if (selectedNodes.value.size !== 1) return null
    const [id] = Array.from(selectedNodes.value)
    const node = findNodeById(testTree.value, id)
    if (node) {
      if (node.type === 'function' || node.id.includes('::') || !node.children || node.children.length === 0) {
        return node
      }
      return null
    }
    if (id && (id.includes('::') || id.endsWith('.py') || id.endsWith('.feature'))) {
      return { id, name: id.split('::').pop(), type: 'function' }
    }
    return null
  })

  const fetchTestDetail = async (nodeId) => {
    if (!nodeId) {
      selectedTestDetail.value = null
      return
    }
    isLoadingDetail.value = true
    try {
      const res = await fetch('/api/test-detail', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_path: targetPath.value,
          node_id: nodeId
        })
      })
      if (res.ok) {
        const data = await res.json()
        selectedTestDetail.value = data
        if (data && !data.latest_run && nodeId && methodOutputs.value[nodeId]) {
          const updated = { ...methodOutputs.value }
          delete updated[nodeId]
          methodOutputs.value = updated
          try {
            localStorage.setItem('pytestdeck_method_outputs', JSON.stringify(methodOutputs.value))
          } catch {
            // Ignore storage errors
          }
        }
      } else {
        selectedTestDetail.value = null
      }
    } catch (err) {
      console.error('Failed to fetch test detail:', err)
      selectedTestDetail.value = null
    } finally {
      isLoadingDetail.value = false
    }
  }

  const methodOutputs = ref({})
  const liveMethodRun = ref(null)

  try {
    const saved = localStorage.getItem('pytestdeck_method_outputs')
    if (saved) {
      methodOutputs.value = JSON.parse(saved)
    }
  } catch (e) {
    console.error('Failed to parse cached method outputs', e)
  }

  const loadStoredMethodOutputs = async () => {
    try {
      const url = targetPath.value ? `/api/test-runs?target_path=${encodeURIComponent(targetPath.value)}` : '/api/test-runs'
      const res = await fetch(url)
      if (res.ok) {
        const data = await res.json()
        methodOutputs.value = data.runs || {}
        try {
          localStorage.setItem('pytestdeck_method_outputs', JSON.stringify(methodOutputs.value))
        } catch {
          // Ignore storage errors
        }
      }
    } catch (e) {
      console.error('Failed to load runs from server SQLite database', e)
    }
  }

  loadStoredMethodOutputs()

  if (typeof window !== 'undefined') {
    window.addEventListener('focus', () => {
      loadStoredMethodOutputs()
    })
  }

  watch(targetPath, () => {
    loadStoredMethodOutputs()
    loadStoredRunOptions()
  })

  const clearMethodOutput = async (nodeId) => {
    if (!nodeId) return
    try {
      await fetch('/api/test-runs', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_path: targetPath.value || '',
          node_id: nodeId
        })
      })
    } catch (e) {
      console.error('Failed to delete run from server', e)
    }

    const updated = { ...methodOutputs.value }
    delete updated[nodeId]
    for (const key of Object.keys(updated)) {
      if (key.endsWith(nodeId) || nodeId.endsWith(key)) {
        delete updated[key]
      }
    }
    methodOutputs.value = updated
    try {
      localStorage.setItem('pytestdeck_method_outputs', JSON.stringify(methodOutputs.value))
    } catch {
      // Ignore storage errors
    }

    // Also update selectedTestDetail if active
    if (selectedTestDetail.value && selectedTestDetail.value.node_id === nodeId) {
      selectedTestDetail.value.latest_run = null
      selectedTestDetail.value.modified_since_run = false
    }
  }

  const clearAllMethodOutputs = async () => {
    try {
      await fetch('/api/test-runs', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_path: targetPath.value || ''
        })
      })
    } catch (e) {
      console.error('Failed to clear runs from server', e)
    }
    methodOutputs.value = {}
    try {
      localStorage.removeItem('pytestdeck_method_outputs')
    } catch {
      // Ignore storage errors
    }
    if (selectedTestDetail.value) {
      selectedTestDetail.value.latest_run = null
      selectedTestDetail.value.modified_since_run = false
    }
  }

  const getMethodOutput = (nodeId) => {
    if (!nodeId) return null
    if (methodOutputs.value[nodeId]) return methodOutputs.value[nodeId]
    for (const [key, val] of Object.entries(methodOutputs.value)) {
      if (nodeId.endsWith(key) || key.endsWith(nodeId)) {
        return val
      }
    }
    return null
  }

  const currentMethodOutput = computed(() => {
    if (!singleSelectedNode.value) return null
    if (isRunning.value && liveMethodRun.value) {
      return liveMethodRun.value
    }
    return getMethodOutput(singleSelectedNode.value.id)
  })

  const runSingleMethod = (nodeId) => {
    if (!nodeId || isRunning.value) return
    selectedNodes.value = new Set([nodeId])
    if (!extraArgs.value.includes('-s')) {
      extraArgs.value = extraArgs.value ? `${extraArgs.value} -s` : '-s'
    }
    const wasDetail = activeTab.value === 'detail'
    runTests()
    if (wasDetail) {
      activeTab.value = 'detail'
    }
  }

  watch([singleSelectedNode, isDetailSuite], async ([node, detailSuite]) => {
    if (detailSuite && node) {
      await fetchTestDetail(node.id)
      activeTab.value = 'detail'
    } else {
      selectedTestDetail.value = null
      if (activeTab.value === 'detail') {
        activeTab.value = 'live'
      }
    }
  })

  const logs = ref([])
  const exitCode = ref(null)
  const summary = ref(null)
  const markerFilter = ref('')
  const extraArgs = ref('')

  let isInitialRunOptionsLoaded = false

  const loadStoredRunOptions = async () => {
    try {
      const url = targetPath.value
        ? `/api/run-options?target_path=${encodeURIComponent(targetPath.value)}`
        : '/api/run-options'
      const res = await fetch(url)
      if (res.ok) {
        const data = await res.json()
        if (data.marker_filter !== undefined) markerFilter.value = data.marker_filter || ''
        if (data.extra_args !== undefined) extraArgs.value = data.extra_args || ''
      }
    } catch (e) {
      console.error('Failed to load run options from server', e)
    } finally {
      isInitialRunOptionsLoaded = true
    }
  }

  const persistRunOptions = async () => {
    if (!isInitialRunOptionsLoaded) return
    try {
      await fetch('/api/run-options', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_path: targetPath.value || '',
          marker_filter: markerFilter.value || '',
          extra_args: extraArgs.value || ''
        })
      })
    } catch (e) {
      console.error('Failed to save run options to server', e)
    }
  }

  loadStoredRunOptions()

  watch([markerFilter, extraArgs], () => {
    persistRunOptions()
  })


  const runHistory = ref([])
  const selectedHistoryId = ref(null)

  let ws = null

  const availableSuites = ref([
    { label: 'Unit Tests', path: 'backend/tests/unit' },
    { label: 'Integration Tests', path: 'backend/tests/integration' },
    { label: 'Acceptance (Behave)', path: 'backend/tests/acceptance' }
  ])

  const MAX_LOG_LINES = 50000

  const appendLog = (line) => {
    logs.value.push(line)
    if (logs.value.length > MAX_LOG_LINES + 5000) {
      logs.value.splice(0, 5000)
    }
  }

  const discoverTests = async () => {
    isDiscovering.value = true
    selectedNodes.value = new Set()
    try {
      const res = await fetch('/api/discover', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_path: targetPath.value,
          suite_rel_path: activeSuite.value
        })
      })
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.detail || `Discovery failed with status ${res.status}`)
      }
      const data = await res.json()
      testTree.value = data.tree

      if (data.tree) {
        const idSet = new Set()
        collectAllChildIds(data.tree, idSet)
        try {
          await fetch('/api/test-runs/prune', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              target_path: targetPath.value || '',
              valid_nodes: Array.from(idSet)
            })
          })
        } catch {
          // Ignore network errors during prune
        }
        await loadStoredMethodOutputs()
      }
    } catch (err) {
      console.error(err)
      appendLog(`\x1b[1;33mDiscovery: ${err.message}\x1b[0m\r\n`)
      testTree.value = null
    } finally {
      isDiscovering.value = false
    }
  }

  const collectAllChildIds = (node, idSet = new Set()) => {
    idSet.add(node.id)
    if (node.children && node.children.length > 0) {
      node.children.forEach(child => collectAllChildIds(child, idSet))
    }
    return idSet
  }

  const toggleSelectNode = (node) => {
    const newSet = new Set(selectedNodes.value)
    const isCurrentlySelected = newSet.has(node.id)
    const allIds = collectAllChildIds(node)

    if (isCurrentlySelected) {
      allIds.forEach(id => newSet.delete(id))
    } else {
      allIds.forEach(id => newSet.add(id))
    }
    selectedNodes.value = newSet
  }

  const clearSelections = () => {
    selectedNodes.value = new Set()
  }

  const getExecutionNodes = () => {
    const selected = Array.from(selectedNodes.value)
    if (selected.length === 0) return []

    return selected.filter(nodeId => {
      return !selected.some(otherId => {
        if (otherId === nodeId) return false
        return nodeId.startsWith(otherId + '/') || nodeId.startsWith(otherId + '::')
      })
    })
  }

  const runTests = () => {
    if (isRunning.value) return
    isRunning.value = true
    logs.value = []
    exitCode.value = null
    summary.value = null
    selectedHistoryId.value = null
    activeTab.value = 'live'

    let retries = 0
    const maxRetries = 3

    const connectWebSocket = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      ws = new WebSocket(`${protocol}//${window.location.host}/ws/run`)

      ws.onopen = () => {
        retries = 0
        const nodesToRun = getExecutionNodes()
        const payload = {
          action: 'START',
          target_path: targetPath.value,
          nodes: nodesToRun,
          marker: markerFilter.value || null,
          extra_args: extraArgs.value ? extraArgs.value.trim().split(/\s+/) : []
        }
        ws.send(JSON.stringify(payload))
      }

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          if (msg.type === 'stdout' || msg.type === 'status') {
            appendLog(msg.data)
            if (singleSelectedNode.value && selectedNodes.value.size === 1) {
              const nid = singleSelectedNode.value.id
              if (!liveMethodRun.value) {
                liveMethodRun.value = {
                  node_id: nid,
                  outcome: 'running',
                  duration: null,
                  timestamp: new Date().toLocaleTimeString(),
                  output: msg.data
                }
              } else {
                liveMethodRun.value.output += msg.data
              }
            }
          } else if (msg.type === 'finished') {
            isRunning.value = false
            exitCode.value = msg.exit_code
            summary.value = msg.summary

            if (msg.method_outputs) {
              methodOutputs.value = {
                ...methodOutputs.value,
                ...msg.method_outputs
              }
              try {
                localStorage.setItem('pytestdeck_method_outputs', JSON.stringify(methodOutputs.value))
              } catch {
                // Ignore storage limits
              }

            }
            liveMethodRun.value = null

            const historyRecord = {
              id: Date.now(),
              timestamp: new Date().toLocaleTimeString(),
              suite: activeSuite.value,
              exitCode: msg.exit_code,
              logs: [...logs.value],
              summary: msg.summary
            }
            runHistory.value.unshift(historyRecord)
            selectedHistoryId.value = historyRecord.id
          } else if (msg.type === 'error') {
            appendLog(`\x1b[1;31mError: ${msg.message}\x1b[0m\r\n`)
            isRunning.value = false
            liveMethodRun.value = null
          }
        } catch {
          appendLog(event.data)
        }

      }

      ws.onerror = (err) => {
        console.error('WebSocket connection error:', err)
        if (retries < maxRetries && isRunning.value) {
          retries++
          const delay = Math.pow(2, retries) * 500
          appendLog(`\x1b[1;33mWebSocket connection error. Retrying (${retries}/${maxRetries}) in ${delay}ms...\x1b[0m\r\n`)
          setTimeout(connectWebSocket, delay)
        } else {
          appendLog('\x1b[1;31mWebSocket Connection Error: Max retries reached.\x1b[0m\r\n')
          isRunning.value = false
        }
      }

      ws.onclose = () => {
        if (retries === 0 || retries >= maxRetries) {
          isRunning.value = false
        }
      }
    }

    connectWebSocket()
  }

  const stopTests = () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action: 'STOP' }))
    }
  }

  const selectHistoryItem = (item) => {
    selectedHistoryId.value = item.id
    logs.value = [...item.logs]
    exitCode.value = item.exitCode
    summary.value = item.summary
    activeTab.value = 'live'
  }

  const envStatus = ref({ ready: true, status: 'ready', message: '' })
  const envLogs = ref('')
  const showEnvLogModal = ref(false)
  let healthPollTimer = null
  let lastSeenLogOffset = 0

  const fetchEnvLogs = async () => {
    try {
      const res = await fetch('/api/health/logs?tail=500')
      if (res.ok) {
        const data = await res.json()
        envLogs.value = data.logs || ''
      }
    } catch {
      // Ignore transient network errors
    }
  }

  const checkHealth = async () => {
    try {
      const res = await fetch('/api/health')
      if (res.ok) {
        const data = await res.json()
        if (data.environment) {
          const wasNotReady = !envStatus.value.ready
          envStatus.value = data.environment

          // Stream live preparation logs to terminal if available
          if (data.environment.status === 'running') {
            if (data.environment.recent_logs) {
              const fullText = data.environment.recent_logs
              if (fullText.length > lastSeenLogOffset) {
                const newChunk = fullText.slice(lastSeenLogOffset)
                lastSeenLogOffset = fullText.length
                const lines = newChunk.split('\n')
                for (const line of lines) {
                  if (line.trim()) {
                    appendLog(`\x1b[90m[uv sync]\x1b[0m ${line}\r\n`)
                  }
                }
              }
              envLogs.value = fullText
            }
            if (showEnvLogModal.value) {
              fetchEnvLogs()
            }
          }

          if (wasNotReady && envStatus.value.ready) {
            appendLog('\x1b[1;32m[PytestDeck] Target environment is ready. Discovering tests...\x1b[0m\r\n')
            fetchEnvLogs()
            discoverTests()
          } else if (wasNotReady && data.environment.status === 'failed') {
            appendLog(`\x1b[1;31m[PytestDeck] ${data.environment.message}\x1b[0m\r\n`)
            fetchEnvLogs()
          }
        }
      }
    } catch {
      // Ignore transient network errors
    }
  }

  const startHealthPolling = () => {
    if (healthPollTimer) return
    healthPollTimer = setInterval(async () => {
      await checkHealth()
      if (envStatus.value.ready || envStatus.value.status === 'failed') {
        clearInterval(healthPollTimer)
        healthPollTimer = null
      }
    }, 2000)
  }

  const fetchConfig = async (overrideTarget = null) => {
    try {
      const urlParams = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null
      const queryTarget = overrideTarget || (urlParams ? urlParams.get('target_path') : null)
      const targetQuery = queryTarget ? `?target_path=${encodeURIComponent(queryTarget)}` : ''
      const res = await fetch(`/api/config${targetQuery}`)
      if (res.ok) {
        const data = await res.json()
        if (data.config) {
          availableSuites.value = [
            { label: 'Unit Tests', path: data.config.unit_dir || 'backend/tests/unit' },
            { label: 'Integration Tests', path: data.config.integration_dir || 'backend/tests/integration' },
            { label: 'Acceptance (Behave)', path: data.config.acceptance_dir || 'backend/tests/acceptance' }
          ]
          activeSuite.value = availableSuites.value[0].path
        }
        if (queryTarget) {
          targetPath.value = queryTarget
        } else if (data.default_target_path) {
          targetPath.value = data.default_target_path
        }
      }
    } catch {
      // Keep default if config fetch fails
    }

    await checkHealth()
    await fetchEnvLogs()
    if (!envStatus.value.ready && envStatus.value.status === 'running') {
      appendLog(`\x1b[1;33m[PytestDeck] ${envStatus.value.message}\x1b[0m\r\n`)
      startHealthPolling()
    } else {
      discoverTests()
    }
  }

  onMounted(() => {
    fetchConfig()
  })

  return {
    targetPath,
    activeSuite,
    availableSuites,
    isDiscovering,
    isRunning,
    envStatus,
    testTree,
    selectedNodes,
    activeTab,
    logs,
    exitCode,
    summary,
    markerFilter,
    extraArgs,
    runHistory,
    selectedHistoryId,
    discoverTests,
    toggleSelectNode,
    clearSelections,
    runTests,
    stopTests,
    selectHistoryItem,
    envLogs,
    showEnvLogModal,
    fetchEnvLogs,
    selectedTestDetail,
    isLoadingDetail,
    isDetailSuite,
    singleSelectedNode,
    fetchTestDetail,
    methodOutputs,
    currentMethodOutput,
    runSingleMethod,
    getMethodOutput,
    clearMethodOutput,
    clearAllMethodOutputs,
    fetchConfig
  }
}


