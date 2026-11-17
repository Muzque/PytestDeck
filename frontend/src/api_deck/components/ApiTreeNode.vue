<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  node: { type: Object, required: true },
  selectedIds: { type: Object, required: true },
  activeRequestId: { type: String, default: null },
  forceExpand: { type: Boolean, default: false }
})

const emit = defineEmits([
  'select-request',
  'toggle-check',
  'delete-node',
  'drop-node'
])

const isOpen = ref(true)
const isDragOver = ref(false)

const effectiveOpen = computed(() => props.forceExpand || isOpen.value)
const isGroup = computed(() => props.node.node_type === 'group')

const isChecked = computed(() => {
  if (props.selectedIds.has(props.node.id)) return true
  if (isGroup.value && props.node.children && props.node.children.length > 0) {
    const checkAll = (n) => {
      if (n.node_type === 'group') {
        return n.children && n.children.length > 0 && n.children.every(checkAll)
      }
      return props.selectedIds.has(n.id)
    }
    return checkAll(props.node)
  }
  return false
})

const rollupCounts = computed(() => {
  if (!isGroup.value) return { total: 0, passed: 0, warning: 0, failed: 0 }
  const counts = { total: 0, passed: 0, warning: 0, failed: 0 }
  const walk = (item) => {
    if (item.node_type === 'request') {
      counts.total++
      if (item.last_outcome === 'passed') counts.passed++
      else if (item.last_outcome === 'warning') counts.warning++
      else if (item.last_outcome === 'failed') counts.failed++
    }
    if (item.children) {
      for (const c of item.children) walk(c)
    }
  }
  walk(props.node)
  return counts
})

const onRowClick = () => {
  if (isGroup.value) {
    isOpen.value = !isOpen.value
  } else {
    emit('select-request', props.node)
  }
}

const onDragStart = (e) => {
  e.stopPropagation()
  e.dataTransfer.effectAllowed = 'move'
  e.dataTransfer.setData('text/plain', props.node.id)
}

const onDragOver = (e) => {
  e.preventDefault()
  e.stopPropagation()
  isDragOver.value = true
}

const onDragLeave = (e) => {
  e.stopPropagation()
  isDragOver.value = false
}

const onDrop = (e) => {
  e.preventDefault()
  e.stopPropagation()
  isDragOver.value = false
  const draggedId = e.dataTransfer.getData('text/plain')
  if (!draggedId || draggedId === props.node.id) return

  if (isGroup.value) {
    emit('drop-node', {
      nodeId: draggedId,
      targetParentId: props.node.id,
      targetIndex: (props.node.children || []).length,
      createGroupWithNodeId: null
    })
  } else {
    emit('drop-node', {
      nodeId: draggedId,
      targetParentId: props.node.parent_id || null,
      targetIndex: 0,
      createGroupWithNodeId: props.node.id
    })
  }
}
</script>

<template>
  <div class="api-tree-node" :data-node-id="node.id" :data-node-type="node.node_type">
    <div
      class="api-node-row"
      :class="{
        'is-active-req': !isGroup && activeRequestId === node.id,
        'is-checked': isChecked,
        'is-drag-over': isDragOver,
        'outcome-passed': !isGroup && node.last_outcome === 'passed',
        'outcome-warning': !isGroup && node.last_outcome === 'warning',
        'outcome-failed': !isGroup && node.last_outcome === 'failed'
      }"
      draggable="true"
      @click="onRowClick"
      @dragstart="onDragStart"
      @dragover="onDragOver"
      @dragleave="onDragLeave"
      @drop="onDrop"
    >
      <span
        v-if="isGroup"
        class="toggle-arrow"
        @click.stop="isOpen = !isOpen"
      >
        {{ effectiveOpen ? '▼' : '▶' }}
      </span>
      <span v-else class="drag-grip" title="Drag onto another API or Group">⋮⋮</span>

      <input
        type="checkbox"
        class="api-node-checkbox"
        :checked="isChecked"
        @click.stop
        @change="emit('toggle-check', node)"
      />

      <span v-if="isGroup" class="method-badge grp">GRP</span>
      <span v-else class="method-badge" :class="(node.method || 'GET').toLowerCase()">
        {{ node.method || 'GET' }}
      </span>

      <div class="api-node-labels">
        <span class="api-node-name">{{ node.name }}</span>
        <span v-if="!isGroup && node.path" class="api-node-path">{{ node.path }}</span>
      </div>

      <!-- Group rollup chips -->
      <div v-if="isGroup && rollupCounts.total > 0" class="group-rollup">
        <span v-if="rollupCounts.passed > 0" class="rollup-tag passed">{{ rollupCounts.passed }} ✓</span>
        <span v-if="rollupCounts.warning > 0" class="rollup-tag warning">{{ rollupCounts.warning }} ⚠</span>
        <span v-if="rollupCounts.failed > 0" class="rollup-tag failed">{{ rollupCounts.failed }} ✗</span>
        <span class="rollup-tag count">{{ rollupCounts.total }}</span>
      </div>

      <!-- Request status & duration badge -->
      <span
        v-if="!isGroup && node.last_status"
        class="req-status-chip"
        :class="node.last_outcome || 'failed'"
      >
        {{ node.last_status }} · {{ Math.round(node.last_duration_ms || 0) }}ms
      </span>

      <button
        type="button"
        class="btn-delete-node"
        title="Delete item"
        @click.stop="emit('delete-node', node.id)"
      >
        ×
      </button>
    </div>

    <div v-if="isGroup && effectiveOpen && node.children && node.children.length > 0" class="api-node-children">
      <ApiTreeNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :selectedIds="selectedIds"
        :activeRequestId="activeRequestId"
        :forceExpand="forceExpand"
        @select-request="emit('select-request', $event)"
        @toggle-check="emit('toggle-check', $event)"
        @delete-node="emit('delete-node', $event)"
        @drop-node="emit('drop-node', $event)"
      />
    </div>
  </div>
</template>

<style scoped>
.api-tree-node {
  user-select: none;
  font-size: 0.85rem;
}

.api-node-row {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 6px 8px;
  border-radius: 7px;
  cursor: pointer;
  border-left: 3px solid transparent;
  transition: background 0.14s ease, border-color 0.14s ease;
}

.api-node-row:hover {
  background: rgba(255, 255, 255, 0.07);
}

.api-node-row.is-active-req {
  background: rgba(56, 189, 248, 0.16);
  border-left-color: var(--accent-blue);
}

.api-node-row.is-drag-over {
  background: rgba(99, 102, 241, 0.25);
  outline: 1px dashed var(--accent-blue);
}

.api-node-row.outcome-passed {
  border-left-color: var(--accent-green);
}

.api-node-row.outcome-warning {
  border-left-color: var(--accent-yellow);
}

.api-node-row.outcome-failed {
  border-left-color: var(--accent-red);
}

.toggle-arrow,
.drag-grip {
  width: 18px;
  text-align: center;
  font-size: 0.75rem;
  color: var(--text-muted);
  flex-shrink: 0;
}

.api-node-checkbox {
  accent-color: var(--accent-blue);
  cursor: pointer;
  flex-shrink: 0;
}

.method-badge {
  font-size: 0.62rem;
  font-weight: 700;
  padding: 2px 5px;
  border-radius: 4px;
  letter-spacing: 0.04em;
  flex-shrink: 0;
  min-width: 38px;
  text-align: center;
}

.method-badge.get {
  background: rgba(56, 189, 248, 0.15);
  color: var(--accent-blue);
  border: 1px solid rgba(56, 189, 248, 0.35);
}

.method-badge.post {
  background: rgba(52, 211, 153, 0.15);
  color: var(--accent-green);
  border: 1px solid rgba(52, 211, 153, 0.35);
}

.method-badge.put,
.method-badge.patch {
  background: rgba(251, 191, 36, 0.15);
  color: var(--accent-yellow);
  border: 1px solid rgba(251, 191, 36, 0.35);
}

.method-badge.delete {
  background: rgba(248, 113, 113, 0.15);
  color: var(--accent-red);
  border: 1px solid rgba(248, 113, 113, 0.35);
}

.method-badge.grp {
  background: rgba(168, 85, 247, 0.16);
  color: #c084fc;
  border: 1px solid rgba(168, 85, 247, 0.35);
}

.api-node-labels {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}

.api-node-name {
  color: var(--text-main);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.api-node-path {
  color: var(--text-muted);
  font-size: 0.72rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.req-status-chip {
  font-size: 0.68rem;
  padding: 1px 5px;
  border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  flex-shrink: 0;
}

.req-status-chip.passed {
  color: var(--accent-green);
  background: rgba(52, 211, 153, 0.12);
}

.req-status-chip.warning {
  color: var(--accent-yellow);
  background: rgba(251, 191, 36, 0.14);
}

.req-status-chip.failed {
  color: var(--accent-red);
  background: rgba(248, 113, 113, 0.14);
}

.group-rollup {
  display: flex;
  gap: 4px;
  align-items: center;
}

.rollup-tag {
  font-size: 0.65rem;
  padding: 1px 5px;
  border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.rollup-tag.passed {
  color: var(--accent-green);
  background: rgba(52, 211, 153, 0.14);
}

.rollup-tag.warning {
  color: var(--accent-yellow);
  background: rgba(251, 191, 36, 0.16);
}

.rollup-tag.failed {
  color: var(--accent-red);
  background: rgba(248, 113, 113, 0.16);
}

.rollup-tag.count {
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.06);
}

.btn-delete-node {
  opacity: 0;
  background: transparent;
  color: var(--text-muted);
  font-size: 1rem;
  padding: 0 4px;
  transition: opacity 0.15s ease;
}

.api-node-row:hover .btn-delete-node {
  opacity: 1;
}

.btn-delete-node:hover {
  color: var(--accent-red);
}

.api-node-children {
  padding-left: 16px;
  margin-left: 8px;
  border-left: 1px dashed rgba(255, 255, 255, 0.12);
}
</style>
