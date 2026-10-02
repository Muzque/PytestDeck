<script setup>
import { ref, computed } from 'vue'

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
    <div class="node-row" :class="{ 'is-selected': isChecked }" @click="onRowClick">
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

      <span class="node-name" :title="node.id">{{ node.name }}</span>
    </div>


    <div v-if="isOpen && node.children && node.children.length > 0" class="node-children">
      <TreeNode 
        v-for="child in node.children" 
        :key="child.id" 
        :node="child"
        :selectedNodes="selectedNodes"
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
  border-radius: 4px;
  cursor: pointer;
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
  font-size: 0.62rem;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  letter-spacing: 0.05em;
  background: var(--bg-input);
  color: var(--text-muted);
  border: 1px solid var(--border-color);
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
  overflow: hidden;
  text-overflow: ellipsis;
}
.node-children {
  padding-left: 18px;
  border-left: 1px dashed rgba(255, 255, 255, 0.1);
  margin-left: 6px;
}
</style>
