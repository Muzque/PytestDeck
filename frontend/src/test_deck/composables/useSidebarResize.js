import { ref, onMounted } from 'vue'

const SIDEBAR_WIDTH_KEY = 'pytestdeck_sidebar_width'

export function useSidebarResize(defaultWidth = 480) {
  const sidebarWidth = ref(defaultWidth)
  const isResizing = ref(false)

  onMounted(() => {
    try {
      const savedWidth = localStorage.getItem(SIDEBAR_WIDTH_KEY)
      if (savedWidth) {
        const parsed = parseInt(savedWidth, 10)
        if (parsed >= 240 && parsed <= 1400) {
          sidebarWidth.value = parsed
        }
      }
    } catch {
      // Ignore storage read errors
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
    const maxAllowed = Math.min(1400, window.innerWidth - 250)
    const newWidth = Math.min(Math.max(e.clientX, 240), maxAllowed)
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
      // Ignore storage write errors
    }
  }

  return {
    sidebarWidth,
    isResizing,
    startResizing
  }
}
