<script setup>
import { defineProps, onMounted, onUnmounted, ref, watch } from 'vue'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import 'xterm/css/xterm.css'
import { TERMINAL_THEMES, useTheme } from '../composables/useTheme'

const props = defineProps({
  logs: { type: Array, default: () => [] },
  isRunning: { type: Boolean, default: false }
})

const { currentTerminalTheme, terminalThemes } = useTheme()

const terminalContainer = ref(null)
let term = null
let fitAddon = null
let resizeObserver = null
let currentLogsRef = null
let lastLogCount = 0
let hasSessionStarted = false
let preSessionBuffer = []

const isSessionStart = (line) => {
  if (typeof line !== 'string') return false
  return line.includes('test session starts') || line.trimStart().startsWith('Feature:')
}

const filterSessionLogs = (allLogs) => {
  if (!allLogs || allLogs.length === 0) return []
  const idx = allLogs.findIndex(isSessionStart)
  if (idx === -1) return allLogs
  if (allLogs[idx].includes('test session starts')) {
    return allLogs.slice(idx + 1)
  }
  return allLogs.slice(idx)
}

const copied = ref(false)

// eslint-disable-next-line no-control-regex
const ANSI_REGEX = /\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])/g

const stripAnsi = (str) => {
  if (!str) return ''
  return str.replace(ANSI_REGEX, '')
}

const copyOutput = async () => {
  const displayLogs = filterSessionLogs(props.logs)
  if (!displayLogs || displayLogs.length === 0) return
  const rawText = displayLogs.join('')
  const cleanText = stripAnsi(rawText)
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(cleanText)
    } else {
      const el = document.createElement('textarea')
      el.value = cleanText
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
    }
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy terminal output:', err)
  }
}

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
  preSessionBuffer = []
  const displayLogs = filterSessionLogs(allLogs)
  if (displayLogs && displayLogs.length > 0) {
    displayLogs.forEach(line => term.write(line))
  }
  lastLogCount = allLogs ? allLogs.length : 0
  hasSessionStarted = allLogs ? allLogs.some(isSessionStart) : false
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
    resetAndWriteAll(props.logs)
  } else {
    lastLogCount = 0
    hasSessionStarted = false
    preSessionBuffer = []
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

watch(() => props.isRunning, (running) => {
  if (!running && !hasSessionStarted && preSessionBuffer.length > 0) {
    preSessionBuffer.forEach(line => term.write(line))
    preSessionBuffer = []
  }
})

watch(() => props.logs, (newLogs) => {
  if (!term) return

  // If logs array was reset/cleared
  if (!newLogs || newLogs.length === 0) {
    currentLogsRef = newLogs
    hasSessionStarted = false
    preSessionBuffer = []
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
    lastLogCount = newLogs.length

    for (const line of appended) {
      if (!hasSessionStarted) {
        if (line.includes('= test session starts =')) {
          hasSessionStarted = true
          preSessionBuffer = []
        } else if (line.trimStart().startsWith('Feature:')) {
          hasSessionStarted = true
          preSessionBuffer = []
          term.write(line)
        } else {
          preSessionBuffer.push(line)
        }
      } else {
        term.write(line)
      }
    }
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
        <button
          class="btn-copy-terminal"
          :class="{ active: copied }"
          :disabled="!props.logs || props.logs.length === 0"
          @click="copyOutput"
          title="Copy all terminal output"
        >
          <span v-if="copied">✓ Copied</span>
          <span v-else>📋 Copy Output</span>
        </button>
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

.terminal-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-copy-terminal {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.78rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-copy-terminal:hover:not(:disabled) {
  background: var(--bg-hover);
  border-color: var(--border-hover);
  color: #fff;
}

.btn-copy-terminal:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.btn-copy-terminal.active {
  background: rgba(39, 201, 63, 0.15);
  border-color: #27c93f;
  color: #27c93f;
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
