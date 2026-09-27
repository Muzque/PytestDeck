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
      selectionBackground: 'rgba(56, 189, 248, 0.3)'
    },
    fontSize: 13,
    fontFamily: 'Menlo, Monaco, "Courier New", monospace',
    convertEol: true,
    cursorBlink: true
  })
  
  fitAddon = new FitAddon()
  term.loadAddon(fitAddon)
  term.open(terminalContainer.value)
  fitAddon.fit()

  term.writeln('\x1b[1;34m=== PytestDeck Terminal Console ===\x1b[0m')

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

watch(() => props.logs.length, (newLength, oldLength) => {
  if (!term) return
  if (newLength === 0) {
    term.clear()
    term.writeln('\x1b[1;34m=== PytestDeck Terminal Console ===\x1b[0m')
    return
  }
  const addedLines = props.logs.slice(oldLength || 0)
  addedLines.forEach(line => term.write(line))
})
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
