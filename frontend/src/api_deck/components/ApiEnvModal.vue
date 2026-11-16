<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  show: { type: Boolean, default: false },
  environments: { type: Array, default: () => [] },
  activeEnv: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['close', 'save', 'activate', 'delete'])

const form = ref({
  id: '',
  name: 'Local Environment',
  base_url: 'http://127.0.0.1:9388',
  auth_type: 'none',
  auth_config: {
    token: '',
    username: '',
    password: '',
    key: 'X-API-Key',
    value: '',
    in: 'header'
  },
  default_headers: [{ key: '', value: '', enabled: true }],
  is_active: true
})

const savedNotice = ref(false)

const loadEnvIntoForm = (env) => {
  const cfg = env?.auth_config || {}
  const hdrs = Array.isArray(env?.default_headers) && env.default_headers.length > 0
    ? env.default_headers.map((h) => ({ ...h }))
    : [{ key: '', value: '', enabled: true }]
  form.value = {
    id: env?.id || '',
    name: env?.name || 'Local Environment',
    base_url: env?.base_url ?? (typeof window !== 'undefined' ? window.location.origin : 'http://127.0.0.1:9388'),
    auth_type: env?.auth_type || 'none',
    auth_config: {
      token: cfg.token || '',
      username: cfg.username || '',
      password: cfg.password || '',
      key: cfg.key || 'X-API-Key',
      value: cfg.value || '',
      in: cfg.in || 'header'
    },
    default_headers: hdrs,
    is_active: true
  }
}

watch(
  () => props.show,
  (visible) => {
    if (visible) {
      loadEnvIntoForm(props.activeEnv)
      savedNotice.value = false
    }
  }
)

const startNewEnv = () => {
  loadEnvIntoForm({
    id: '',
    name: `Environment #${props.environments.length + 1}`,
    base_url: typeof window !== 'undefined' ? window.location.origin : 'http://127.0.0.1:9388',
    auth_type: 'none',
    auth_config: {},
    default_headers: [],
    is_active: true
  })
}

const addHeaderRow = () => {
  form.value.default_headers.push({ key: '', value: '', enabled: true })
}

const removeHeaderRow = (idx) => {
  form.value.default_headers.splice(idx, 1)
  if (form.value.default_headers.length === 0) {
    form.value.default_headers.push({ key: '', value: '', enabled: true })
  }
}

const onSave = () => {
  const cleanHeaders = form.value.default_headers.filter(
    (h) => String(h.key || '').trim() !== '' || String(h.value || '').trim() !== ''
  )
  emit('save', {
    id: form.value.id || undefined,
    name: form.value.name,
    base_url: form.value.base_url,
    auth_type: form.value.auth_type,
    auth_config: { ...form.value.auth_config },
    default_headers: cleanHeaders,
    is_active: true
  })
  savedNotice.value = true
  setTimeout(() => {
    savedNotice.value = false
  }, 1800)
}
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="modal-overlay" @click.self="emit('close')">
      <div class="modal-card api-env-modal" role="dialog" aria-label="API Environment & Auth Settings">
        <div class="modal-header">
          <div>
            <h3>API Address &amp; Authentication</h3>
            <p class="modal-subtitle">Saved in repository SQLite database (.pytestdeck/&lt;repo&gt;/history.db)</p>
          </div>
          <button type="button" class="btn-modal-close" @click="emit('close')">×</button>
        </div>

        <div class="modal-body">
          <!-- Saved Environments Switcher Row -->
          <div class="env-list-bar">
            <div class="env-chips">
              <button
                v-for="env in environments"
                :key="env.id"
                type="button"
                class="env-chip-btn"
                :class="{ active: form.id === env.id }"
                @click="loadEnvIntoForm(env)"
              >
                {{ env.name }}
              </button>
            </div>
            <button id="btn-new-env-profile" type="button" class="btn-small-outline" @click="startNewEnv">
              + New Profile
            </button>
          </div>

          <div class="form-grid-2">
            <div class="form-group">
              <label for="api-env-name-input">Environment Name</label>
              <input
                id="api-env-name-input"
                v-model="form.name"
                type="text"
                class="modal-input"
                placeholder="e.g. Local Dev, Staging..."
              />
            </div>

            <div class="form-group">
              <label for="api-env-addr-input">Server Address (Base URL)</label>
              <input
                id="api-env-addr-input"
                v-model="form.base_url"
                type="text"
                class="modal-input"
                placeholder="http://127.0.0.1:9388"
              />
            </div>
          </div>

          <!-- Auth Section -->
          <div class="form-group">
            <label for="api-env-auth-type">Authentication Scheme</label>
            <select id="api-env-auth-type" v-model="form.auth_type" class="modal-input">
              <option value="none">No Auth</option>
              <option value="bearer">Bearer Token (JWT / OAuth)</option>
              <option value="basic">Basic Auth (Username &amp; Password)</option>
              <option value="api_key">API Key (Header or Query Param)</option>
            </select>
          </div>

          <div v-if="form.auth_type === 'bearer'" class="auth-detail-box">
            <label for="api-env-bearer-token">Bearer Token</label>
            <input
              id="api-env-bearer-token"
              v-model="form.auth_config.token"
              type="text"
              class="modal-input"
              placeholder="eyJhbGciOiJIUzI1NiIs..."
            />
          </div>

          <div v-else-if="form.auth_type === 'basic'" class="auth-detail-box form-grid-2">
            <div>
              <label for="api-env-basic-user">Username</label>
              <input
                id="api-env-basic-user"
                v-model="form.auth_config.username"
                type="text"
                class="modal-input"
                placeholder="admin"
              />
            </div>
            <div>
              <label for="api-env-basic-pass">Password</label>
              <input
                id="api-env-basic-pass"
                v-model="form.auth_config.password"
                type="password"
                class="modal-input"
                placeholder="••••••••"
              />
            </div>
          </div>

          <div v-else-if="form.auth_type === 'api_key'" class="auth-detail-box form-grid-3">
            <div>
              <label>Key Name</label>
              <input
                v-model="form.auth_config.key"
                type="text"
                class="modal-input"
                placeholder="X-API-Key"
              />
            </div>
            <div>
              <label>Key Value</label>
              <input
                v-model="form.auth_config.value"
                type="text"
                class="modal-input"
                placeholder="secret-api-key"
              />
            </div>
            <div>
              <label>Pass By</label>
              <select v-model="form.auth_config.in" class="modal-input">
                <option value="header">Header</option>
                <option value="query">Query Param</option>
              </select>
            </div>
          </div>

          <!-- Default Headers -->
          <div class="form-group">
            <div class="section-label-row">
              <label>Default Headers</label>
              <button type="button" class="btn-small-outline" @click="addHeaderRow">+ Add Header</button>
            </div>
            <div class="kv-list">
              <div v-for="(h, idx) in form.default_headers" :key="idx" class="kv-row">
                <input v-model="h.enabled" type="checkbox" class="kv-check" />
                <input v-model="h.key" type="text" class="modal-input kv-input" placeholder="Header Name" />
                <input v-model="h.value" type="text" class="modal-input kv-input" placeholder="Header Value" />
                <button type="button" class="btn-kv-remove" @click="removeHeaderRow(idx)">×</button>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button
            v-if="form.id"
            type="button"
            class="btn btn-danger"
            @click="emit('delete', form.id)"
          >
            Delete Profile
          </button>
          <span v-if="savedNotice" class="saved-badge" data-testid="env-saved-badge">✓ Saved to DB</span>
          <div class="footer-right">
            <button type="button" class="btn-secondary-modal" @click="emit('close')">Close</button>
            <button id="btn-save-api-env" type="button" class="btn btn-primary" @click="onSave">
              Save Environment
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: var(--bg-modal-overlay);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1500;
}

.api-env-modal {
  width: min(640px, 94vw);
  max-height: 88vh;
  background: var(--bg-modal);
  border: 1px solid var(--border-modal);
  border-radius: 14px;
  box-shadow: var(--shadow-modal);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  background: var(--bg-modal-header);
  border-bottom: 1px solid var(--border-color);
}

.modal-header h3 {
  font-size: 1rem;
  color: var(--text-main);
}

.modal-subtitle {
  font-size: 0.74rem;
  color: var(--text-muted);
  margin-top: 2px;
}

.btn-modal-close {
  background: transparent;
  color: var(--text-muted);
  font-size: 1.4rem;
  line-height: 1;
  padding: 2px 8px;
}

.modal-body {
  padding: 16px 18px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.env-list-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.env-chips {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.env-chip-btn {
  font-size: 0.75rem;
  padding: 4px 10px;
  border-radius: 6px;
  background: var(--bg-input);
  color: var(--text-muted);
  border: 1px solid var(--border-color);
}

.env-chip-btn.active {
  background: rgba(56, 189, 248, 0.2);
  color: var(--accent-blue);
  border-color: var(--accent-blue);
  font-weight: 600;
}

.form-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.form-grid-3 {
  display: grid;
  grid-template-columns: 1fr 1fr 120px;
  gap: 10px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.form-group label,
.auth-detail-box label {
  font-size: 0.76rem;
  font-weight: 600;
  color: var(--text-muted);
}

.modal-input {
  width: 100%;
  padding: 7px 10px;
  font-size: 0.82rem;
  border-radius: 6px;
  background: var(--bg-input);
  color: var(--text-main);
  border: 1px solid var(--border-color);
}

.auth-detail-box {
  padding: 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-color);
}

.section-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.btn-small-outline {
  font-size: 0.73rem;
  padding: 3px 8px;
  border-radius: 5px;
  background: transparent;
  color: var(--accent-blue);
  border: 1px solid rgba(56, 189, 248, 0.35);
}

.kv-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.kv-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.kv-input {
  flex: 1;
}

.btn-kv-remove {
  background: transparent;
  color: var(--text-muted);
  font-size: 1.1rem;
  padding: 2px 6px;
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 18px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-modal-header);
}

.footer-right {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.btn-secondary-modal {
  padding: 6px 12px;
  border-radius: 6px;
  background: var(--bg-input);
  color: var(--text-main);
  border: 1px solid var(--border-color);
  font-size: 0.82rem;
}

.saved-badge {
  color: var(--accent-green);
  font-size: 0.8rem;
  font-weight: 600;
  margin-left: 12px;
}
</style>
