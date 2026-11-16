<script setup>
defineProps({
  targetPath: { type: String, default: '' },
  apiEnvironments: { type: Array, default: () => [] },
  activeApiEnv: { type: Object, default: () => ({}) }
})

const emit = defineEmits([
  'update:targetPath',
  'open-api-env-modal',
  'select-api-env',
  'switch-mode'
])
</script>

<template>
  <header class="deck-header">
    <div class="brand">
      <div class="brand-info">
        <img src="/favicon.svg" alt="PytestDeck Logo" class="brand-logo-img" />
        <h1>PytestDeck</h1>
      </div>

      <div class="header-right-controls">
        <div class="mode-switch-group" role="group" aria-label="Switch UI Mode">
          <button
            id="btn-mode-tests"
            type="button"
            class="mode-switch-btn"
            title="Switch to Pytest / Behave Test Runner"
            @click="emit('switch-mode', 'tests')"
          >
            🧪 Tests
          </button>
          <button
            id="btn-mode-api"
            type="button"
            class="mode-switch-btn active"
            title="API Caller & Stress Test Deck"
          >
            ⚡ API Deck
          </button>
          <button
            id="btn-mode-switch"
            type="button"
            class="mode-QuickToggle"
            title="Switch back to Tests"
            @click="emit('switch-mode', 'tests')"
          >
            ⇄
          </button>
        </div>
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
      <div class="suite-control-row api-env-row">
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
