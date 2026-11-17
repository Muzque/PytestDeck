<script setup>
import { computed } from 'vue'

const props = defineProps({
  request: { type: Object, required: true },
  activeEnv: { type: Object, default: () => ({}) },
  stressConfig: { type: Object, required: true },
  stressResult: { type: Object, default: null },
  isRunningStress: { type: Boolean, default: false }
})

const emit = defineEmits(['update:stressConfig', 'run-stress'])

const updateStressField = (key, val) => {
  emit('update:stressConfig', {
    ...props.stressConfig,
    [key]: Number(val || 1)
  })
}

const fullUrl = computed(() => {
  const p = props.request.path || ''
  if (p.startsWith('http://') || p.startsWith('https://')) return p
  const base = (props.activeEnv?.base_url || 'http://127.0.0.1:9388').replace(/\/$/, '')
  return p.startsWith('/') ? `${base}${p}` : `${base}/${p}`
})
</script>

<template>
  <div class="stress-test-view">
    <!-- Target API Summary & Controls -->
    <div class="stress-control-card">
      <div class="stress-target-info">
        <span class="stress-method-tag">{{ request.method || 'GET' }}</span>
        <span class="stress-target-name">{{ request.name || 'Current API' }}</span>
        <code class="stress-target-url">{{ fullUrl }}</code>
      </div>

      <div class="stress-params-row">
        <div class="stress-field">
          <label for="stress-total-input">Total Requests (N)</label>
          <input
            id="stress-total-input"
            :value="stressConfig.totalRequests"
            type="number"
            min="1"
            max="2000"
            class="stress-number-input"
            @input="updateStressField('totalRequests', $event.target.value)"
          />
        </div>

        <div class="stress-field">
          <label for="stress-concurrency-input">Parallel Concurrency (C)</label>
          <input
            id="stress-concurrency-input"
            :value="stressConfig.concurrency"
            type="number"
            min="1"
            max="200"
            class="stress-number-input"
            @input="updateStressField('concurrency', $event.target.value)"
          />
        </div>

        <button
          id="btn-run-stress-test"
          type="button"
          class="btn btn-primary btn-run-stress"
          :disabled="isRunningStress"
          @click="emit('run-stress')"
        >
          {{ isRunningStress ? '⏳ Running Stress Test...' : '⚡ Run Parallel Stress Test' }}
        </button>
      </div>
    </div>

    <!-- Stress Test Results Dashboard -->
    <div v-if="stressResult" class="stress-results-area" data-testid="stress-results-panel">
      <div class="stress-kpi-grid">
        <div class="stress-kpi-card highlight-avg">
          <span class="kpi-label">Avg Time Cost</span>
          <span class="kpi-value" data-testid="stress-avg-ms">{{ stressResult.avg_ms }} ms</span>
        </div>

        <div class="stress-kpi-card highlight-min">
          <span class="kpi-label">Min Time Cost</span>
          <span class="kpi-value" data-testid="stress-min-ms">{{ stressResult.min_ms }} ms</span>
        </div>

        <div class="stress-kpi-card highlight-max">
          <span class="kpi-label">Max Time Cost</span>
          <span class="kpi-value" data-testid="stress-max-ms">{{ stressResult.max_ms }} ms</span>
        </div>

        <div class="stress-kpi-card">
          <span class="kpi-label">P95 Latency</span>
          <span class="kpi-value" data-testid="stress-p95-ms">{{ stressResult.p95_ms }} ms</span>
        </div>

        <div class="stress-kpi-card">
          <span class="kpi-label">Throughput</span>
          <span class="kpi-value" data-testid="stress-rps">{{ stressResult.rps }} req/s</span>
        </div>

        <div class="stress-kpi-card">
          <span class="kpi-label">Success / Warn / Fail</span>
          <span class="kpi-value" data-testid="stress-success-fail">
            <span class="text-pass">{{ stressResult.success_count }}</span> /
            <span class="text-warn">{{ stressResult.warning_count ?? 0 }}</span> /
            <span class="text-fail">{{ stressResult.fail_count }}</span>
          </span>
        </div>
      </div>

      <!-- Status Code Breakdown & Latency Distribution -->
      <div class="stress-detail-grid">
        <div class="stress-subcard">
          <h4>HTTP Status Code Distribution</h4>
          <div class="status-dist-list">
            <div
              v-for="(count, code) in stressResult.status_codes"
              :key="code"
              class="status-dist-row"
            >
              <span class="status-code-pill">{{ code }}</span>
              <div class="status-bar-track">
                <div
                  class="status-bar-fill"
                  :style="{ width: Math.round((count / stressResult.total_requests) * 100) + '%' }"
                ></div>
              </div>
              <span class="status-count-label">
                {{ count }} ({{ Math.round((count / stressResult.total_requests) * 100) }}%)
              </span>
            </div>
          </div>
        </div>

        <div class="stress-subcard">
          <h4>Sample Request Latencies (First {{ stressResult.latency_samples?.length || 0 }} Calls)</h4>
          <div class="latency-bars">
            <div
              v-for="(ms, idx) in stressResult.latency_samples"
              :key="idx"
              class="latency-bar"
              :style="{
                height: Math.max(12, Math.min(100, Math.round((ms / Math.max(0.1, stressResult.max_ms)) * 100))) + '%'
              }"
              :title="`Request #${idx + 1}: ${ms} ms`"
            ></div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="stress-empty">
      Configure Total Requests (N) and Parallel Concurrency (C), then click
      <strong>Run Parallel Stress Test</strong> to measure Avg, Min, Max, and P95 latency.
    </div>
  </div>
</template>

<style scoped>
.stress-test-view {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px;
  height: 100%;
  overflow-y: auto;
}

.stress-control-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stress-target-info {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.stress-method-tag {
  font-size: 0.75rem;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 5px;
  background: rgba(56, 189, 248, 0.16);
  color: var(--accent-blue);
  border: 1px solid rgba(56, 189, 248, 0.35);
}

.stress-target-name {
  font-weight: 700;
  color: var(--text-main);
}

.stress-target-url {
  font-size: 0.8rem;
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.04);
  padding: 3px 8px;
  border-radius: 5px;
}

.stress-params-row {
  display: flex;
  align-items: flex-end;
  gap: 14px;
  flex-wrap: wrap;
}

.stress-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stress-field label {
  font-size: 0.74rem;
  font-weight: 600;
  color: var(--text-muted);
}

.stress-number-input {
  width: 150px;
  padding: 7px 10px;
  border-radius: 6px;
  background: var(--bg-input);
  color: var(--text-main);
  border: 1px solid var(--border-color);
  font-size: 0.85rem;
}

.btn-run-stress {
  padding: 8px 18px;
  font-weight: 700;
  border-radius: 7px;
}

.stress-kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(155px, 1fr));
  gap: 10px;
}

.stress-kpi-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stress-kpi-card.highlight-avg {
  border-color: rgba(56, 189, 248, 0.45);
}

.stress-kpi-card.highlight-min {
  border-color: rgba(52, 211, 153, 0.45);
}

.stress-kpi-card.highlight-max {
  border-color: rgba(251, 191, 36, 0.45);
}

.kpi-label {
  font-size: 0.73rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.kpi-value {
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--text-main);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.text-pass {
  color: var(--accent-green);
}

.text-warn {
  color: var(--accent-yellow);
}

.text-fail {
  color: var(--accent-red);
}

.stress-detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 12px;
}

.stress-subcard {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.stress-subcard h4 {
  font-size: 0.82rem;
  color: var(--text-muted);
}

.status-dist-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.status-dist-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-code-pill {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.76rem;
  font-weight: 700;
  color: var(--accent-green);
  min-width: 44px;
}

.status-bar-track {
  flex: 1;
  height: 8px;
  background: rgba(255, 255, 255, 0.07);
  border-radius: 4px;
  overflow: hidden;
}

.status-bar-fill {
  height: 100%;
  background: var(--accent-blue);
}

.status-count-label {
  font-size: 0.75rem;
  color: var(--text-muted);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.latency-bars {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 90px;
  padding-top: 8px;
}

.latency-bar {
  flex: 1;
  min-width: 3px;
  background: var(--accent-blue);
  border-radius: 2px 2px 0 0;
  opacity: 0.85;
}

.stress-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 0.86rem;
}
</style>
