<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  response: { type: Object, default: null }
})

const showRespHeaders = ref(false)

// Response Quick Search & Virtual Scroll state
const responseSearch = ref('')
const filterMatchedLinesOnly = ref(false)
const activeMatchIdx = ref(0)
const scrollContainer = ref(null)
const scrollTop = ref(0)
const ROW_HEIGHT = 20
const VISIBLE_BUFFER = 60

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
</template>

<style scoped>
.btn-mini {
  font-size: 0.72rem;
  padding: 3px 8px;
  border-radius: 5px;
  background: var(--bg-input);
  color: var(--accent-blue);
  border: 1px solid var(--border-color);
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
