<script setup>
import { ref, onMounted } from 'vue'
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

const SIDEBAR_WIDTH_KEY = 'pytestdeck_sidebar_width'
const sidebarWidth = ref(380)
const isResizing = ref(false)

onMounted(() => {
  const savedWidth = localStorage.getItem(SIDEBAR_WIDTH_KEY)
  if (savedWidth) {
    const parsed = parseInt(savedWidth, 10)
    if (parsed >= 240 && parsed <= 800) {
      sidebarWidth.value = parsed
    }
  }
})

const startResizing = () => {
  isResizing.value = true
  document.addEventListener('mousemove', handleMouseMove)
  document.addEventListener('mouseup', stopResizing)
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}

const handleMouseMove = (e) => {
  if (!isResizing.value) return
  const newWidth = Math.min(Math.max(e.clientX, 240), 800)
  sidebarWidth.value = newWidth
}

const stopResizing = () => {
  isResizing.value = false
  document.removeEventListener('mousemove', handleMouseMove)
  document.removeEventListener('mouseup', stopResizing)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  try {
    localStorage.setItem(SIDEBAR_WIDTH_KEY, sidebarWidth.value.toString())
  } catch {
    // Ignore storage errors in sandbox
  }
}
</script>

<template>
  <aside class="deck-sidebar" :style="{ width: sidebarWidth + 'px' }">
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

    <!-- Drag handle to adjust sidebar width -->
    <div 
      class="sidebar-resizer" 
      :class="{ 'is-active': isResizing }"
      @mousedown.prevent="startResizing"
      title="Drag to resize explorer sidebar"
    ></div>
  </aside>
</template>
