import { ref, onMounted } from 'vue'

export function useTestRunner() {
  const targetPath = ref('')
  const activeSuite = ref('backend/tests/unit')
  const isDiscovering = ref(false)
  const isRunning = ref(false)
  const testTree = ref(null)
  const selectedNodes = ref(new Set())
  const activeTab = ref('live')

  const logs = ref([])
  const exitCode = ref(null)
  const summary = ref(null)
  const markerFilter = ref('')
  const extraArgs = ref('')

  const runHistory = ref([])
  const selectedHistoryId = ref(null)

  let ws = null

  const availableSuites = ref([
    { label: 'Unit Tests', path: 'backend/tests/unit' },
    { label: 'Integration Tests', path: 'backend/tests/integration' },
    { label: 'Acceptance (Behave)', path: 'backend/tests/acceptance' }
  ])

  const MAX_LOG_LINES = 5000

  const appendLog = (line) => {
    logs.value.push(line)
    if (logs.value.length > MAX_LOG_LINES) {
      logs.value = logs.value.slice(-MAX_LOG_LINES)
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
          } else if (msg.type === 'finished') {
            isRunning.value = false
            exitCode.value = msg.exit_code
            summary.value = msg.summary

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

  const fetchConfig = async () => {
    try {
      const res = await fetch('/api/config')
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
        if (data.default_target_path) {
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
    runTests,
    stopTests,
    selectHistoryItem,
    envLogs,
    showEnvLogModal,
    fetchEnvLogs
  }
}
