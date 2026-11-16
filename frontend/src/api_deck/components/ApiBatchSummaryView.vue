<script setup>
defineProps({
  batchSummary: { type: Object, default: null },
  isRunningBatch: { type: Boolean, default: false }
})

const emit = defineEmits(['inspect-result'])
</script>

<template>
  <div class="batch-summary-view">
    <div v-if="isRunningBatch" class="batch-loading">
      ⏳ Running selected APIs and groups...
    </div>

    <template v-else-if="batchSummary">
      <div class="batch-kpi-row" data-testid="api-batch-summary">
        <div class="batch-kpi">
          <span class="bk-label">Total APIs Run</span>
          <span class="bk-val" data-testid="batch-total-count">{{ batchSummary.total }}</span>
        </div>
        <div class="batch-kpi">
          <span class="bk-label">Passed</span>
          <span class="bk-val passed" data-testid="batch-passed-count">{{ batchSummary.passed }}</span>
        </div>
        <div class="batch-kpi">
          <span class="bk-label">Failed</span>
          <span class="bk-val failed" data-testid="batch-failed-count">{{ batchSummary.failed }}</span>
        </div>
        <div class="batch-kpi">
          <span class="bk-label">Avg Latency</span>
          <span class="bk-val">{{ batchSummary.avg_ms }} ms</span>
        </div>
        <div class="batch-kpi">
          <span class="bk-label">Total Wall Time</span>
          <span class="bk-val">{{ batchSummary.total_ms }} ms</span>
        </div>
      </div>

      <div class="batch-table-card">
        <table class="batch-results-table">
          <thead>
            <tr>
              <th>Outcome</th>
              <th>Method</th>
              <th>API Name</th>
              <th>URL</th>
              <th>Status</th>
              <th>Duration</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in batchSummary.results"
              :key="item.node_id"
              class="batch-row"
              @click="emit('inspect-result', item)"
            >
              <td>
                <span class="outcome-pill" :class="item.outcome">
                  {{ item.outcome === 'passed' ? '✓ PASS' : '✗ FAIL' }}
                </span>
              </td>
              <td>
                <span class="method-pill">{{ item.method }}</span>
              </td>
              <td class="td-name">{{ item.name }}</td>
              <td class="td-url">{{ item.url }}</td>
              <td class="td-mono">{{ item.status_code ?? 'ERR' }}</td>
              <td class="td-mono">{{ item.duration_ms }} ms</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <div v-else class="batch-empty">
      Select APIs or Groups in the left sidebar and click <strong>Run Selected</strong> to execute batch API tests.
    </div>
  </div>
</template>

<style scoped>
.batch-summary-view {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px;
  height: 100%;
  overflow-y: auto;
}

.batch-kpi-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
}

.batch-kpi {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.bk-label {
  font-size: 0.72rem;
  color: var(--text-muted);
  text-transform: uppercase;
  font-weight: 600;
}

.bk-val {
  font-size: 1.3rem;
  font-weight: 700;
  color: var(--text-main);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.bk-val.passed {
  color: var(--accent-green);
}

.bk-val.failed {
  color: var(--accent-red);
}

.batch-table-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  overflow: hidden;
}

.batch-results-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
}

.batch-results-table th,
.batch-results-table td {
  padding: 9px 12px;
  text-align: left;
  border-bottom: 1px solid var(--border-color);
}

.batch-results-table th {
  font-size: 0.73rem;
  text-transform: uppercase;
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.03);
}

.batch-row {
  cursor: pointer;
}

.batch-row:hover {
  background: rgba(255, 255, 255, 0.05);
}

.outcome-pill {
  font-size: 0.7rem;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 4px;
}

.outcome-pill.passed {
  color: var(--accent-green);
  background: rgba(52, 211, 153, 0.15);
}

.outcome-pill.failed {
  color: var(--accent-red);
  background: rgba(248, 113, 113, 0.16);
}

.method-pill {
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--accent-blue);
}

.td-name {
  font-weight: 600;
  color: var(--text-main);
}

.td-url,
.td-mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.76rem;
  color: var(--text-muted);
}

.batch-empty,
.batch-loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 0.86rem;
}
</style>
