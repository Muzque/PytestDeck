<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import 'xterm/css/xterm.css'
import { useTheme, TERMINAL_THEMES } from '../composables/useTheme'

const props = defineProps({
  logs: { type: Array, default: () => [] }
})

const { currentTerminalTheme, terminalThemes } = useTheme()

const terminalContainer = ref(null)
let term = null
let fitAddon = null
let resizeObserver = null
let currentLogsRef = null
let lastLogCount = 0

const applyTerminalTheme = (themeId) => {
  if (!term) return
  const themeObj = TERMINAL_THEMES[themeId] || TERMINAL_THEMES['apple-dark']
  term.options.theme = themeObj.options
}

const handleResize = () => {
  if (fitAddon && terminalContainer.value && terminalContainer.value.clientWidth > 0) {
    try {
      fitAddon.fit()
    } catch {
      // Ignore fit errors if element dimensions are transiently zero
    }
  }
}

const resetAndWriteAll = (allLogs) => {
  if (!term) return
  term.clear()
  if (allLogs && allLogs.length > 0) {
    allLogs.forEach(line => term.write(line))
    lastLogCount = allLogs.length
  } else {
    lastLogCount = 0
  }
  term.scrollToBottom()
}

onMounted(() => {
  const initialTheme = TERMINAL_THEMES[currentTerminalTheme.value] || TERMINAL_THEMES['apple-dark']

  term = new Terminal({
    theme: initialTheme.options,
    fontSize: 13,
    fontFamily: 'Fira Code, Menlo, Monaco, "Courier New", monospace',
    convertEol: true,
    cursorBlink: true,
    scrollback: 50000
  })
  
  fitAddon = new FitAddon()
  term.loadAddon(fitAddon)
  term.open(terminalContainer.value)
  handleResize()

  currentLogsRef = props.logs
  if (props.logs && props.logs.length > 0) {
    props.logs.forEach(line => term.write(line))
    lastLogCount = props.logs.length
  } else {
    lastLogCount = 0
  }

  resizeObserver = new ResizeObserver(() => {
    handleResize()
  })
  if (terminalContainer.value) {
    resizeObserver.observe(terminalContainer.value)
  }

  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
  window.removeEventListener('resize', handleResize)
  if (term) term.dispose()
})

watch(() => props.logs, (newLogs) => {
  if (!term) return

  // If logs array was reset/cleared
  if (!newLogs || newLogs.length === 0) {
    currentLogsRef = newLogs
    resetAndWriteAll([])
    return
  }

  // If logs array was replaced (e.g. starting a run or selecting history item)
  if (newLogs !== currentLogsRef) {
    currentLogsRef = newLogs
    resetAndWriteAll(newLogs)
    return
  }

  // If logs array was trimmed in place
  if (newLogs.length < lastLogCount) {
    resetAndWriteAll(newLogs)
    return
  }

  // If new log lines were appended during streaming
  if (newLogs.length > lastLogCount) {
    const appended = newLogs.slice(lastLogCount)
    appended.forEach(line => term.write(line))
    lastLogCount = newLogs.length
  }
}, { deep: true })

watch(currentTerminalTheme, (newThemeId) => {
  applyTerminalTheme(newThemeId)
})
</script>

<template>
  <div class="terminal-wrapper" :data-term-theme="currentTerminalTheme">
    <div class="terminal-toolbar">
      <div class="terminal-dots">
        <span class="dot dot-red"></span>
        <span class="dot dot-yellow"></span>
        <span class="dot dot-green"></span>
        <span class="terminal-title">Terminal Output</span>
      </div>
      <div class="terminal-actions">
        <select v-model="currentTerminalTheme" class="term-theme-select" title="Terminal Color Theme">
          <option v-for="tt in terminalThemes" :key="tt.id" :value="tt.id">
            {{ tt.label }}
          </option>
        </select>
      </div>
    </div>
    <div ref="terminalContainer" class="terminal-container"></div>
  </div>
</template>

<style scoped>
.terminal-wrapper {
  width: 100%;
  height: 100%;
  background: var(--bg-card);
  backdrop-filter: var(--glass-backdrop);
  -webkit-backdrop-filter: var(--glass-backdrop);
  border-radius: var(--glass-border-radius);
  border: 1px solid var(--border-color);
  box-shadow: var(--glass-shadow);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.terminal-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
}

.terminal-dots {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.dot-red { background: #ff5f56; }
.dot-yellow { background: #ffbd2e; }
.dot-green { background: #27c93f; }

.terminal-title {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-muted);
  margin-left: 6px;
}

.term-theme-select {
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.78rem;
  cursor: pointer;
}

.term-theme-select:hover {
  border-color: var(--border-hover);
}

.terminal-container {
  flex: 1;
  width: 100%;
  min-height: 0;
  min-width: 0;
  padding: 8px;
  box-sizing: border-box;
  overflow: hidden;
  position: relative;
}
</style>
