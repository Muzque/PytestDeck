<script setup>
import TreeNode from './TreeNode.vue'

defineProps({
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
</script>

<template>
  <aside class="deck-sidebar">
    <div class="sidebar-header">
      <h3>Test Explorer</h3>
      <span class="suite-tag">{{ activeSuite }}</span>
    </div>

    <div class="filter-box">
      <input 
        :value="markerFilter" 
        placeholder="Marker (e.g. -m smoke)" 
        class="filter-input"
        @input="emit('update:markerFilter', $event.target.value)"
      />
      <input 
        :value="extraArgs" 
        placeholder="Extra flags (e.g. -v --tb=short)" 
        class="filter-input"
        @input="emit('update:extraArgs', $event.target.value)"
      />
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
  </aside>
</template>
