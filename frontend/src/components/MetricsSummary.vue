<script setup>
import { computed } from 'vue'

const props = defineProps({
  summary: { type: Object, default: null },
  exitCode: { type: Number, default: null }
})

const reportSummary = computed(() => props.summary?.report?.summary || null)
const totalCount = computed(() => reportSummary.value?.total || 0)
const passedCount = computed(
  () => (reportSummary.value?.passed || 0) + (reportSummary.value?.xpassed || 0)
)
const failedCount = computed(
  () => (reportSummary.value?.failed || 0) + (reportSummary.value?.error || 0)
)
const skippedCount = computed(
  () => (reportSummary.value?.skipped || 0) + (reportSummary.value?.xfailed || 0)
)
</script>

<template>
  <div class="summary-wrapper">
    <div v-if="summary" class="summary-cards">
      <div class="card card-exit">
        <h4>Exit Code</h4>
        <div class="value" :class="{ pass: exitCode === 0, fail: exitCode !== 0 }">
          {{ exitCode }}
        </div>
      </div>
      <div v-if="summary.report" class="card card-total">
        <h4>Total Tests</h4>
        <div class="value">{{ totalCount }}</div>
      </div>
      <div v-if="summary.report" class="card card-pass">
        <h4>Passed</h4>
        <div class="value pass">{{ passedCount }}</div>
      </div>
      <div v-if="summary.report" class="card card-fail">
        <h4>Failed</h4>
        <div class="value fail">{{ failedCount }}</div>
      </div>
      <div v-if="summary.report" class="card card-skip">
        <h4>Skipped</h4>
        <div class="value skip">{{ skippedCount }}</div>
      </div>
    </div>
    <div v-else class="no-summary">
      Run tests to view execution summary report.
    </div>
  </div>
</template>
