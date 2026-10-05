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
  isRunning: { type: Boolean, default: false },
  isDiscovering: { type: Boolean, default: false }
})

const emit = defineEmits([
  'update:markerFilter',
  'update:extraArgs',
  'toggle-select',
  'discover',
  'run',
  'stop'
])

const showRunOptions = ref(false)

const activeOptionCount = computed(() =>
  (props.markerFilter ? 1 : 0) + (props.extraArgs ? 1 : 0)
)
</script>

<template>
  <div class="explorer-section">
    <!-- Unified Action Toolbar: Run Selected, Refresh, and Run Options -->
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

    <div v-if="testTree" class="tree-container">
      <TreeNode 
        :node="testTree" 
        :selectedNodes="selectedNodes"
        @toggle-select="emit('toggle-select', $event)"
      />
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
      @close="showRunOptions = false"
    />
  </div>
</template>
