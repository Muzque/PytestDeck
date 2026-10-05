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
  'open-env-logs'
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

      <select v-model="currentTheme" class="theme-select" title="Switch Theme">
        <option v-for="t in themes" :key="t.id" :value="t.id">
          {{ t.label }}
        </option>
      </select>
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
