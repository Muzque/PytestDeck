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

const applyTerminalTheme = (themeId) => {
  if (!term) return
  const themeObj = TERMINAL_THEMES[themeId] || TERMINAL_THEMES['apple-dark']
  term.options.theme = themeObj.options
}

onMounted(() => {
  const initialTheme = TERMINAL_THEMES[currentTerminalTheme.value] || TERMINAL_THEMES['apple-dark']

  term = new Terminal({
    theme: initialTheme.options,
    fontSize: 13,
    fontFamily: 'Fira Code, Menlo, Monaco, "Courier New", monospace',
    convertEol: true,
    cursorBlink: true
  })
  
  fitAddon = new FitAddon()
  term.loadAddon(fitAddon)
  term.open(terminalContainer.value)
  fitAddon.fit()

  props.logs.forEach(line => term.write(line))

  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (term) term.dispose()
})

const handleResize = () => {
  if (fitAddon) fitAddon.fit()
}

let lastLogCount = props.logs.length

watch(() => props.logs, (newLogs) => {
  if (!term) return

  // If logs array was reset/cleared or replaced (e.g. starting a run or selecting history)
  if (!newLogs || newLogs.length === 0 || newLogs.length < lastLogCount) {
    term.clear()
    if (newLogs && newLogs.length > 0) {
      newLogs.forEach(line => term.write(line))
    }
    lastLogCount = newLogs ? newLogs.length : 0
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
  padding: 8px;
  box-sizing: border-box;
}
</style>
