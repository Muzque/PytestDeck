<script setup>
import { ref, watch, computed } from 'vue'

const props = defineProps({
  node: { type: Object, required: true },
  selectedNodes: { type: Set, required: true }
})

const emit = defineEmits(['toggle-select'])

const isOpen = ref(true)

const isChecked = computed(() => {
  return props.selectedNodes.has(props.node.id)
})

const toggleOpen = () => {
  if (props.node.type === 'directory' || props.node.type === 'file' || props.node.type === 'class') {
    isOpen.value = !isOpen.value
  }
}

const onCheckboxChange = () => {
  emit('toggle-select', props.node)
}
</script>

<template>
  <div class="tree-node">
    <div class="node-row" :class="{ 'is-selected': isChecked }">
      <span 
        class="toggle-icon" 
        @click="toggleOpen"
        v-if="node.children && node.children.length > 0"
      >
        {{ isOpen ? '▼' : '▶' }}
      </span>
      <span v-else class="icon-spacer"></span>

      <input 
        type="checkbox" 
        :checked="isChecked" 
        @change="onCheckboxChange"
        class="node-checkbox"
      />

      <span class="type-badge" :class="node.type">
        {{ node.type.substring(0, 3).toUpperCase() }}
      </span>

      <span class="node-name" :title="node.id">{{ node.name }}</span>
    </div>

    <div v-if="isOpen && node.children && node.children.length > 0" class="node-children">
      <TreeNode 
        v-for="child in node.children" 
        :key="child.id" 
        :node="child"
        :selectedNodes="selectedNodes"
        @toggle-select="$emit('toggle-select', $event)"
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
  border-radius: 4px;
  transition: background 0.15s ease;
}
.node-row:hover {
  background: rgba(255, 255, 255, 0.05);
}
.node-row.is-selected {
  background: rgba(56, 189, 248, 0.12);
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
  font-size: 0.65rem;
  font-weight: 700;
  padding: 1px 4px;
  border-radius: 3px;
  background: #334155;
  color: #94a3b8;
}
.type-badge.dir { background: #1e293b; color: #38bdf8; }
.type-badge.fil { background: #334155; color: #a7f3d0; }
.type-badge.fun { background: #475569; color: #fef08a; }
.node-name {
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.node-children {
  padding-left: 18px;
  border-left: 1px dashed rgba(255, 255, 255, 0.1);
  margin-left: 6px;
}
</style>
