<script setup>
defineProps({
  summary: { type: Object, default: null },
  exitCode: { type: Number, default: null }
})
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
        <div class="value">{{ summary.report.summary?.total || 0 }}</div>
      </div>
      <div v-if="summary.report" class="card card-pass">
        <h4>Passed</h4>
        <div class="value pass">{{ summary.report.summary?.passed || 0 }}</div>
      </div>
      <div v-if="summary.report" class="card card-fail">
        <h4>Failed</h4>
        <div class="value fail">{{ summary.report.summary?.failed || 0 }}</div>
      </div>
    </div>
    <div v-else class="no-summary">
      Run tests to view execution summary report.
    </div>
  </div>
</template>
