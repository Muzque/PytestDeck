<script setup>
import { ref, nextTick } from 'vue'
import ApiResponseViewer from './ApiResponseViewer.vue'

const props = defineProps({
  request: { type: Object, required: true },
  activeEnv: { type: Object, default: () => ({}) },
  saveStatus: { type: String, default: 'saved' },
  isSending: { type: Boolean, default: false },
  response: { type: Object, default: null }
})

const emit = defineEmits(['update:request', 'send', 'open-stress'])

const reqSubTab = ref('params')
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

    <ApiResponseViewer :response="response" />
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
</style>
