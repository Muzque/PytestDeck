<script setup>
import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps({
  request: { type: Object, required: true },
  activeEnv: { type: Object, default: () => ({}) },
  saveStatus: { type: String, default: 'saved' },
  isSending: { type: Boolean, default: false },
  response: { type: Object, default: null }
})

const emit = defineEmits(['update:request', 'send', 'open-stress'])

const reqSubTab = ref('params')
const showRespHeaders = ref(false)

// Response Quick Search & Virtual Scroll state
const responseSearch = ref('')
const filterMatchedLinesOnly = ref(false)
const activeMatchIdx = ref(0)
const scrollContainer = ref(null)
const scrollTop = ref(0)
const ROW_HEIGHT = 20
const VISIBLE_BUFFER = 60

const HTTP_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']

const updateField = (key, value) => {
  emit('update:request', {
    ...props.request,
    [key]: value
  })
}

const updateQueryParam = (idx, key, value) => {
  const next = props.request.query_params.map((item, i) =>
    i === idx ? { ...item, [key]: value } : { ...item }
  )
  updateField('query_params', next)
}

const addQueryParam = () => {
  updateField('query_params', [
    ...props.request.query_params,
    { key: '', value: '', enabled: true }
  ])
}

const removeQueryParam = (idx) => {
  const next = props.request.query_params.filter((_, i) => i !== idx)
  updateField(
    'query_params',
    next.length > 0 ? next : [{ key: '', value: '', enabled: true }]
  )
}

const updateHeader = (idx, key, value) => {
  const next = props.request.headers.map((item, i) =>
    i === idx ? { ...item, [key]: value } : { ...item }
  )
  updateField('headers', next)
}

const addHeader = () => {
  updateField('headers', [
    ...props.request.headers,
    { key: '', value: '', enabled: true }
  ])
}

const removeHeader = (idx) => {
  const next = props.request.headers.filter((_, i) => i !== idx)
  updateField(
    'headers',
    next.length > 0 ? next : [{ key: '', value: '', enabled: true }]
  )
}

const formatJsonBody = () => {
  if (!props.request.body) return
  try {
    const parsed = JSON.parse(props.request.body)
    updateField('body', JSON.stringify(parsed, null, 2))
  } catch {
    // Keep as-is if invalid JSON
  }
}

const onBodyKeyDown = (e) => {
  if (e.key === 'Tab' && !e.ctrlKey && !e.altKey && !e.metaKey && !e.shiftKey) {
    e.preventDefault()
    const el = e.target
    const start = el.selectionStart ?? 0
    const end = el.selectionEnd ?? start
    const val = String(props.request.body || '')
    const nextVal = val.slice(0, start) + '  ' + val.slice(end)
    updateField('body', nextVal)
    nextTick(() => {
      el.selectionStart = el.selectionEnd = start + 2
    })
  }
}

const allLines = computed(() => {
  const raw = props.response?.body ?? ''
  if (!raw) return []
  return String(raw).split('\n')
})

const searchTermLower = computed(() => responseSearch.value.trim().toLowerCase())

const matchedLineNumbers = computed(() => {
  const q = searchTermLower.value
  if (!q) return []
  const matches = []
  const lines = allLines.value
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].toLowerCase().includes(q)) {
      matches.push(i)
    }
  }
  return matches
})

const displayLines = computed(() => {
  const lines = allLines.value
  const q = searchTermLower.value
  const matchedSet = new Set(matchedLineNumbers.value)
  if (q && filterMatchedLinesOnly.value) {
    return matchedLineNumbers.value.map((lineIdx) => ({
      lineNo: lineIdx + 1,
      origIdx: lineIdx,
      text: lines[lineIdx],
      isMatch: true
    }))
  }
  return lines.map((text, idx) => ({
    lineNo: idx + 1,
    origIdx: idx,
    text,
    isMatch: q ? matchedSet.has(idx) : false
  }))
})

const totalVirtualHeight = computed(() => displayLines.value.length * ROW_HEIGHT)

const visibleSlice = computed(() => {
  const total = displayLines.value.length
  const startIdx = Math.max(0, Math.floor(scrollTop.value / ROW_HEIGHT) - 15)
  const endIdx = Math.min(total, startIdx + VISIBLE_BUFFER)
  return {
    startIdx,
    offsetY: startIdx * ROW_HEIGHT,
    items: displayLines.value.slice(startIdx, endIdx)
  }
})

const onResponseScroll = (e) => {
  scrollTop.value = e.target.scrollTop
}

const scrollToMatch = (matchIndex) => {
  if (matchedLineNumbers.value.length === 0) return
  const targetOrigIdx = matchedLineNumbers.value[matchIndex]
  const displayIdx = displayLines.value.findIndex((d) => d.origIdx === targetOrigIdx)
  if (displayIdx !== -1 && scrollContainer.value) {
    scrollContainer.value.scrollTop = Math.max(0, (displayIdx - 3) * ROW_HEIGHT)
  }
}

const nextMatch = () => {
  const total = matchedLineNumbers.value.length
  if (total === 0) return
  activeMatchIdx.value = (activeMatchIdx.value + 1) % total
  scrollToMatch(activeMatchIdx.value)
}

const prevMatch = () => {
  const total = matchedLineNumbers.value.length
  if (total === 0) return
  activeMatchIdx.value = (activeMatchIdx.value - 1 + total) % total
  scrollToMatch(activeMatchIdx.value)
}

watch(searchTermLower, () => {
  activeMatchIdx.value = 0
  if (matchedLineNumbers.value.length > 0) {
    scrollToMatch(0)
  }
})

const formatBytes = (bytes) => {
  const b = Number(bytes || 0)
  if (b < 1024) return `${b} B`
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`
  return `${(b / (1024 * 1024)).toFixed(2)} MB`
}
</script>

<template>
  <div class="api-request-view">
    <!-- Request Metadata Row -->
    <div class="req-meta-bar">
      <div class="req-name-group">
        <label for="api-req-name" class="meta-label">API Name</label>
        <input
          id="api-req-name"
          :value="request.name"
          type="text"
          class="req-name-input"
          placeholder="API Request Name..."
          @input="updateField('name', $event.target.value)"
        />
      </div>

      <div class="req-expected-group">
        <label for="api-expected-status" class="meta-label">Expected Status</label>
        <input
          id="api-expected-status"
          :value="request.expected_status"
          type="number"
          class="req-status-input"
          min="100"
          max="599"
          @input="updateField('expected_status', Number($event.target.value || 200))"
        />
      </div>

      <div class="req-meta-right">
        <span class="autosave-indicator" data-testid="api-autosave-badge">
          {{ saveStatus === 'saving' ? '⏳ Saving...' : '✓ Auto-saved' }}
        </span>
        <button
          id="btn-jump-stress"
          type="button"
          class="btn-jump-stress"
          title="Open Parallel Stress Test for this API"
          @click="emit('open-stress')"
        >
          ⚡ Parallel Stress Test
        </button>
      </div>
    </div>

    <!-- URL & Method Bar -->
    <div class="req-url-bar">
      <select
        id="api-method-select"
        :value="request.method"
        class="api-method-select"
        @change="updateField('method', $event.target.value)"
      >
        <option v-for="m in HTTP_METHODS" :key="m" :value="m">{{ m }}</option>
      </select>

      <div class="url-input-composite">
        <span v-if="!request.path?.startsWith('http')" class="base-url-prefix" :title="activeEnv?.base_url">
          {{ activeEnv?.base_url || 'http://127.0.0.1:9388' }}
        </span>
        <input
          id="api-path-input"
          :value="request.path"
          type="text"
          class="api-path-input"
          placeholder="/api/endpoint or https://..."
          @input="updateField('path', $event.target.value)"
          @keydown.enter="emit('send')"
        />
      </div>

      <button
        id="btn-send-api"
        type="button"
        class="btn btn-primary btn-send-api"
        :disabled="isSending"
        @click="emit('send')"
      >
        {{ isSending ? 'Sending...' : '🚀 Send' }}
      </button>
    </div>

    <!-- Request Config Sub-Tabs -->
    <div class="req-config-panel">
      <div class="req-subtabs">
        <button
          type="button"
          class="req-subtab-btn"
          :class="{ active: reqSubTab === 'params' }"
          data-req-tab="params"
          @click="reqSubTab = 'params'"
        >
          Query Params ({{ request.query_params.filter((q) => q.key).length }})
        </button>
        <button
          type="button"
          class="req-subtab-btn"
          :class="{ active: reqSubTab === 'headers' }"
          data-req-tab="headers"
          @click="reqSubTab = 'headers'"
        >
          Headers ({{ request.headers.filter((h) => h.key).length }})
        </button>
        <button
          type="button"
          class="req-subtab-btn"
          :class="{ active: reqSubTab === 'body' }"
          data-req-tab="body"
          @click="reqSubTab = 'body'"
        >
          Body
        </button>
      </div>

      <!-- Query Params Editor -->
      <div v-show="reqSubTab === 'params'" class="req-subtab-body">
        <div class="kv-toolbar">
          <span>Query Parameters</span>
          <button id="btn-add-query-param" type="button" class="btn-mini" @click="addQueryParam">
            + Add Param
          </button>
        </div>
        <div class="kv-rows-scroll">
          <div v-for="(q, idx) in request.query_params" :key="idx" class="kv-edit-row">
            <input
              :checked="q.enabled"
              type="checkbox"
              @change="updateQueryParam(idx, 'enabled', $event.target.checked)"
            />
            <input
              :value="q.key"
              type="text"
              class="kv-text-input param-key-input"
              placeholder="Param key (e.g. page)"
              @input="updateQueryParam(idx, 'key', $event.target.value)"
            />
            <input
              :value="q.value"
              type="text"
              class="kv-text-input param-val-input"
              placeholder="Value (e.g. 1)"
              @input="updateQueryParam(idx, 'value', $event.target.value)"
            />
            <button type="button" class="btn-kv-del" @click="removeQueryParam(idx)">×</button>
          </div>
        </div>
      </div>

      <!-- Headers Editor -->
      <div v-show="reqSubTab === 'headers'" class="req-subtab-body">
        <div class="kv-toolbar">
          <span>Request Headers</span>
          <button id="btn-add-req-header" type="button" class="btn-mini" @click="addHeader">
            + Add Header
          </button>
        </div>
        <div class="kv-rows-scroll">
          <div v-for="(h, idx) in request.headers" :key="idx" class="kv-edit-row">
            <input
              :checked="h.enabled"
              type="checkbox"
              @change="updateHeader(idx, 'enabled', $event.target.checked)"
            />
            <input
              :value="h.key"
              type="text"
              class="kv-text-input header-key-input"
              placeholder="Header name"
              @input="updateHeader(idx, 'key', $event.target.value)"
            />
            <input
              :value="h.value"
              type="text"
              class="kv-text-input header-val-input"
              placeholder="Header value"
              @input="updateHeader(idx, 'value', $event.target.value)"
            />
            <button type="button" class="btn-kv-del" @click="removeHeader(idx)">×</button>
          </div>
        </div>
      </div>

      <!-- Body Editor -->
      <div v-show="reqSubTab === 'body'" class="req-subtab-body body-editor-wrap">
        <div class="kv-toolbar">
          <div class="body-type-group">
            <label>
              <input
                :checked="request.body_type === 'json'"
                type="radio"
                value="json"
                @change="updateField('body_type', 'json')"
              />
              JSON
            </label>
            <label>
              <input
                :checked="request.body_type === 'text'"
                type="radio"
                value="text"
                @change="updateField('body_type', 'text')"
              />
              Raw Text
            </label>
          </div>
          <button type="button" class="btn-mini" @click="formatJsonBody">Beautify JSON</button>
        </div>
        <textarea
          id="api-body-textarea"
          :value="request.body"
          class="api-body-textarea"
          placeholder='{"key": "value"}'
          @input="updateField('body', $event.target.value)"
          @keydown="onBodyKeyDown"
        ></textarea>
      </div>
    </div>

    <!-- Response Panel -->
    <div class="response-panel">
      <div class="response-header-bar">
        <div class="response-title-group">
          <span class="resp-section-title">Response</span>
          <template v-if="response">
            <span
              class="resp-status-badge"
              :class="response.outcome || 'failed'"
              data-testid="api-response-status"
            >
              {{ response.status_code ?? 'ERR' }}
            </span>
            <span class="resp-metric-chip" data-testid="api-response-time">
              ⏱ {{ response.duration_ms }} ms
            </span>
            <span class="resp-metric-chip">
              📦 {{ formatBytes(response.size_bytes) }}
            </span>
            <span class="resp-metric-chip">
              {{ allLines.length }} lines
            </span>
            <button
              type="button"
              class="btn-mini"
              @click="showRespHeaders = !showRespHeaders"
            >
              {{ showRespHeaders ? 'Hide Headers' : 'Headers' }}
            </button>
          </template>
        </div>

        <!-- Quick Search Bar in Response -->
        <div class="response-search-bar">
          <input
            id="response-search-input"
            v-model="responseSearch"
            type="text"
            class="response-search-input"
            placeholder="Quick search in response..."
          />
          <template v-if="responseSearch.trim()">
            <span class="match-counter" data-testid="response-match-count">
              {{ matchedLineNumbers.length > 0 ? `${activeMatchIdx + 1} / ${matchedLineNumbers.length}` : '0 matches' }}
            </span>
            <button
              id="btn-resp-prev-match"
              type="button"
              class="btn-search-nav"
              :disabled="matchedLineNumbers.length === 0"
              title="Previous match"
              @click="prevMatch"
            >
              ↑
            </button>
            <button
              id="btn-resp-next-match"
              type="button"
              class="btn-search-nav"
              :disabled="matchedLineNumbers.length === 0"
              title="Next match"
              @click="nextMatch"
            >
              ↓
            </button>
            <label class="filter-matches-toggle" title="Show only lines matching search">
              <input id="chk-filter-matches" v-model="filterMatchedLinesOnly" type="checkbox" />
              Filter
            </label>
          </template>
        </div>
      </div>

      <!-- Optional Collapsible Response Headers -->
      <div v-if="response && showRespHeaders" class="resp-headers-drawer">
        <div v-for="(val, key) in response.headers" :key="key" class="resp-header-item">
          <span class="rh-key">{{ key }}:</span>
          <span class="rh-val">{{ val }}</span>
        </div>
      </div>

      <!-- Virtualized Scrollable Response Output -->
      <div
        v-if="response"
        id="api-response-scroll"
        ref="scrollContainer"
        class="response-body-viewport"
        @scroll="onResponseScroll"
      >
        <div
          class="virtual-spacer"
          :style="{ height: totalVirtualHeight + 'px' }"
        >
          <div
            class="virtual-window"
            :style="{ transform: `translateY(${visibleSlice.offsetY}px)` }"
          >
            <div
              v-for="line in visibleSlice.items"
              :key="line.origIdx"
              class="resp-line"
              :class="{
                'is-match': line.isMatch,
                'is-active-match':
                  line.isMatch && matchedLineNumbers[activeMatchIdx] === line.origIdx
              }"
            >
              <span class="resp-line-no">{{ line.lineNo }}</span>
              <span class="resp-line-text">{{ line.text }}</span>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="response-empty">
        Click <strong>Send</strong> to execute this API request and inspect the response.
      </div>
    </div>
  </div>
</template>

<style scoped>
.api-request-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 10px;
  padding: 12px 16px;
  overflow: hidden;
}

.req-meta-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.req-name-group {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  min-width: 200px;
}

.req-expected-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.meta-label {
  font-size: 0.74rem;
  font-weight: 600;
  color: var(--text-muted);
  white-space: nowrap;
}

.req-name-input {
  flex: 1;
  padding: 5px 9px;
  border-radius: 6px;
  background: var(--bg-input);
  color: var(--text-main);
  border: 1px solid var(--border-color);
  font-size: 0.84rem;
}

.req-status-input {
  width: 68px;
  padding: 5px 8px;
  border-radius: 6px;
  background: var(--bg-input);
  color: var(--text-main);
  border: 1px solid var(--border-color);
  font-size: 0.82rem;
}

.req-meta-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.autosave-indicator {
  font-size: 0.74rem;
  color: var(--accent-green);
  font-weight: 600;
}

.btn-jump-stress {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 5px 10px;
  border-radius: 6px;
  background: rgba(99, 102, 241, 0.16);
  color: #a5b4fc;
  border: 1px solid rgba(99, 102, 241, 0.35);
}

.req-url-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.api-method-select {
  padding: 8px 10px;
  border-radius: 7px;
  background: var(--bg-input);
  color: var(--accent-blue);
  border: 1px solid var(--border-color);
  font-weight: 700;
  font-size: 0.84rem;
}

.url-input-composite {
  display: flex;
  align-items: center;
  flex: 1;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: 7px;
  overflow: hidden;
}

.base-url-prefix {
  padding: 8px 10px;
  font-size: 0.78rem;
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.04);
  border-right: 1px solid var(--border-color);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.api-path-input {
  flex: 1;
  padding: 8px 10px;
  background: transparent;
  color: var(--text-main);
  border: none;
  font-size: 0.85rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.btn-send-api {
  padding: 8px 18px;
  font-weight: 700;
  font-size: 0.85rem;
  border-radius: 7px;
}

.req-config-panel {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 9px;
  display: flex;
  flex-direction: column;
  height: 195px;
  flex-shrink: 0;
  overflow: hidden;
}

.req-subtabs {
  display: flex;
  gap: 4px;
  padding: 6px 10px;
  border-bottom: 1px solid var(--border-color);
  background: rgba(255, 255, 255, 0.02);
}

.req-subtab-btn {
  font-size: 0.76rem;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 5px;
  background: transparent;
  color: var(--text-muted);
}

.req-subtab-btn.active {
  background: rgba(56, 189, 248, 0.16);
  color: var(--accent-blue);
}

.req-subtab-body {
  flex: 1;
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow: hidden;
}

.kv-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.btn-mini {
  font-size: 0.72rem;
  padding: 3px 8px;
  border-radius: 5px;
  background: var(--bg-input);
  color: var(--accent-blue);
  border: 1px solid var(--border-color);
}

.kv-rows-scroll {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.kv-edit-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.kv-text-input {
  flex: 1;
  padding: 5px 8px;
  border-radius: 5px;
  background: var(--bg-input);
  color: var(--text-main);
  border: 1px solid var(--border-color);
  font-size: 0.8rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.btn-kv-del {
  background: transparent;
  color: var(--text-muted);
  font-size: 1rem;
  padding: 0 6px;
}

.body-editor-wrap {
  height: 100%;
}

.body-type-group {
  display: flex;
  gap: 12px;
}

.api-body-textarea {
  flex: 1;
  width: 100%;
  resize: none;
  padding: 8px;
  border-radius: 6px;
  background: var(--bg-input);
  color: var(--text-main);
  border: 1px solid var(--border-color);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.8rem;
}

.response-panel {
  flex: 1;
  min-height: 0;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 9px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.response-header-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-color);
  background: rgba(255, 255, 255, 0.02);
  flex-wrap: wrap;
}

.response-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.resp-section-title {
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--text-main);
}

.resp-status-badge {
  font-size: 0.75rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 5px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.resp-status-badge.passed {
  background: rgba(52, 211, 153, 0.16);
  color: var(--accent-green);
  border: 1px solid rgba(52, 211, 153, 0.35);
}

.resp-status-badge.warning {
  background: rgba(251, 191, 36, 0.16);
  color: var(--accent-yellow);
  border: 1px solid rgba(251, 191, 36, 0.35);
}

.resp-status-badge.failed {
  background: rgba(248, 113, 113, 0.16);
  color: var(--accent-red);
  border: 1px solid rgba(248, 113, 113, 0.35);
}

.resp-metric-chip {
  font-size: 0.74rem;
  color: var(--text-muted);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.response-search-bar {
  display: flex;
  align-items: center;
  gap: 6px;
}

.response-search-input {
  width: 210px;
  padding: 4px 8px;
  border-radius: 6px;
  background: var(--bg-input);
  color: var(--text-main);
  border: 1px solid var(--border-color);
  font-size: 0.78rem;
}

.match-counter {
  font-size: 0.74rem;
  color: var(--accent-yellow);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  white-space: nowrap;
}

.btn-search-nav {
  padding: 2px 7px;
  border-radius: 4px;
  background: var(--bg-input);
  color: var(--text-main);
  border: 1px solid var(--border-color);
  font-size: 0.74rem;
}

.filter-matches-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 0.73rem;
  color: var(--text-muted);
  cursor: pointer;
}

.resp-headers-drawer {
  max-height: 110px;
  overflow-y: auto;
  padding: 6px 12px;
  border-bottom: 1px solid var(--border-color);
  background: rgba(0, 0, 0, 0.2);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.74rem;
}

.resp-header-item {
  display: flex;
  gap: 6px;
  line-height: 1.4;
}

.rh-key {
  color: var(--accent-blue);
  font-weight: 600;
}

.rh-val {
  color: var(--text-main);
}

.response-body-viewport {
  flex: 1;
  overflow: auto;
  position: relative;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.78rem;
  background: rgba(0, 0, 0, 0.18);
}

.virtual-spacer {
  position: relative;
  width: 100%;
}

.virtual-window {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
}

.resp-line {
  display: flex;
  align-items: center;
  height: 20px;
  line-height: 20px;
  padding: 0 10px;
  white-space: pre;
}

.resp-line.is-match {
  background: rgba(251, 191, 36, 0.16);
}

.resp-line.is-active-match {
  background: rgba(251, 191, 36, 0.35);
  outline: 1px solid var(--accent-yellow);
}

.resp-line-no {
  width: 48px;
  color: var(--text-muted);
  text-align: right;
  padding-right: 12px;
  user-select: none;
  flex-shrink: 0;
  opacity: 0.65;
}

.resp-line-text {
  color: var(--text-main);
}

.response-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 0.85rem;
}
</style>
