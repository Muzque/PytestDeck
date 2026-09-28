<script setup>
import { ref, onMounted } from 'vue'
import TreeNode from './components/TreeNode.vue'
import TerminalView from './components/TerminalView.vue'


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

// Compute minimal execution targets (avoid passing container file/folder AND child functions simultaneously)
const getExecutionNodes = () => {
  const selected = Array.from(selectedNodes.value)
  if (selected.length === 0) return []


  return selected.filter(nodeId => {
    return !selected.some(otherId => {
      if (otherId === nodeId) return false
      // If otherId is a parent path (folder/file) of nodeId
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

onMounted(() => {
  discoverTests()
})
</script>

<template>
  <div class="deck-app">
    <!-- Top Navigation Header -->
    <header class="deck-header">
      <div class="brand">
        <span class="logo">⚡</span>
        <h1>PytestDeck</h1>
      </div>

      <div class="target-controls">
        <input 
          v-model="targetPath" 
          type="text" 
          class="path-input" 
          placeholder="Target Repo Path..."
        />
        <select v-model="activeSuite" class="suite-select" @change="discoverTests">
          <option v-for="s in availableSuites" :key="s.path" :value="s.path">
            {{ s.label }}
          </option>
        </select>
        <button class="btn btn-secondary" @click="discoverTests" :disabled="isDiscovering">
          {{ isDiscovering ? 'Scanning...' : 'Refresh Tree' }}
        </button>
      </div>

      <div class="run-actions">
        <button v-if="!isRunning" class="btn btn-primary" @click="runTests">
          ▶ Run Selected ({{ selectedNodes.size }})
        </button>
        <button v-else class="btn btn-danger" @click="stopTests">
          ⏹ Stop Execution
        </button>
      </div>
    </header>

    <!-- Deck Main Body -->
    <div class="deck-body">
      <!-- Left Sidebar: Test Tree Explorer -->
      <aside class="deck-sidebar">
        <div class="sidebar-header">
          <h3>Test Explorer</h3>
          <span class="suite-tag">{{ activeSuite }}</span>
        </div>

        <div class="filter-box">
          <input v-model="markerFilter" placeholder="Marker (e.g. -m smoke)" class="filter-input" />
          <input v-model="extraArgs" placeholder="Extra flags (e.g. -v --tb=short)" class="filter-input" />
        </div>

        <div class="tree-container" v-if="testTree">
          <TreeNode 
            :node="testTree" 
            :selectedNodes="selectedNodes"
            @toggle-select="toggleSelectNode"
          />
        </div>
        <div v-else class="tree-loading">
          No tests discovered.
        </div>
      </aside>

      <!-- Right Main: Live Terminal & Metrics -->
      <main class="deck-main">
        <div class="tabs-header">
          <button 
            class="tab-btn" 
            :class="{ active: activeTab === 'live' }"
            @click="activeTab = 'live'"
          >
            Terminal Output
          </button>
          <button 
            class="tab-btn" 
            :class="{ active: activeTab === 'summary' }"
            @click="activeTab = 'summary'"
          >
            Metrics & Summary
          </button>
          <button 
            class="tab-btn" 
            :class="{ active: activeTab === 'report' }"
            @click="activeTab = 'report'"
          >
            JSON Report
          </button>
        </div>

        <div class="tab-content">
          <div v-show="activeTab === 'live'" class="tab-pane">
            <TerminalView :logs="logs" />
          </div>

          <div v-show="activeTab === 'summary'" class="tab-pane summary-pane">
            <div v-if="summary" class="summary-cards">
              <div class="card card-exit">
                <h4>Exit Code</h4>
                <div class="value" :class="{ pass: exitCode === 0, fail: exitCode !== 0 }">
                  {{ exitCode }}
                </div>
              </div>
              <div class="card card-total" v-if="summary.report">
                <h4>Total Tests</h4>
                <div class="value">{{ summary.report.summary?.total || 0 }}</div>
              </div>
              <div class="card card-pass" v-if="summary.report">
                <h4>Passed</h4>
                <div class="value pass">{{ summary.report.summary?.passed || 0 }}</div>
              </div>
              <div class="card card-fail" v-if="summary.report">
                <h4>Failed</h4>
                <div class="value fail">{{ summary.report.summary?.failed || 0 }}</div>
              </div>
            </div>
            <div v-else class="no-summary">
              Run tests to view execution summary report.
            </div>
          </div>

          <div v-show="activeTab === 'report'" class="tab-pane report-pane">
            <pre v-if="summary?.report" class="json-code">{{ JSON.stringify(summary.report, null, 2) }}</pre>
            <div v-else class="no-summary">
              No JSON report available. Run tests to generate report content.
            </div>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.deck-app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100vw;
  background: var(--bg-primary);
}

.deck-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
}
.brand h1 {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-main);
}

.target-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  max-width: 650px;
  margin: 0 20px;
}

.path-input {
  flex: 1;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 0.88rem;
}

.suite-select {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 0.88rem;
}

.btn {
  padding: 6px 14px;
  border-radius: 6px;
  font-weight: 600;
  font-size: 0.88rem;
}
.btn-primary { background: var(--accent-blue); color: #000; }
.btn-primary:hover { background: #7dd3fc; }
.btn-secondary { background: #334155; color: var(--text-main); }
.btn-secondary:hover { background: #475569; }
.btn-danger { background: var(--accent-red); color: #fff; }

.deck-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.deck-sidebar {
  width: 360px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 14px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-color);
}

.suite-tag {
  font-size: 0.75rem;
  background: var(--border-color);
  padding: 2px 8px;
  border-radius: 4px;
  color: var(--accent-blue);
}

.filter-box {
  padding: 10px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-bottom: 1px solid var(--border-color);
}

.filter-input {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 0.8rem;
}

.tree-container {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.deck-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
}

.tabs-header {
  display: flex;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.tab-btn {
  padding: 10px 20px;
  background: transparent;
  color: var(--text-muted);
  border-bottom: 2px solid transparent;
  font-weight: 500;
}

.tab-btn.active {
  color: var(--accent-blue);
  border-bottom-color: var(--accent-blue);
}

.tab-content {
  flex: 1;
  padding: 12px;
  position: relative;
}

.tab-pane {
  width: 100%;
  height: 100%;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.card {
  background: var(--bg-secondary);
  padding: 16px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.card h4 {
  font-size: 0.85rem;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.card .value {
  font-size: 1.8rem;
  font-weight: 700;
}

.value.pass { color: var(--accent-green); }
.value.fail { color: var(--accent-red); }

.no-summary {
  color: var(--text-muted);
  text-align: center;
  margin-top: 40px;
}

.report-pane {
  height: 100%;
  overflow: auto;
}

.json-code {
  background: var(--bg-secondary);
  color: var(--accent-blue);
  padding: 16px;
  border-radius: 6px;
  font-family: 'Fira Code', Menlo, Monaco, monospace;
  font-size: 0.85rem;
  overflow: auto;
  max-height: calc(100vh - 120px);
  border: 1px solid var(--border-color);
}
</style>
