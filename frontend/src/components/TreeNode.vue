<script setup>
import { ref, computed, watch } from 'vue'
import { useTooltip } from '../composables/useTooltip'

const props = defineProps({
  node: { type: Object, required: true },
  selectedNodes: { type: Set, required: true },
  methodOutputs: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['toggle-select'])

const { showTooltip, hideTooltip } = useTooltip()

const isOpen = ref(props.node.type !== 'file' && props.node.type !== 'fil')

watch(
  () => props.node.id,
  () => {
    isOpen.value = props.node.type !== 'file' && props.node.type !== 'fil'
  }
)

const isChecked = computed(() => {
  return props.selectedNodes.has(props.node.id)
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
  const outputs = props.methodOutputs || {}
  const id = props.node.id
  if (!id) return null

  if (outputs[id]) {
    return outputs[id]
  }

  for (const [key, val] of Object.entries(outputs)) {
    if ((id.endsWith(key) || key.endsWith(id)) && val) {
      return val
    }
  }
  return null
})

const nodeOutcome = computed(() => {
  return nodeRecord.value?.outcome ? nodeRecord.value.outcome.toLowerCase() : null
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
  if (num < 1.0) {
    return `${Math.round(num * 1000)}ms`
  }
  return `${num.toFixed(2)}s`
})

// Calculate aggregated outcomes for collapsed directories and files
const rollupCounts = computed(() => {
  if (!props.node.children || props.node.children.length === 0) {
    return { total: 0, passed: 0, failed: 0, skipped: 0, running: 0 }
  }

  const counts = { total: 0, passed: 0, failed: 0, skipped: 0, running: 0 }
  const outputs = props.methodOutputs || {}

  const traverse = (item) => {
    if (item.children && item.children.length > 0) {
      for (const child of item.children) {
        traverse(child)
      }
    } else {
      const id = item.id
      if (!id) return
      let rec = outputs[id]
      if (!rec) {
        for (const [k, v] of Object.entries(outputs)) {
          if ((id.endsWith(k) || k.endsWith(id)) && v) {
            rec = v
            break
          }
        }
      }
      if (rec?.outcome) {
        const out = rec.outcome.toLowerCase()
        if (out === 'passed') counts.passed++
        else if (out === 'failed' || out === 'error') counts.failed++
        else if (out === 'skipped') counts.skipped++
        else if (out === 'running') counts.running++
        counts.total++
      }
    }
  }

  traverse(props.node)
  return counts
})

const toggleOpen = () => {
  if (props.node.type === 'directory' || props.node.type === 'file' || props.node.type === 'class') {
    isOpen.value = !isOpen.value
  }
}

const onRowClick = () => {
  emit('toggle-select', props.node)
}

const onToggleClick = (e) => {
  e.stopPropagation()
  toggleOpen()
}

const onChildToggleSelect = (targetNode) => {
  emit('toggle-select', targetNode)
}
</script>

<template>
  <div class="tree-node">
    <div 
      class="node-row" 
      :class="[
        { 'is-selected': isChecked },
        nodeOutcome ? 'row-outcome-' + nodeOutcome : '',
        !isOpen && rollupCounts.failed > 0 ? 'row-has-failed' : '',
        !isOpen && rollupCounts.failed === 0 && rollupCounts.passed > 0 ? 'row-has-passed' : '',
        !isOpen && rollupCounts.failed === 0 && rollupCounts.passed === 0 && rollupCounts.skipped > 0 ? 'row-has-skipped' : ''
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
        {{ isOpen ? '▼' : '▶' }}
      </span>
      <span v-else class="icon-spacer"></span>

      <input 
        type="checkbox" 
        :checked="isChecked" 
        @click.stop
        @change="onRowClick"
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

      <!-- Right-aligned duration chip for test functions -->
      <span 
        v-if="formattedDuration" 
        class="node-duration" 
        :class="nodeOutcome ? 'outcome-' + nodeOutcome : ''"
        title="Execution duration"
      >
        {{ formattedDuration }}
      </span>

      <!-- Rollup badges when folder/file is collapsed -->
      <div 
        v-if="!isOpen && rollupCounts.total > 0" 
        class="node-rollup"
        :title="`${rollupCounts.passed} passed, ${rollupCounts.failed} failed, ${rollupCounts.skipped} skipped`"
      >
        <span v-if="rollupCounts.failed > 0" class="rollup-chip failed">
          {{ rollupCounts.failed }} ✗
        </span>
        <span v-if="rollupCounts.passed > 0" class="rollup-chip passed">
          {{ rollupCounts.passed }} ✓
        </span>
        <span v-if="rollupCounts.skipped > 0" class="rollup-chip skipped">
          {{ rollupCounts.skipped }} –
        </span>
      </div>
    </div>

    <div v-if="isOpen && node.children && node.children.length > 0" class="node-children">
      <TreeNode 
        v-for="child in node.children" 
        :key="child.id" 
        :node="child"
        :selectedNodes="selectedNodes"
        :methodOutputs="methodOutputs"
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

.node-row:hover {
  background: rgba(255, 255, 255, 0.08);
}
.node-row.is-selected {
  background: rgba(56, 189, 248, 0.15);
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

.node-row.row-outcome-skipped,
.node-row.row-has-skipped {
  border-left-color: var(--accent-yellow);
  background: rgba(251, 191, 36, 0.04);
}

.node-row.row-outcome-running {
  border-left-color: var(--accent-blue);
  background: rgba(56, 189, 248, 0.05);
}

.toggle-icon {
  font-size: 0.65rem;
  color: var(--text-muted);
  cursor: pointer;
  width: 14px;
}
.icon-spacer {
  width: 14px;
}
.node-checkbox {
  accent-color: var(--accent-blue);
  cursor: pointer;
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

.node-children {
  padding-left: 18px;
  border-left: 1px dashed rgba(255, 255, 255, 0.1);
  margin-left: 6px;
}
</style>
