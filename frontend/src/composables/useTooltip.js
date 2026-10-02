import { ref } from 'vue'

const activeTooltip = ref({
  name: '',
  id: '',
  type: '',
  x: 0,
  y: 0,
  visible: false
})

export function useTooltip() {
  const showTooltip = (node, event) => {
    if (!node || !node.name) return
    const rect = event.currentTarget.getBoundingClientRect()
    // Position tooltip below the hovered item
    activeTooltip.value = {
      name: node.name,
      id: node.id || node.name,
      type: node.type || '',
      x: Math.min(rect.left, window.innerWidth - 320),
      y: Math.min(rect.bottom + 6, window.innerHeight - 80),
      visible: true
    }
  }

  const hideTooltip = () => {
    activeTooltip.value.visible = false
  }

  return {
    activeTooltip,
    showTooltip,
    hideTooltip
  }
}
