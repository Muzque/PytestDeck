<script setup>
import { ref, watch, nextTick, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  show: { type: Boolean, default: false },
  envStatus: { type: Object, default: () => ({ ready: true, status: 'ready', message: '' }) },
  logs: { type: String, default: '' }
})

const emit = defineEmits(['close', 'refresh'])

const logContainer = ref(null)
const copied = ref(false)

const copyLogs = async () => {
  if (!props.logs) return
  try {
    await navigator.clipboard.writeText(props.logs)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy logs:', err)
  }
}

const scrollToBottom = () => {
  if (logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
}

watch(
  () => props.logs,
  async () => {
    await nextTick()
    scrollToBottom()
  }
)

const handleKeydown = (e) => {
  if (e.key === 'Escape' && props.show) {
    emit('close')
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  nextTick(scrollToBottom)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="env-modal-overlay" @click.self="emit('close')">
      <div class="env-modal-card" role="dialog" aria-modal="true">
        <!-- Header -->
        <div class="env-modal-header">
          <div class="header-left">
            <span class="modal-icon">⚙️</span>
            <div>
              <h3>Environment Setup Logs</h3>
              <p class="modal-subtitle">
                Target repository container environment preparation (<code>uv sync</code>)
              </p>
            </div>
          </div>
          <div class="header-right">
            <span class="env-status-badge" :class="'env-' + (envStatus?.status || 'ready')">
              <span class="status-dot"></span>
              <span class="status-text">
                {{ envStatus?.status === 'running' ? 'Preparing Env...' : (envStatus?.status === 'failed' ? 'Env Failed' : 'Ready') }}
              </span>
            </span>
            <button class="modal-close-btn" title="Close (Esc)" @click="emit('close')">
              ✕
            </button>
          </div>
        </div>

        <!-- Log Area -->
        <div ref="logContainer" class="env-modal-log-container">
          <pre v-if="logs" class="env-modal-log-text">{{ logs }}</pre>
          <div v-else class="env-modal-empty">
            <span v-if="envStatus?.status === 'running'">Waiting for initial log output...</span>
            <span v-else>No sync logs recorded yet.</span>
          </div>
        </div>

        <!-- Footer -->
        <div class="env-modal-footer">
          <div class="footer-info">
            <span v-if="envStatus?.status === 'running'" class="running-indicator">
              <span class="pulse-indicator"></span> Syncing target dependencies in container...
            </span>
            <span v-else-if="envStatus?.status === 'failed'" class="failed-indicator">
              ⚠️ Dependency installation failed.
            </span>
            <span v-else class="ready-indicator">
              ✓ Target environment ready.
            </span>
          </div>

          <div class="footer-actions">
            <button class="btn btn-secondary btn-sm" @click="emit('refresh')">
              🔄 Refresh
            </button>
            <button 
              class="btn btn-secondary btn-sm" 
              :disabled="!logs" 
              @click="copyLogs"
            >
              {{ copied ? '✓ Copied!' : '📋 Copy Log' }}
            </button>
            <button class="btn btn-primary btn-sm" @click="emit('close')">
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
