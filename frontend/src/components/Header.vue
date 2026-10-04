<script setup>
import { useTheme } from '../composables/useTheme'

defineProps({
  targetPath: { type: String, required: true },
  activeSuite: { type: String, required: true },
  availableSuites: { type: Array, required: true },
  isDiscovering: { type: Boolean, default: false },
  isRunning: { type: Boolean, default: false },
  selectedCount: { type: Number, default: 0 },
  envStatus: { type: Object, default: () => ({ ready: true, status: 'ready', message: '' }) }
})

const emit = defineEmits([
  'update:targetPath',
  'update:activeSuite',
  'discover',
  'run',
  'stop',
  'open-env-logs'
])

const { currentTheme, themes } = useTheme()
</script>

<template>
  <header class="deck-header">
    <div class="brand">
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
          {{ envStatus?.status === 'running' ? 'Preparing Env...' : (envStatus?.status === 'failed' ? 'Env Failed' : 'Ready') }}
        </span>
      </span>
    </div>

    <div class="target-controls">
      <input 
        :value="targetPath" 
        type="text" 
        class="path-input" 
        placeholder="Target Repo Path..."
        @input="emit('update:targetPath', $event.target.value)"
      />
      <select 
        :value="activeSuite" 
        class="suite-select" 
        @change="emit('update:activeSuite', $event.target.value); emit('discover')"
      >
        <option v-for="s in availableSuites" :key="s.path" :value="s.path">
          {{ s.label }}
        </option>
      </select>
      <button class="btn btn-secondary" :disabled="isDiscovering" @click="emit('discover')">
        {{ isDiscovering ? 'Scanning...' : 'Refresh Tree' }}
      </button>
    </div>

    <div class="run-actions">
      <select v-model="currentTheme" class="theme-select" title="Switch Theme">
        <option v-for="t in themes" :key="t.id" :value="t.id">
          {{ t.label }}
        </option>
      </select>

      <button v-if="!isRunning" class="btn btn-primary" @click="emit('run')">
        ▶ Run Selected ({{ selectedCount }})
      </button>
      <button v-else class="btn btn-danger" @click="emit('stop')">
        ⏹ Stop Execution
      </button>
    </div>
  </header>
</template>
