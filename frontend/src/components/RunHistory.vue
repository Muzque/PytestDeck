<script setup>
defineProps({
  runHistory: { type: Array, required: true },
  selectedHistoryId: { type: Number, default: null }
})

const emit = defineEmits(['select-history'])
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
