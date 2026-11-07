<script setup>
import { ref, computed, watch } from 'vue'
import { useTooltip } from '../composables/useTooltip'
import { findNodeRecord } from '../composables/nodeLookup'

const props = defineProps({
  node: { type: Object, required: true },
  selectedNodes: { type: Set, required: true },
  methodOutputs: { type: Object, default: () => ({}) },
  isRunning: { type: Boolean, default: false },
  forceExpand: { type: Boolean, default: false }
})

const emit = defineEmits(['toggle-select'])

const { showTooltip, hideTooltip } = useTooltip()

const isOpen = ref(props.node.type !== 'file' && props.node.type !== 'fil')
const effectiveIsOpen = computed(() => props.forceExpand || isOpen.value)

watch(
  () => props.node.id,
  () => {
    isOpen.value = props.node.type !== 'file' && props.node.type !== 'fil'
  }
)

const isChecked = computed(() => {
  if (props.selectedNodes.has(props.node.id)) return true
  if (props.node.children && props.node.children.length > 0) {
    const checkAllLeaves = (n) => {
      if (n.children && n.children.length > 0) {
        return n.children.every(checkAllLeaves)
      }
      return Boolean(n.id && props.selectedNodes.has(n.id))
    }
    return checkAllLeaves(props.node)
  }
  return false
})

const isFunctionNode = computed(() => {
  return (
    props.node.type === 'function' ||
    props.node.type === 'fun' ||
    props.node.type === 'scenario' ||
    (props.node.id && props.node.id.includes('::') && (!props.node.children || props.node.children.length === 0))
  )
})

const nodeRecord = computed(() => {
  if (!isFunctionNode.value) return null
  return findNodeRecord(props.methodOutputs || {}, props.node.id)
})

const normalizeOutcome = (raw) => {
  if (!raw) return null
  const lower = raw.toLowerCase()
  if (lower === 'xfailed' || lower === 'xfail') return 'skipped'
  if (lower === 'xpassed' || lower === 'xpass') return 'passed'
  return lower
}

const nodeOutcome = computed(() => {
  return normalizeOutcome(nodeRecord.value?.outcome)
})

const outcomeTitle = computed(() => {
  if (!nodeOutcome.value) return ''
  return `Result: ${nodeOutcome.value}`
})

const formattedDuration = computed(() => {
  const d = nodeRecord.value?.duration
  if (d === null || d === undefined) return null
  const num = Number(d)
  if (isNaN(num)) return null
  if (num < 0.001) {
    return '<1ms'
  }
  if (num < 1.0) {
    return `${Math.round(num * 1000)}ms`
  }
  return `${num.toFixed(2)}s`
})

// Calculate aggregated outcomes for parent nodes (directories, files, and classes)
const rollupCounts = computed(() => {
  if (!props.node.children || props.node.children.length === 0) {
    return { total: 0, passed: 0, failed: 0, skipped: 0, notRun: 0, running: 0 }
  }

  const counts = { total: 0, passed: 0, failed: 0, skipped: 0, notRun: 0, running: 0 }
  const outputs = props.methodOutputs || {}

  const traverse = (item) => {
    if (item.children && item.children.length > 0) {
      for (const child of item.children) {
        traverse(child)
      }
    } else {
      const id = item.id
      if (!id) return
      counts.total++
      const rec = findNodeRecord(outputs, id)
      const out = normalizeOutcome(rec?.outcome)
      if (out === 'passed') counts.passed++
      else if (out === 'failed' || out === 'error') counts.failed++
      else if (out === 'skipped') counts.skipped++
      else if (out === 'running') counts.running++
      else counts.notRun++
    }
  }

  traverse(props.node)
  return counts
})

const hasChildren = computed(() => Boolean(props.node.children && props.node.children.length > 0))

const toggleOpen = () => {
  if (
    hasChildren.value ||
    props.node.type === 'directory' ||
    props.node.type === 'dir' ||
    props.node.type === 'file' ||
    props.node.type === 'fil' ||
    props.node.type === 'class' ||
    props.node.type === 'cls'
  ) {
    isOpen.value = !isOpen.value
  }
}

const onCheckboxChange = () => {
  if (props.isRunning) return
  emit('toggle-select', props.node)
}

const onRowClick = () => {
  if (hasChildren.value) {
    toggleOpen()
    return
  }
  if (props.isRunning) return
  emit('toggle-select', props.node)
}

const onToggleClick = (e) => {
  e.stopPropagation()
  toggleOpen()
}

const onChildToggleSelect = (targetNode) => {
  if (props.isRunning) return
  emit('toggle-select', targetNode)
}
</script>

<template>
  <div class="tree-node">
    <div 
      class="node-row" 
      :class="[
        { 'is-selected': isChecked, 'is-running-locked': isRunning },
        nodeOutcome ? 'row-outcome-' + nodeOutcome : '',
        rollupCounts.running > 0 ? 'row-has-running' : '',
        rollupCounts.running === 0 && rollupCounts.failed > 0 ? 'row-has-failed' : '',
        rollupCounts.running === 0 && rollupCounts.failed === 0 && rollupCounts.notRun > 0 ? 'row-has-not-run' : '',
        rollupCounts.running === 0 && rollupCounts.failed === 0 && rollupCounts.notRun === 0 && rollupCounts.passed > 0 ? 'row-has-passed' : ''
      ]" 
      @click="onRowClick"
      @mouseenter="showTooltip(node, $event)"
      @mouseleave="hideTooltip"
    >
      <span 
        class="toggle-icon" 
        @click="onToggleClick"
        v-if="node.children && node.children.length > 0"
      >
        {{ effectiveIsOpen ? '▼' : '▶' }}
      </span>
      <span v-else class="icon-spacer"></span>

      <input 
        type="checkbox" 
        :checked="isChecked" 
        :disabled="isRunning"
        @click.stop
        @change="onCheckboxChange"
        class="node-checkbox"
      />

      <span class="type-badge" :class="node.type">
        {{ node.type.substring(0, 3).toUpperCase() }}
      </span>

      <span 
        class="node-name" 
        :title="outcomeTitle"
      >
        {{ node.name }}
      </span>

      <!-- Right-aligned duration or running chip for test functions -->
      <span 
        v-if="nodeOutcome === 'running'" 
        class="node-duration outcome-running" 
        title="Test is currently executing"
      >
        ⏳ Running
      </span>
      <span 
        v-else-if="formattedDuration" 
        class="node-duration" 
        :class="nodeOutcome ? 'outcome-' + nodeOutcome : ''"
        title="Execution duration"
      >
        {{ formattedDuration }}
      </span>
      <span 
        v-else-if="nodeOutcome" 
        class="node-duration" 
        :class="'outcome-' + nodeOutcome"
        :title="outcomeTitle"
      >
        {{ nodeOutcome === 'passed' ? '✓' : (nodeOutcome === 'failed' || nodeOutcome === 'error' ? '✗' : '–') }}
      </span>

      <!-- Rollup badges on parent nodes (directories, files, and classes) whether expanded or collapsed -->
      <div 
        v-if="rollupCounts.total > 0" 
        class="node-rollup"
        :title="`${rollupCounts.running ? rollupCounts.running + ' running, ' : ''}${rollupCounts.passed} passed, ${rollupCounts.failed} failed, ${rollupCounts.skipped} skipped, ${rollupCounts.notRun} not-run`"
      >
        <span v-if="rollupCounts.running > 0" class="rollup-chip running">
          {{ rollupCounts.running }} ⏳
        </span>
        <span v-if="rollupCounts.failed > 0" class="rollup-chip failed">
          {{ rollupCounts.failed }} ✗
        </span>
        <span v-if="rollupCounts.passed > 0" class="rollup-chip passed">
          {{ rollupCounts.passed }} ✓
        </span>
        <span v-if="rollupCounts.skipped > 0" class="rollup-chip skipped">
          {{ rollupCounts.skipped }} –
        </span>
        <span v-if="rollupCounts.notRun > 0" class="rollup-chip not-run">
          {{ rollupCounts.notRun }} ○
        </span>
      </div>
    </div>

    <div v-if="effectiveIsOpen && node.children && node.children.length > 0" class="node-children">
      <TreeNode 
        v-for="child in node.children" 
        :key="child.id" 
        :node="child"
        :selectedNodes="selectedNodes"
        :methodOutputs="methodOutputs"
        :isRunning="isRunning"
        :forceExpand="forceExpand"
        @toggle-select="onChildToggleSelect"
      />
    </div>
  </div>
</template>

<style scoped>
.tree-node {
  user-select: none;
  font-size: 0.88rem;
}
.node-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
  min-width: max-content;
  border-left: 3px solid transparent;
}
.node-row.is-running-locked {
  cursor: default;
}

.node-row:hover {
  background: rgba(255, 255, 255, 0.08);
}

/* Left-edge status stripe */
.node-row.row-outcome-passed,
.node-row.row-has-passed {
  border-left-color: var(--accent-green);
  background: rgba(52, 211, 153, 0.04);
}

.node-row.row-outcome-failed,
.node-row.row-outcome-error,
.node-row.row-has-failed {
  border-left-color: var(--accent-red);
  background: rgba(248, 113, 113, 0.06);
}

.node-row.row-outcome-skipped {
  border-left-color: var(--accent-yellow);
  background: rgba(251, 191, 36, 0.04);
}

.node-row.row-has-not-run {
  border-left-color: var(--text-muted);
  background: rgba(148, 163, 184, 0.06);
}

.node-row.is-selected {
  background: rgba(56, 189, 248, 0.15);
}

.node-row.row-outcome-running,
.node-row.row-has-running {
  border-left-color: var(--accent-blue);
  background: rgba(56, 189, 248, 0.10);
}

.node-row.is-selected.row-outcome-running,
.node-row.is-selected.row-has-running {
  background: rgba(56, 189, 248, 0.20);
}

.toggle-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  font-size: 0.85rem;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: 5px;
  flex-shrink: 0;
  transition: background 0.15s ease, color 0.15s ease;
}
.toggle-icon:hover {
  background: rgba(255, 255, 255, 0.12);
  color: var(--text-main);
}
.icon-spacer {
  display: inline-block;
  width: 24px;
  height: 24px;
  flex-shrink: 0;
}
.node-checkbox {
  accent-color: var(--accent-blue);
  cursor: pointer;
}
.node-checkbox:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
.type-badge {
  font-size: 0.62rem;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  letter-spacing: 0.05em;
  background: var(--bg-input);
  color: var(--text-muted);
  border: 1px solid var(--border-color);
  flex-shrink: 0;
}
.type-badge.directory, .type-badge.dir {
  background: rgba(56, 189, 248, 0.15);
  color: var(--accent-blue);
  border: 1px solid rgba(56, 189, 248, 0.3);
}
.type-badge.file, .type-badge.fil {
  background: rgba(52, 211, 153, 0.15);
  color: var(--accent-green);
  border: 1px solid rgba(52, 211, 153, 0.3);
}
.type-badge.class, .type-badge.cls {
  background: rgba(168, 85, 247, 0.15);
  color: #c084fc;
  border: 1px solid rgba(168, 85, 247, 0.3);
}
.type-badge.function, .type-badge.fun {
  background: rgba(251, 191, 36, 0.15);
  color: var(--accent-yellow);
  border: 1px solid rgba(251, 191, 36, 0.3);
}

.node-name {
  color: var(--text-main);
  white-space: nowrap;
}

/* Right-aligned duration chip */
.node-duration {
  margin-left: auto;
  font-size: 0.70rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  padding: 1px 5px;
  border-radius: 4px;
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  flex-shrink: 0;
  letter-spacing: 0.02em;
}

.node-duration.outcome-passed {
  color: var(--accent-green);
  background: rgba(52, 211, 153, 0.10);
  border-color: rgba(52, 211, 153, 0.25);
}

.node-duration.outcome-failed,
.node-duration.outcome-error {
  color: var(--accent-red);
  background: rgba(248, 113, 113, 0.12);
  border-color: rgba(248, 113, 113, 0.3);
}

.node-duration.outcome-skipped {
  color: var(--accent-yellow);
  background: rgba(251, 191, 36, 0.10);
  border-color: rgba(251, 191, 36, 0.25);
}

.node-duration.outcome-running {
  color: var(--accent-blue);
  background: rgba(56, 189, 248, 0.18);
  border-color: rgba(56, 189, 248, 0.45);
  font-weight: 600;
}

/* Rollup chips on collapsed folders/files */
.node-rollup {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.rollup-chip {
  font-size: 0.65rem;
  font-weight: 600;
  padding: 1px 5px;
  border-radius: 4px;
  letter-spacing: 0.02em;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.rollup-chip.passed {
  background: rgba(52, 211, 153, 0.15);
  color: var(--accent-green);
  border: 1px solid rgba(52, 211, 153, 0.35);
}

.rollup-chip.failed {
  background: rgba(248, 113, 113, 0.18);
  color: var(--accent-red);
  border: 1px solid rgba(248, 113, 113, 0.45);
}

.rollup-chip.skipped {
  background: rgba(251, 191, 36, 0.15);
  color: var(--accent-yellow);
  border: 1px solid rgba(251, 191, 36, 0.35);
}

.rollup-chip.not-run {
  background: rgba(148, 163, 184, 0.15);
  color: var(--text-muted);
  border: 1px solid rgba(148, 163, 184, 0.35);
}

.rollup-chip.running {
  background: rgba(56, 189, 248, 0.20);
  color: var(--accent-blue);
  border: 1px solid rgba(56, 189, 248, 0.45);
}

.node-children {
  padding-left: 18px;
  border-left: 1px dashed rgba(255, 255, 255, 0.1);
  margin-left: 6px;
}
</style>
