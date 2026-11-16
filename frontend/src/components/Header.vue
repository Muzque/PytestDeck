<script setup>
import { useTheme } from '../composables/useTheme'

const props = defineProps({
  targetPath: { type: String, required: true },
  activeSuite: { type: String, required: true },
  availableSuites: { type: Array, required: true },
  envStatus: { type: Object, default: () => ({ ready: true, status: 'ready', message: '' }) },
  activeMode: { type: String, default: 'tests' },
  apiEnvironments: { type: Array, default: () => [] },
  activeApiEnv: { type: Object, default: () => ({}) }
})

const emit = defineEmits([
  'update:targetPath',
  'update:activeSuite',
  'update:activeMode',
  'discover',
  'open-env-logs',
  'open-api-env-modal',
  'select-api-env'
])

const { currentTheme, themes } = useTheme()

const toggleMode = () => {
  emit('update:activeMode', props.activeMode === 'api' ? 'tests' : 'api')
}
</script>

<template>
  <header class="deck-header">
    <div class="brand">
      <div class="brand-info">
        <img src="/favicon.svg" alt="PytestDeck Logo" class="brand-logo-img" />
        <h1>PytestDeck</h1>
        <span 
          class="env-status-badge" 
          :class="'env-' + (envStatus?.status || 'ready')"
          :title="(envStatus?.message || 'Target environment ready') + ' (Click to view logs)'"
          role="button"
          tabindex="0"
          @click="emit('open-env-logs')"
          @keydown.enter="emit('open-env-logs')"
        >
          <span class="status-dot"></span>
          <span class="status-text">
            {{ envStatus?.status === 'running' ? 'Preparing...' : (envStatus?.status === 'failed' ? 'Failed' : 'Ready') }}
          </span>
        </span>
      </div>

      <div class="header-right-controls">
        <!-- Switch button between Tests UI and API Caller UI -->
        <div class="mode-switch-group" role="group" aria-label="Switch UI Mode">
          <button
            id="btn-mode-tests"
            type="button"
            class="mode-switch-btn"
            :class="{ active: activeMode === 'tests' }"
            title="Switch to Pytest / Behave Test Runner"
            @click="emit('update:activeMode', 'tests')"
          >
            🧪 Tests
          </button>
          <button
            id="btn-mode-api"
            type="button"
            class="mode-switch-btn"
            :class="{ active: activeMode === 'api' }"
            title="Switch to API Caller & Stress Test Deck"
            @click="emit('update:activeMode', 'api')"
          >
            ⚡ API Deck
          </button>
          <button
            id="btn-mode-switch"
            type="button"
            class="mode-QuickToggle"
            :title="activeMode === 'api' ? 'Switch back to Tests' : 'Switch to API Deck'"
            @click="toggleMode"
          >
            ⇄
          </button>
        </div>

        <select v-model="currentTheme" class="theme-select" title="Switch Theme">
          <option v-for="t in themes" :key="t.id" :value="t.id">
            {{ t.label }}
          </option>
        </select>
      </div>
    </div>

    <div class="target-controls">
      <input 
        :value="targetPath" 
        type="text" 
        class="path-input" 
        placeholder="Target Repo Path..."
        title="Target Repository Root Path"
        @input="emit('update:targetPath', $event.target.value)"
      />
      <div v-if="activeMode === 'tests'" class="suite-control-row">
        <select 
          :value="activeSuite" 
          class="suite-select" 
          title="Select Active Test Suite"
          @change="emit('update:activeSuite', $event.target.value); emit('discover')"
        >
          <option v-for="s in availableSuites" :key="s.path" :value="s.path">
            {{ s.label }}
          </option>
        </select>
      </div>
      <div v-else class="suite-control-row api-env-row">
        <select
          id="api-env-select"
          :value="activeApiEnv?.id || ''"
          class="suite-select api-env-select"
          title="Select Active API Environment"
          @change="emit('select-api-env', $event.target.value)"
        >
          <option v-if="apiEnvironments.length === 0" value="">
            {{ activeApiEnv?.name || 'Default Environment' }} ({{ activeApiEnv?.base_url || 'http://127.0.0.1:9388' }})
          </option>
          <option v-for="env in apiEnvironments" :key="env.id" :value="env.id">
            {{ env.name }} — {{ env.base_url || '(No Addr)' }}
          </option>
        </select>
        <button
          id="btn-api-env-config"
          type="button"
          class="btn-api-env-config"
          title="Configure Address, Auth & Default Headers (Saved in DB)"
          @click="emit('open-api-env-modal')"
        >
          ⚙️ Addr &amp; Auth
        </button>
      </div>
    </div>
  </header>
</template>

<style scoped>
.header-right-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mode-switch-group {
  display: inline-flex;
  align-items: center;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 2px;
  gap: 2px;
}

.mode-switch-btn {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 6px;
  background: transparent;
  color: var(--text-muted);
  white-space: nowrap;
}

.mode-switch-btn:hover {
  color: var(--text-main);
}

.mode-switch-btn.active {
  background: var(--accent-blue);
  color: #0b0f19;
  font-weight: 700;
}

.mode-QuickToggle {
  font-size: 0.75rem;
  padding: 4px 6px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-muted);
}

.mode-QuickToggle:hover {
  color: var(--accent-blue);
  background: rgba(56, 189, 248, 0.15);
}

.api-env-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.api-env-select {
  flex: 1;
  min-width: 0;
}

.btn-api-env-config {
  font-size: 0.76rem;
  font-weight: 600;
  padding: 6px 10px;
  border-radius: 6px;
  background: rgba(56, 189, 248, 0.14);
  color: var(--accent-blue);
  border: 1px solid rgba(56, 189, 248, 0.35);
  white-space: nowrap;
  flex-shrink: 0;
}

.btn-api-env-config:hover {
  background: rgba(56, 189, 248, 0.24);
}
</style>
