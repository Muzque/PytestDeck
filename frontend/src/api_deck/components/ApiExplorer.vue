<script setup>
import { ref, computed } from 'vue'
import ApiTreeNode from './ApiTreeNode.vue'

const props = defineProps({
  apiTree: { type: Array, default: () => [] },
  selectedIds: { type: Object, required: true },
  selectedCount: { type: Number, default: 0 },
  activeRequestId: { type: String, default: null },
  isRunningBatch: { type: Boolean, default: false }
})

const emit = defineEmits([
  'new-request',
  'new-group',
  'select-request',
  'toggle-check',
  'clear-selection',
  'delete-node',
  'drop-node',
  'rename-node',
  'run-selected'
])

const searchQuery = ref('')
const methodFilter = ref('ALL')

const METHOD_FILTERS = ['ALL', 'GET', 'POST', 'PUT', 'DELETE']

const isFiltering = computed(() => {
  return searchQuery.value.trim().length > 0 || methodFilter.value !== 'ALL'
})

const filterNodes = (nodes, qLower, mFilter) => {
  const out = []
  for (const node of nodes) {
    if (node.node_type === 'group') {
      const groupNameMatched = !qLower || String(node.name || '').toLowerCase().includes(qLower)
      const filteredChildren = filterNodes(
        node.children || [],
        groupNameMatched ? '' : qLower,
        mFilter
      )
      if (filteredChildren.length > 0 || (groupNameMatched && mFilter === 'ALL')) {
        out.push({
          ...node,
          children: filteredChildren
        })
      }
    } else {
      const matchesMethod = mFilter === 'ALL' || String(node.method || 'GET').toUpperCase() === mFilter
      const matchesQuery =
        !qLower ||
        String(node.name || '').toLowerCase().includes(qLower) ||
        String(node.path || '').toLowerCase().includes(qLower) ||
        String(node.method || '').toLowerCase().includes(qLower)
      if (matchesMethod && matchesQuery) {
        out.push(node)
      }
    }
  }
  return out
}

const filteredApiTree = computed(() => {
  if (!isFiltering.value) return props.apiTree
  return filterNodes(
    props.apiTree,
    searchQuery.value.trim().toLowerCase(),
    methodFilter.value
  )
})

const onRootDrop = (e) => {
  const draggedId = e.dataTransfer.getData('text/plain')
  if (!draggedId) return
  emit('drop-node', {
    nodeId: draggedId,
    targetParentId: null,
    targetIndex: props.apiTree.length,
    createGroupWithNodeId: null
  })
}
</script>

<template>
  <div class="explorer-section api-explorer-section">
    <!-- Top Toolbar -->
    <div class="explorer-toolbar">
      <button
        id="btn-run-selected-apis"
        type="button"
        class="btn btn-primary btn-run-selected"
        :disabled="isRunningBatch"
        title="Run Selected APIs or Groups"
        @click="emit('run-selected')"
      >
        <span class="btn-icon">{{ isRunningBatch ? '⏳' : '▶' }}</span>
        <span class="btn-label">
          {{ isRunningBatch ? 'Running APIs...' : `Run Selected (${selectedCount})` }}
        </span>
      </button>

      <div class="toolbar-actions">
        <button
          id="btn-new-api"
          type="button"
          class="btn-api-action"
          title="Add New API Request"
          @click="emit('new-request')"
        >
          + API
        </button>
        <button
          id="btn-new-api-group"
          type="button"
          class="btn-api-action"
          title="Add New API Group"
          @click="emit('new-group')"
        >
          + Group
        </button>
        <button
          id="btn-clear-api-selection"
          type="button"
          class="btn-icon-action"
          :disabled="selectedCount === 0 && selectedIds.size === 0"
          title="Clear API Selection"
          @click="emit('clear-selection')"
        >
          🧹
        </button>
      </div>
    </div>

    <!-- Search & Method Filter Bar for Huge API Lists -->
    <div class="explorer-filter-bar">
      <div class="search-input-wrap">
        <input
          id="api-search-input"
          v-model="searchQuery"
          type="text"
          class="explorer-search-input"
          placeholder="Search APIs by name, path, or method..."
        />
        <button
          v-if="searchQuery"
          type="button"
          class="btn-clear-search"
          @click="searchQuery = ''"
        >
          ×
        </button>
      </div>
      <div class="status-filter-group">
        <button
          v-for="m in METHOD_FILTERS"
          :key="m"
          type="button"
          class="status-filter-btn"
          :class="{ active: methodFilter === m }"
          @click="methodFilter = m"
        >
          {{ m }}
        </button>
      </div>
    </div>

    <div class="drag-hint-strip">
      💡 Tip: Drag an API onto another API or Group to organize into folders.
    </div>

    <!-- API Tree Container -->
    <div
      v-if="filteredApiTree.length > 0"
      class="tree-container api-tree-container"
      @dragover.prevent
      @drop="onRootDrop"
    >
      <ApiTreeNode
        v-for="item in filteredApiTree"
        :key="item.id"
        :node="item"
        :selectedIds="selectedIds"
        :activeRequestId="activeRequestId"
        :forceExpand="isFiltering"
        @select-request="emit('select-request', $event)"
        @toggle-check="emit('toggle-check', $event)"
        @delete-node="emit('delete-node', $event)"
        @drop-node="emit('drop-node', $event)"
        @rename-node="emit('rename-node', $event)"
      />
    </div>
    <div v-else class="tree-loading api-empty-state">
      <p>No API requests yet.</p>
      <button type="button" class="btn btn-primary" style="margin-top: 8px;" @click="emit('new-request')">
        + Create First API Request
      </button>
    </div>
  </div>
</template>

<style scoped>
.btn-api-action {
  font-size: 0.74rem;
  font-weight: 600;
  padding: 5px 9px;
  border-radius: 6px;
  background: var(--bg-input);
  color: var(--text-main);
  border: 1px solid var(--border-color);
}

.btn-api-action:hover {
  border-color: var(--accent-blue);
  color: var(--accent-blue);
}

.drag-hint-strip {
  font-size: 0.71rem;
  color: var(--text-muted);
  padding: 4px 12px;
  border-bottom: 1px solid var(--border-color);
  background: rgba(255, 255, 255, 0.02);
}

.api-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
}
</style>
