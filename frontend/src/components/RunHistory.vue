<script setup>
defineProps({
  runHistory: { type: Array, required: true },
  selectedHistoryId: { type: Number, default: null }
})

const emit = defineEmits(['select-history'])

// eslint-disable-next-line no-control-regex
const ANSI_REGEX = /\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])/g

const extractDurationSeconds = (item) => {
  const reportDuration = item?.summary?.report?.duration
  if (reportDuration !== null && reportDuration !== undefined) {
    const num = Number(reportDuration)
    if (!Number.isNaN(num) && num >= 0) {
      return num
    }
  }

  if (Array.isArray(item?.logs) && item.logs.length > 0) {
    const tail = item.logs.slice(-20).join('').replace(ANSI_REGEX, '')
    const match = tail.match(/Took\s+(\d+)min\s+([\d.]+)s/)
    if (match) {
      const mins = Number(match[1])
      const secs = Number(match[2])
      if (!Number.isNaN(mins) && !Number.isNaN(secs)) {
        return mins * 60 + secs
      }
    }
  }

  return null
}

const formatRunDuration = (item) => {
  const d = extractDurationSeconds(item)
  if (d === null || d === undefined) return null
  const num = Number(d)
  if (Number.isNaN(num)) return null
  if (num < 0.001) {
    return '<1ms'
  }
  if (num < 1.0) {
    return `${Math.round(num * 1000)}ms`
  }
  return `${num.toFixed(2)}s`
}
</script>

<template>
  <div class="history-wrapper">
    <div v-if="runHistory.length > 0" class="history-list">
      <div 
        v-for="item in runHistory" 
        :key="item.id" 
        class="history-item"
        :class="{ active: item.id === selectedHistoryId }"
        @click="emit('select-history', item)"
      >
        <div class="history-header">
          <span class="history-time">{{ item.timestamp }}</span>
          <span class="history-suite">{{ item.suite }}</span>
          <span v-if="formatRunDuration(item)" class="history-duration">{{ formatRunDuration(item) }}</span>
          <span class="history-status" :class="{ pass: item.exitCode === 0, fail: item.exitCode !== 0 }">
            {{ item.exitCode === 0 ? 'PASSED' : 'FAILED' }}
          </span>
        </div>
        <div v-if="item.summary?.report?.summary" class="history-details">
          <span>Passed: {{ item.summary.report.summary.passed || 0 }}</span> |
          <span>Failed: {{ item.summary.report.summary.failed || 0 }}</span>
        </div>
      </div>
    </div>
    <div v-else class="no-summary">
      No execution history recorded yet. Run a test suite to populate history log.
    </div>
  </div>
</template>

