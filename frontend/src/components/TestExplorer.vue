<script setup>
import { ref, computed } from 'vue'
import TreeNode from './TreeNode.vue'
import RunOptionsModal from './RunOptionsModal.vue'

const props = defineProps({
  activeSuite: { type: String, required: true },
  markerFilter: { type: String, default: '' },
  extraArgs: { type: String, default: '' },
  testTree: { type: Object, default: null },
  selectedNodes: { type: Object, required: true }
})

const emit = defineEmits([
  'update:markerFilter',
  'update:extraArgs',
  'toggle-select'
])

const showRunOptions = ref(false)

const activeOptionCount = computed(() =>
  (props.markerFilter ? 1 : 0) + (props.extraArgs ? 1 : 0)
)
</script>

<template>
  <div class="explorer-section">
    <div class="sidebar-header">
      <h3>Test Explorer</h3>
      <span class="suite-tag">{{ activeSuite }}</span>
    </div>

    <div class="filter-box">
      <button
        id="btn-run-options"
        class="btn-run-options"
        :class="{ 'has-options': activeOptionCount > 0 }"
        title="Configure marker expression and extra flags"
        @click="showRunOptions = true"
      >
        <span>⚙️ Run Options</span>
        <span v-if="activeOptionCount" class="run-options-count">{{ activeOptionCount }}</span>
      </button>

      <div v-if="activeOptionCount" class="run-options-summary">
        <code v-if="markerFilter" :title="markerFilter">-m {{ markerFilter }}</code>
        <code v-if="extraArgs" :title="extraArgs">{{ extraArgs }}</code>
      </div>
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
