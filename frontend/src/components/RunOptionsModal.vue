<script setup>
import { ref, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  show: { type: Boolean, default: false },
  markerFilter: { type: String, default: '' },
  extraArgs: { type: String, default: '' }
})

const emit = defineEmits(['close', 'update:markerFilter', 'update:extraArgs'])

// Local drafts so Cancel discards edits
const draftMarker = ref('')
const draftExtra = ref('')
const markerInputRef = ref(null)

watch(() => props.show, async (visible) => {
  if (visible) {
    draftMarker.value = props.markerFilter
    draftExtra.value = props.extraArgs
    await nextTick()
    markerInputRef.value?.focus()
  }
})

const apply = () => {
  emit('update:markerFilter', draftMarker.value.trim())
  emit('update:extraArgs', draftExtra.value.trim())
  emit('close')
}

const clearAll = () => {
  draftMarker.value = ''
  draftExtra.value = ''
}

const onKeydown = (e) => {
  if (!props.show) return
  if (e.key === 'Escape') emit('close')
}

onMounted(() => document.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="ro-overlay" @click.self="emit('close')">
      <div class="ro-card" role="dialog" aria-labelledby="ro-title">
        <div class="ro-header">
          <div class="ro-title-wrap">
            <span class="ro-icon">⚙️</span>
            <div>
              <h3 id="ro-title">Run Options</h3>
              <p class="ro-subtitle">Applied to every test run from this deck</p>
            </div>
          </div>
          <button class="ro-close" title="Close (Esc)" @click="emit('close')">✕</button>
        </div>

        <form class="ro-body" @submit.prevent="apply">
          <label class="ro-field">
            <span class="ro-label">Marker expression</span>
            <input
              id="run-options-marker"
              ref="markerInputRef"
              v-model="draftMarker"
              class="ro-input"
              placeholder="Marker (e.g. smoke and not slow)"
            />
            <span class="ro-hint">Passed to pytest as <code>-m "&lt;expr&gt;"</code></span>
          </label>

          <label class="ro-field">
            <span class="ro-label">Extra flags</span>
            <input
              id="run-options-extra"
              v-model="draftExtra"
              class="ro-input"
              placeholder="Extra flags (e.g. -v --tb=short -s)"
            />
            <span class="ro-hint">Appended verbatim to the pytest / behave command</span>
          </label>

          <div class="ro-footer">
            <button type="button" class="btn btn-secondary ro-clear" @click="clearAll">Clear</button>
            <div class="ro-footer-right">
              <button type="button" class="btn btn-secondary" @click="emit('close')">Cancel</button>
              <button id="run-options-apply" type="submit" class="btn btn-primary">Apply</button>
            </div>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.ro-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(8px);
  animation: ro-fade 0.18s ease-out;
}

.ro-card {
  width: 100%;
  max-width: 520px;
  background: var(--bg-card);
  backdrop-filter: var(--glass-backdrop);
  border: 1px solid var(--border-color);
  border-radius: var(--glass-border-radius);
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
  overflow: hidden;
  animation: ro-pop 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.ro-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.ro-title-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ro-icon { font-size: 1.4rem; }

.ro-header h3 {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--text-main);
}

.ro-subtitle {
  margin: 2px 0 0;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.ro-close {
  background: transparent;
  color: var(--text-muted);
  font-size: 1.1rem;
  padding: 4px 8px;
  border-radius: 6px;
}

.ro-close:hover {
  color: var(--text-main);
  background: rgba(255, 255, 255, 0.1);
}

.ro-body {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 20px;
}

.ro-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ro-label {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--text-main);
}

.ro-input {
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  padding: 9px 12px;
  border-radius: 8px;
  font-size: 0.88rem;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.ro-input:focus {
  border-color: var(--border-hover);
  box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2);
}

.ro-hint {
  font-size: 0.74rem;
  color: var(--text-muted);
}

.ro-hint code {
  background: var(--bg-input);
  padding: 1px 5px;
  border-radius: 4px;
}

.ro-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 4px;
}

.ro-footer-right {
  display: flex;
  gap: 8px;
}

@keyframes ro-fade {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes ro-pop {
  from { opacity: 0; transform: translateY(8px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
</style>
