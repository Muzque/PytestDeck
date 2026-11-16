<script setup>
import { useTheme } from '../composables/useTheme'

defineProps({
  targetPath: { type: String, required: true },
  activeSuite: { type: String, required: true },
  availableSuites: { type: Array, required: true },
  envStatus: { type: Object, default: () => ({ ready: true, status: 'ready', message: '' }) }
})

const emit = defineEmits([
  'update:targetPath',
  'update:activeSuite',
  'discover',
  'open-env-logs',
  'switch-mode'
])

const { currentTheme, themes } = useTheme()
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
        <div class="mode-switch-group" role="group" aria-label="Switch UI Mode">
          <button
            id="btn-mode-tests"
            type="button"
            class="mode-switch-btn active"
            title="Pytest / Behave Test Runner"
          >
            🧪 Tests
          </button>
          <button
            id="btn-mode-api"
            type="button"
            class="mode-switch-btn"
            title="Switch to API Caller & Stress Test Deck"
            @click="emit('switch-mode', 'api')"
          >
            ⚡ API Deck
          </button>
          <button
            id="btn-mode-switch"
            type="button"
            class="mode-QuickToggle"
            title="Switch to API Deck"
            @click="emit('switch-mode', 'api')"
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
      <div class="suite-control-row">
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
</style>
