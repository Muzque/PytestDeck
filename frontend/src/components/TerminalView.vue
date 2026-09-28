<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import 'xterm/css/xterm.css'

const props = defineProps({
  logs: { type: Array, default: () => [] }
})

const terminalContainer = ref(null)
let term = null
let fitAddon = null

onMounted(() => {
  term = new Terminal({
    theme: {
      background: '#090d16',
      foreground: '#e2e8f0',
      cursor: '#38bdf8',
      selectionBackground: 'rgba(56, 189, 248, 0.3)',
      black: '#1e222a',
      red: '#f87171',
      green: '#4ade80',
      yellow: '#facc15',
      blue: '#60a5fa',
      magenta: '#c084fc',
      cyan: '#38bdf8',
      white: '#f1f5f9',
      brightBlack: '#475569',
      brightRed: '#ef4444',
      brightGreen: '#22c55e',
      brightYellow: '#eab308',
      brightBlue: '#3b82f6',
      brightMagenta: '#a855f7',
      brightCyan: '#06b6d4',
      brightWhite: '#ffffff'
    },
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


</script>

<template>
  <div class="terminal-wrapper">
    <div ref="terminalContainer" class="terminal-container"></div>
  </div>
</template>

<style scoped>
.terminal-wrapper {
  width: 100%;
  height: 100%;
  background: #090d16;
  border-radius: 6px;
  padding: 8px;
  box-sizing: border-box;
}
.terminal-container {
  width: 100%;
  height: 100%;
}
</style>
