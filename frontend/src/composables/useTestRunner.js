import { ref, onMounted } from 'vue'

export function useTestRunner() {
  const targetPath = ref('/Users/xuandi/repo/PytestDeck')
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
      const data = await res.json()
      testTree.value = data.tree
    } catch (err) {
      console.error(err)
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

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    ws = new WebSocket(`${protocol}//${window.location.host}/ws/run`)

    ws.onopen = () => {
      const nodesToRun = getExecutionNodes()
      const payload = {
        action: 'START',
        target_path: targetPath.value,
        nodes: nodesToRun,
        marker: markerFilter.value || null,
        extra_args: extraArgs.value ? extraArgs.value.split(' ') : []
      }
      ws.send(JSON.stringify(payload))
    }

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      if (msg.type === 'stdout' || msg.type === 'status') {
        logs.value.push(msg.data)
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
        logs.value.push(`\x1b[1;31mError: ${msg.message}\x1b[0m\r\n`)
        isRunning.value = false
      }
    }

    ws.onclose = () => {
      isRunning.value = false
    }
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

  onMounted(() => {
    discoverTests()
  })

  return {
    targetPath,
    activeSuite,
    availableSuites,
    isDiscovering,
    isRunning,
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
    selectHistoryItem
  }
}
