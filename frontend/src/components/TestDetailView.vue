<script setup>
/* eslint-disable no-control-regex */
import { ref, computed } from 'vue'

const props = defineProps({
  detail: {
    type: Object,
    default: null
  },
  isLoading: {
    type: Boolean,
    default: false
  },
  latestRun: {
    type: Object,
    default: null
  },
  isRunning: {
    type: Boolean,
    default: false
  }
})

defineEmits(['run-test', 'run-single-method', 'clear-single-output'])

const copied = ref(false)

const copiedId = ref(false)
const copiedOutput = ref(false)

const stripAnsi = (str) => {
  if (!str) return ''
  return str.replace(/\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])/g, '')
}

const formattedOutput = computed(() => {
  if (!props.latestRun?.output) return ''
  let text = props.latestRun.output
  let escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  return escaped
    .replace(/\x1b\[32m/g, '<span style="color: #34d399; font-weight: 600;">')
    .replace(/\x1b\[31m/g, '<span style="color: #f87171; font-weight: 600;">')
    .replace(/\x1b\[33m/g, '<span style="color: #fbbf24;">')
    .replace(/\x1b\[34m/g, '<span style="color: #60a5fa;">')
    .replace(/\x1b\[35m/g, '<span style="color: #c084fc;">')
    .replace(/\x1b\[36m/g, '<span style="color: #38bdf8;">')
    .replace(/\x1b\[1m/g, '<span style="font-weight: 700; color: #f8fafc;">')
    .replace(/\x1b\[90m/g, '<span style="color: #94a3b8;">')
    .replace(/\x1b\[0m/g, '</span>')
    .replace(/\x1b\[[0-9;]*m/g, '')
})

const copyOutput = async () => {
  if (!props.latestRun?.output) return
  try {
    const clean = stripAnsi(props.latestRun.output)
    await navigator.clipboard.writeText(clean)
    copiedOutput.value = true
    setTimeout(() => {
      copiedOutput.value = false
    }, 2000)
  } catch (e) {
    console.error('Failed to copy output:', e)
  }
}



const copyDocstring = async () => {
  if (!props.detail?.docstring) return
  try {
    await navigator.clipboard.writeText(props.detail.docstring)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (e) {
    console.error('Failed to copy docstring:', e)
  }
}

const copyNodeId = async () => {
  if (!props.detail?.node_id) return
  try {
    await navigator.clipboard.writeText(props.detail.node_id)
    copiedId.value = true
    setTimeout(() => {
      copiedId.value = false
    }, 2000)
  } catch (e) {
    console.error('Failed to copy node id:', e)
  }
}
</script>

<template>
  <div class="test-detail-container">
    <!-- Loading State -->
    <div v-if="isLoading" class="detail-loading-state">
      <div class="detail-spinner"></div>
      <p class="loading-label">Extracting test docstring and metadata...</p>
    </div>

    <!-- Empty / No Detail State -->
    <div v-else-if="!detail" class="detail-empty-state">
      <div class="empty-icon">ℹ️</div>
      <h3>No Test Selected</h3>
      <p>Select exactly one test method from the explorer tree to view its docstring and details.</p>
    </div>

    <!-- Active Test Detail Card -->
    <div v-else class="detail-content-wrapper">
      <!-- Top Header Card -->
      <div class="detail-card detail-header-card">
        <div class="detail-badge-row">
          <span 
            class="detail-badge"
            :class="detail.type === 'scenario' ? 'badge-scenario' : 'badge-pytest'"
          >
            {{ detail.type === 'scenario' ? 'BEHAVE SCENARIO' : 'PYTEST METHOD' }}
          </span>

          <span v-if="detail.class_name" class="detail-badge badge-class">
            Class: {{ detail.class_name }}
          </span>

          <span v-if="detail.feature_title" class="detail-badge badge-feature">
            Feature: {{ detail.feature_title }}
          </span>

          <span v-if="detail.line_number" class="detail-badge badge-line">
            Line {{ detail.line_number }}
          </span>
        </div>

        <h2 class="detail-title">{{ detail.name }}</h2>

        <div class="detail-path-row">
          <span class="detail-path-text" :title="detail.file_path">
            📄 {{ detail.file_path }}
          </span>
          <button 
            class="btn-copy-id" 
            :class="{ active: copiedId }"
            @click="copyNodeId"
            title="Copy test node ID"
          >
            {{ copiedId ? '✓ Copied Node ID' : 'Copy ID' }}
          </button>
        </div>

        <!-- Tags / Decorators / Parameters Badges -->
        <div v-if="(detail.decorators && detail.decorators.length) || (detail.parameters && detail.parameters.length)" class="detail-meta-pills">
          <span 
            v-for="(dec, idx) in detail.decorators" 
            :key="'dec-' + idx"
            class="pill-tag pill-decorator"
          >
            {{ dec }}
          </span>
          <span 
            v-for="(param, idx) in detail.parameters" 
            :key="'param-' + idx"
            class="pill-tag pill-param"
          >
            arg: {{ param }}
          </span>
        </div>
      </div>

      <!-- Class Docstring (if exists) -->
      <div v-if="detail.class_docstring" class="detail-card class-docstring-card">
        <div class="card-section-header">
          <div class="section-title-wrap">
            <span class="section-icon">🏛️</span>
            <span class="section-heading">Class Docstring ({{ detail.class_name }})</span>
          </div>
        </div>
        <div class="docstring-box">
          <pre class="docstring-text">{{ detail.class_docstring }}</pre>
        </div>
      </div>

      <!-- Docstring Section -->
      <div class="detail-card docstring-card">
        <div class="card-section-header">
          <div class="section-title-wrap">
            <span class="section-icon">📝</span>
            <span class="section-heading">Method Docstring</span>
          </div>
          <button 
            v-if="detail.docstring" 
            class="btn-copy-doc"
            :class="{ active: copied }"
            @click="copyDocstring"
          >
            {{ copied ? '✓ Copied Docstring' : 'Copy Docstring' }}
          </button>
        </div>

        <div v-if="detail.docstring" class="docstring-box">
          <pre class="docstring-text">{{ detail.docstring }}</pre>
        </div>
        <div v-else class="docstring-empty">
          <span class="empty-subicon">💬</span>
          <p class="empty-text">No docstring provided for this test method.</p>
          <span class="empty-hint">Add a Python docstring (<code>"""..."""</code>) to provide documentation for this test case.</span>
        </div>
      </div>

      <!-- Latest Run Output & Logs Card -->
      <div class="detail-card run-output-card">
        <div class="card-section-header">
          <div class="section-title-wrap">
            <span class="section-icon">⚡</span>
            <span class="section-heading">Latest Run Output</span>
            <span 
              v-if="latestRun" 
              class="run-status-badge"
              :class="'status-' + (latestRun.outcome || 'unknown')"
            >
              {{ (latestRun.outcome || 'UNKNOWN').toUpperCase() }}
            </span>
            <span v-if="latestRun && latestRun.duration" class="run-meta-pill">
              ⏱️ {{ latestRun.duration }}s
            </span>
            <span v-if="latestRun && latestRun.timestamp" class="run-meta-pill">
              🕒 {{ latestRun.timestamp }}
            </span>
            <span 
              v-if="latestRun && detail.modified_since_run" 
              class="run-meta-pill modified-badge"
              title="Test code has been modified after this run output was recorded"
            >
              ⚠️ Code Modified
            </span>
          </div>

          <div class="run-actions">
            <button 
              v-if="latestRun && latestRun.output" 
              class="btn-clear-output"
              @click="$emit('clear-single-output', detail.node_id)"
              title="Clear stored run output for this test method"
            >
              🗑️ Clear
            </button>

            <button 
              v-if="latestRun && latestRun.output" 
              class="btn-copy-output"
              :class="{ active: copiedOutput }"
              @click="copyOutput"
              title="Copy output logs"
            >
              {{ copiedOutput ? '✓ Copied Output' : 'Copy Output' }}
            </button>

            <button 
              class="btn-run-method" 
              :disabled="isRunning"
              @click="$emit('run-single-method', detail.node_id)"
              :title="detail.type === 'scenario' ? 'Execute this scenario' : 'Execute this test method with -s flag'"
            >
              {{ isRunning ? '⏳ Running...' : (detail.type === 'scenario' ? '▶ Run Scenario' : '▶ Run Test (-s)') }}
            </button>
          </div>
        </div>

        <!-- Terminal Output Box -->
        <div v-if="latestRun && latestRun.output" class="method-terminal-box">
          <pre class="method-terminal-text" v-html="formattedOutput"></pre>
        </div>
        <div v-else class="method-terminal-empty">
          <span class="terminal-empty-icon">⚪</span>
          <p class="empty-text">No execution output recorded for this test method yet.</p>
          <span class="empty-hint">Click <strong>{{ detail.type === 'scenario' ? '▶ Run Scenario' : '▶ Run Test (-s)' }}</strong> to execute this test and capture console logs.</span>
        </div>

      </div>

      <!-- Behave Scenario Steps (if exists) -->
      <div v-if="detail.steps && detail.steps.length" class="detail-card steps-card">
        <div class="card-section-header">
          <div class="section-title-wrap">
            <span class="section-icon">📋</span>
            <span class="section-heading">Scenario Steps ({{ detail.steps.length }})</span>
          </div>
        </div>

        <div class="scenario-steps-list">
          <div 
            v-for="(step, idx) in detail.steps" 
            :key="'step-' + idx"
            class="scenario-step-item"
          >
            <span class="step-num">{{ idx + 1 }}</span>
            <span 
              class="step-badge"
              :class="getStepBadgeClass(step)"
            >
              {{ getStepKeyword(step) }}
            </span>
            <span class="step-body">{{ getStepBody(step) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  methods: {
    getStepKeyword(step) {
      const match = step.match(/^(Given|When|Then|And|But)\s+/i)
      return match ? match[1].toUpperCase() : 'STEP'
    },
    getStepBody(step) {
      return step.replace(/^(Given|When|Then|And|But)\s+/i, '')
    },
    getStepBadgeClass(step) {
      const kw = this.getStepKeyword(step).toLowerCase()
      switch (kw) {
        case 'given': return 'badge-given'
        case 'when': return 'badge-when'
        case 'then': return 'badge-then'
        case 'and': return 'badge-and'
        case 'but': return 'badge-but'
        default: return 'badge-generic'
      }
    }
  }
}
</script>

<style scoped>
.test-detail-container {
  height: 100%;
  overflow-y: auto;
  padding-right: 8px;
}

.detail-loading-state,
.detail-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 350px;
  background: var(--bg-card);
  backdrop-filter: var(--glass-backdrop);
  -webkit-backdrop-filter: var(--glass-backdrop);
  border: 1px solid var(--border-color);
  border-radius: var(--glass-border-radius);
  color: var(--text-muted);
  text-align: center;
  padding: 32px;
}

.detail-spinner {
  width: 38px;
  height: 38px;
  border: 3px solid rgba(56, 189, 248, 0.2);
  border-top-color: var(--accent-blue);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-label {
  font-size: 0.95rem;
  color: var(--text-muted);
}

.empty-icon {
  font-size: 2.2rem;
  margin-bottom: 12px;
}

.detail-empty-state h3 {
  font-size: 1.15rem;
  color: var(--text-main);
  margin-bottom: 8px;
}

.detail-empty-state p {
  font-size: 0.88rem;
  max-width: 400px;
  line-height: 1.5;
}

.detail-content-wrapper {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-card {
  background: var(--bg-card);
  backdrop-filter: var(--glass-backdrop);
  -webkit-backdrop-filter: var(--glass-backdrop);
  border: 1px solid var(--border-color);
  border-radius: var(--glass-border-radius);
  padding: 20px;
  box-shadow: var(--glass-shadow);
  transition: border-color 0.2s ease;
}

.detail-card:hover {
  border-color: var(--border-hover);
}

.detail-badge-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.detail-badge {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  padding: 3px 8px;
  border-radius: 6px;
  text-transform: uppercase;
}

.badge-pytest {
  background: rgba(56, 189, 248, 0.18);
  color: #38bdf8;
  border: 1px solid rgba(56, 189, 248, 0.35);
}

.badge-scenario {
  background: rgba(168, 85, 247, 0.2);
  color: #c084fc;
  border: 1px solid rgba(168, 85, 247, 0.4);
}

.badge-class {
  background: rgba(251, 191, 36, 0.15);
  color: #fbbf24;
  border: 1px solid rgba(251, 191, 36, 0.3);
}

.badge-feature {
  background: rgba(52, 211, 153, 0.15);
  color: #34d399;
  border: 1px solid rgba(52, 211, 153, 0.3);
}

.badge-line {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-muted);
  border: 1px solid var(--border-color);
}

.detail-title {
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--text-main);
  word-break: break-word;
  line-height: 1.3;
  margin-bottom: 10px;
}

.detail-path-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: var(--bg-input);
  padding: 8px 12px;
  border-radius: 8px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.8rem;
  color: var(--text-muted);
}

.detail-path-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-copy-id {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-main);
  border: 1px solid var(--border-color);
  padding: 4px 8px;
  border-radius: 5px;
  font-size: 0.72rem;
  font-weight: 600;
  white-space: nowrap;
}

.btn-copy-id:hover {
  background: rgba(56, 189, 248, 0.25);
  border-color: var(--accent-blue);
}

.btn-copy-id.active {
  background: rgba(52, 211, 153, 0.25);
  border-color: var(--accent-green);
  color: #34d399;
}

.detail-meta-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 14px;
}

.pill-tag {
  font-size: 0.75rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  padding: 3px 8px;
  border-radius: 6px;
}

.pill-decorator {
  background: rgba(129, 140, 248, 0.15);
  color: #818cf8;
  border: 1px solid rgba(129, 140, 248, 0.3);
}

.pill-param {
  background: rgba(244, 114, 182, 0.15);
  color: #f472b6;
  border: 1px solid rgba(244, 114, 182, 0.3);
}

/* Card Section Header */
.card-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.section-title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-icon {
  font-size: 1.1rem;
}

.section-heading {
  font-size: 0.95rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: var(--text-main);
}

.btn-copy-doc {
  background: rgba(56, 189, 248, 0.15);
  color: #38bdf8;
  border: 1px solid rgba(56, 189, 248, 0.3);
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 0.78rem;
  font-weight: 600;
}

.btn-copy-doc:hover {
  background: rgba(56, 189, 248, 0.25);
  border-color: #38bdf8;
}

.btn-copy-doc.active {
  background: rgba(52, 211, 153, 0.25);
  border-color: #34d399;
  color: #34d399;
}

/* Docstring Box */
.docstring-box {
  background: rgba(11, 15, 25, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-left: 3px solid var(--accent-blue);
  border-radius: 8px;
  padding: 16px;
}

.docstring-text {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.88rem;
  line-height: 1.6;
  color: #e2e8f0;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}

.docstring-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(11, 15, 25, 0.4);
  border: 1px dashed var(--border-color);
  border-radius: 8px;
  text-align: center;
}

.empty-subicon {
  font-size: 1.5rem;
  margin-bottom: 6px;
  opacity: 0.7;
}

.empty-text {
  font-size: 0.9rem;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.empty-hint {
  font-size: 0.78rem;
  color: var(--text-muted);
  opacity: 0.8;
}

.empty-hint code {
  background: var(--bg-input);
  padding: 2px 5px;
  border-radius: 4px;
}

/* Scenario Steps */
.scenario-steps-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.scenario-step-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  background: rgba(11, 15, 25, 0.6);
  border: 1px solid var(--border-color);
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 0.85rem;
  line-height: 1.4;
}

.step-num {
  font-size: 0.72rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  color: var(--text-muted);
  min-width: 18px;
  padding-top: 2px;
}

.step-badge {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  padding: 2px 7px;
  border-radius: 5px;
  min-width: 52px;
  text-align: center;
  flex-shrink: 0;
}

.badge-given {
  background: rgba(56, 189, 248, 0.2);
  color: #38bdf8;
  border: 1px solid rgba(56, 189, 248, 0.35);
}

.badge-when {
  background: rgba(251, 146, 60, 0.2);
  color: #fb923c;
  border: 1px solid rgba(251, 146, 60, 0.35);
}

.badge-then {
  background: rgba(52, 211, 153, 0.2);
  color: #34d399;
  border: 1px solid rgba(52, 211, 153, 0.35);
}

.badge-and,
.badge-but {
  background: rgba(167, 139, 250, 0.2);
  color: #c084fc;
  border: 1px solid rgba(167, 139, 250, 0.35);
}

.badge-generic {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-muted);
}

.step-body {
  color: var(--text-main);
  word-break: break-word;
}

/* Latest Run Output Styles */
.run-output-card {
  border-left: 3px solid rgba(56, 189, 248, 0.4);
}

.run-status-badge {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  padding: 3px 8px;
  border-radius: 6px;
  text-transform: uppercase;
}

.status-passed {
  background: rgba(52, 211, 153, 0.2);
  color: #34d399;
  border: 1px solid rgba(52, 211, 153, 0.4);
  box-shadow: 0 0 10px rgba(52, 211, 153, 0.15);
}

.status-failed {
  background: rgba(248, 113, 113, 0.2);
  color: #f87171;
  border: 1px solid rgba(248, 113, 113, 0.4);
  box-shadow: 0 0 10px rgba(248, 113, 113, 0.15);
}

.status-skipped {
  background: rgba(251, 191, 36, 0.2);
  color: #fbbf24;
  border: 1px solid rgba(251, 191, 36, 0.4);
}

.status-running {
  background: rgba(56, 189, 248, 0.25);
  color: #38bdf8;
  border: 1px solid rgba(56, 189, 248, 0.5);
  animation: pulse-badge 1.5s infinite;
}

@keyframes pulse-badge {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.status-unknown {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-muted);
  border: 1px solid var(--border-color);
}

.run-meta-pill {
  font-size: 0.75rem;
  background: var(--bg-input);
  color: var(--text-muted);
  padding: 3px 8px;
  border-radius: 6px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.modified-badge {
  background: rgba(245, 158, 11, 0.18);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.45);
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.run-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-clear-output {
  background: rgba(239, 68, 68, 0.12);
  color: #fca5a5;
  border: 1px solid rgba(239, 68, 68, 0.3);
  padding: 5px 10px;
  border-radius: 6px;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.btn-clear-output:hover {
  background: rgba(239, 68, 68, 0.25);
  border-color: rgba(239, 68, 68, 0.6);
  color: #ffffff;
}

.btn-copy-output {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-muted);
  border: 1px solid var(--border-color);
  padding: 5px 10px;
  border-radius: 6px;
  font-size: 0.78rem;
  font-weight: 600;
}

.btn-copy-output:hover {
  background: rgba(255, 255, 255, 0.15);
  color: var(--text-main);
}

.btn-copy-output.active {
  background: rgba(52, 211, 153, 0.25);
  border-color: #34d399;
  color: #34d399;
}

.btn-run-method {
  background: linear-gradient(135deg, rgba(56, 189, 248, 0.2) 0%, rgba(99, 102, 241, 0.2) 100%);
  color: #38bdf8;
  border: 1px solid rgba(56, 189, 248, 0.4);
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 6px;
}

.btn-run-method:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(56, 189, 248, 0.35) 0%, rgba(99, 102, 241, 0.35) 100%);
  border-color: #38bdf8;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(56, 189, 248, 0.25);
}

.btn-run-method:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.method-terminal-box {
  background: #080c14;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 14px 16px;
  max-height: 380px;
  overflow-y: auto;
  box-shadow: inset 0 2px 6px rgba(0, 0, 0, 0.4);
}

.method-terminal-text {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", Courier, monospace;
  font-size: 0.84rem;
  line-height: 1.55;
  color: #e2e8f0;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}

.method-terminal-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(8, 12, 20, 0.4);
  border: 1px dashed var(--border-color);
  border-radius: 8px;
  text-align: center;
}

.terminal-empty-icon {
  font-size: 1.4rem;
  margin-bottom: 6px;
  opacity: 0.6;
}
</style>

