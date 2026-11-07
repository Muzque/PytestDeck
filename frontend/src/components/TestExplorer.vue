<script setup>
import { ref, computed } from 'vue'
import TreeNode from './TreeNode.vue'
import RunOptionsModal from './RunOptionsModal.vue'

const props = defineProps({
  activeSuite: { type: String, required: true },
  markerFilter: { type: String, default: '' },
  extraArgs: { type: String, default: '' },
  testTree: { type: Object, default: null },
  selectedNodes: { type: Object, required: true },
  selectedCount: { type: Number, default: 0 },
  failedCount: { type: Number, default: 0 },
  isRunning: { type: Boolean, default: false },
  isDiscovering: { type: Boolean, default: false },
  methodOutputs: { type: Object, default: () => ({}) }
})

const emit = defineEmits([
  'update:markerFilter',
  'update:extraArgs',
  'toggle-select',
  'clear-selection',
  'discover',
  'run',
  'run-failed',
  'stop',
  'clear-all-history',
  'prune-branches'
])


const showRunOptions = ref(false)
const searchQuery = ref('')
const statusFilter = ref('all')

const STATUS_FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'failed', label: 'Failed' },
  { key: 'passed', label: 'Passed' },
  { key: 'skipped', label: 'Skipped' },
  { key: 'not-run', label: 'Not Run' }
]

const activeOptionCount = computed(() =>
  (props.markerFilter ? 1 : 0) + (props.extraArgs ? 1 : 0)
)

const isSameTestNodeId = (idA, idB) => {
  if (!idA || !idB) return false
  const normA = idA.replace(/\\/g, '/')
  const normB = idB.replace(/\\/g, '/')
  if (normA === normB) return true
  const sepA = normA.indexOf('::')
  const sepB = normB.indexOf('::')
  if (sepA === -1 || sepB === -1) {
    return normA.endsWith('/' + normB) || normB.endsWith('/' + normA)
  }
  const tailA = normA.slice(sepA)
  const tailB = normB.slice(sepB)
  if (tailA !== tailB) return false
  const fileA = normA.slice(0, sepA)
  const fileB = normB.slice(0, sepB)
  return fileA === fileB || fileA.endsWith('/' + fileB) || fileB.endsWith('/' + fileA)
}

const findNodeRecord = (outputs, id) => {
  if (!id || !outputs) return null
  if (outputs[id]) return outputs[id]
  let bestKey = null
  let bestDiff = Infinity
  for (const key of Object.keys(outputs)) {
    if (outputs[key] && isSameTestNodeId(id, key)) {
      const diff = Math.abs(id.length - key.length)
      if (diff < bestDiff) {
        bestDiff = diff
        bestKey = key
      }
    }
  }
  return bestKey ? outputs[bestKey] : null
}

const normalizeOutcome = (raw) => {
  if (!raw) return 'not-run'
  const lower = String(raw).toLowerCase()
  if (lower === 'xfailed' || lower === 'xfail' || lower === 'skipped') return 'skipped'
  if (lower === 'xpassed' || lower === 'xpass' || lower === 'passed') return 'passed'
  if (lower === 'failed' || lower === 'error') return 'failed'
  if (lower === 'running') return 'running'
  return 'not-run'
}

const isFiltering = computed(() => {
  return searchQuery.value.trim().length > 0 || statusFilter.value !== 'all'
})

const filterTreeRecursive = (node, queryLower, statusKey, outputs, ancestorMatchedQuery = false) => {
  if (!node) return null
  const selfMatchesQuery =
    !queryLower ||
    String(node.name || '').toLowerCase().includes(queryLower) ||
    String(node.id || '').toLowerCase().includes(queryLower)

  const branchMatchedQuery = ancestorMatchedQuery || selfMatchesQuery

  if (node.children && node.children.length > 0) {
    const filteredChildren = []
    for (const child of node.children) {
      const matchedChild = filterTreeRecursive(
        child,
        queryLower,
        statusKey,
        outputs,
        branchMatchedQuery
      )
      if (matchedChild) {
        filteredChildren.push(matchedChild)
      }
    }
    if (filteredChildren.length === 0) return null
    return {
      ...node,
      children: filteredChildren
    }
  }

  if (!branchMatchedQuery) return null

  if (statusKey !== 'all') {
    const rec = findNodeRecord(outputs, node.id)
    const outcome = normalizeOutcome(rec?.outcome)
    if (outcome !== statusKey) return null
  }

  return node
}

const filteredTree = computed(() => {
  if (!props.testTree) return null
  if (!isFiltering.value) return props.testTree
  return filterTreeRecursive(
    props.testTree,
    searchQuery.value.trim().toLowerCase(),
    statusFilter.value,
    props.methodOutputs || {}
  )
})
</script>

<template>
  <div class="explorer-section">
    <!-- Unified Action Toolbar: Run Selected, Re-run Failed, Refresh, and Run Options -->
    <div class="explorer-toolbar">
      <button
        v-if="!isRunning"
        class="btn btn-primary btn-run-selected"
        @click="emit('run')"
        title="Run Selected Tests"
      >
        <span class="btn-icon">▶</span>
        <span class="btn-label">Run Selected ({{ selectedCount }})</span>
      </button>
      <button
        v-else
        class="btn btn-danger btn-run-selected"
        @click="emit('stop')"
        title="Stop Execution"
      >
        <span class="btn-icon">⏹</span>
        <span class="btn-label">Stop Execution</span>
      </button>

      <button
        v-if="!isRunning && failedCount > 0"
        id="btn-rerun-failed"
        class="btn btn-rerun-failed"
        :title="`Re-run ${failedCount} failed test${failedCount > 1 ? 's' : ''}`"
        @click="emit('run-failed')"
      >
        <span class="btn-icon">↻</span>
        <span class="btn-label">Re-run Failed ({{ failedCount }})</span>
      </button>

      <div class="toolbar-actions">
        <button
          class="btn-icon-action btn-refresh"
          :disabled="isDiscovering"
          @click="emit('discover')"
          title="Refresh Test Tree"
        >
          <span class="icon-refresh" :class="{ 'is-spinning': isDiscovering }">🔄</span>
        </button>

        <button
          id="btn-clear-selection"
          class="btn-icon-action btn-clear-selection"
          :class="{ 'has-selections': selectedCount > 0 || selectedNodes.size > 0 }"
          :disabled="(selectedCount === 0 && selectedNodes.size === 0) || isRunning"
          :title="selectedCount > 0 ? `Clear ${selectedCount} selected test${selectedCount > 1 ? 's' : ''}` : (selectedNodes.size > 0 ? 'Clear selections' : 'Clear selections (none selected)')"
          @click="emit('clear-selection')"
        >
          <span>🧹</span>
        </button>


        <button
          id="btn-run-options"
          class="btn-icon-action btn-run-options"
          :class="{ 'has-options': activeOptionCount > 0 }"
          title="Configure Run Options (-m markers, extra flags)"
          @click="showRunOptions = true"
        >
          <span>⚙️</span>
          <span v-if="activeOptionCount" class="run-options-count">{{ activeOptionCount }}</span>
        </button>
      </div>
    </div>

    <!-- Search and Status Filter Bar -->
    <div class="explorer-filter-bar">
      <div class="search-input-wrap">
        <input
          id="explorer-search-input"
          v-model="searchQuery"
          type="text"
          class="explorer-search-input"
          placeholder="Search tests or files..."
        />
        <button
          v-if="searchQuery"
          id="btn-clear-search"
          class="btn-clear-search"
          title="Clear search"
          @click="searchQuery = ''"
        >×</button>
      </div>
      <div class="status-filter-group">
        <button
          v-for="item in STATUS_FILTERS"
          :key="item.key"
          class="status-filter-btn"
          :class="{ active: statusFilter === item.key }"
          :data-status-filter="item.key"
          @click="statusFilter = item.key"
        >
          {{ item.label }}
        </button>
      </div>
    </div>

    <!-- Active Run Options Summary (compact strip below toolbar) -->
    <div v-if="activeOptionCount" class="run-options-summary">
      <div class="summary-chips">
        <span
          v-if="markerFilter"
          class="summary-chip"
          title="Click to edit marker"
          @click="showRunOptions = true"
        >
          <code>-m {{ markerFilter }}</code>
          <button
            class="chip-remove"
            title="Remove marker"
            @click.stop="emit('update:markerFilter', '')"
          >×</button>
        </span>

        <span
          v-if="extraArgs"
          class="summary-chip"
          title="Click to edit flags"
          @click="showRunOptions = true"
        >
          <code>{{ extraArgs }}</code>
          <button
            class="chip-remove"
            title="Remove extra flags"
            @click.stop="emit('update:extraArgs', '')"
          >×</button>
        </span>
      </div>

      <button
        class="btn-clear-all"
        title="Clear all options"
        @click="emit('update:markerFilter', ''); emit('update:extraArgs', '')"
      >Clear</button>
    </div>

    <div v-if="filteredTree" class="tree-container">
      <TreeNode 
        :node="filteredTree" 
        :selectedNodes="selectedNodes"
        :methodOutputs="methodOutputs"
        :isRunning="isRunning"
        :forceExpand="isFiltering"
        @toggle-select="emit('toggle-select', $event)"
      />
    </div>
    <div v-else-if="testTree && isFiltering" class="tree-loading tree-empty-filter">
      No matching tests found.
    </div>
    <div v-else class="tree-loading">
      No tests discovered.
    </div>

    <RunOptionsModal
      :show="showRunOptions"
      :markerFilter="markerFilter"
      :extraArgs="extraArgs"
      @update:markerFilter="emit('update:markerFilter', $event)"
      @update:extraArgs="emit('update:extraArgs', $event)"
      @clear-all-history="emit('clear-all-history')"
      @prune-branches="emit('prune-branches', $event)"
      @close="showRunOptions = false"
    />

  </div>
</template>
