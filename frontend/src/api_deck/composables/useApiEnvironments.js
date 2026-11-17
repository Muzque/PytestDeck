import { ref, computed } from 'vue'

export function useApiEnvironments({
  targetPathRef,
  activeRequest,
  apiNodes,
  flushAutoSave,
  clearAutoSaveTimer,
  syncEditorAfterCollectionChange
}) {
  const environments = ref([])
  const showEnvModal = ref(false)

  const activeEnv = computed(() => {
    const found = environments.value.find((e) => e.is_active)
    if (found) return found
    if (environments.value.length > 0) return environments.value[0]
    return {
      id: '',
      name: 'Default (Current Host)',
      base_url: typeof window !== 'undefined' ? window.location.origin : 'http://127.0.0.1:9388',
      auth_type: 'none',
      auth_config: {},
      default_headers: [],
      is_active: true
    }
  })

  const saveEnvironment = async (envPayload) => {
    const prevEnvId = activeEnv.value?.id || ''
    const isSwitchingToNewActive = Boolean(envPayload?.is_active) && envPayload?.id !== prevEnvId
    if (isSwitchingToNewActive && activeRequest.value.id) {
      await flushAutoSave()
    }
    try {
      const res = await fetch('/api/api-deck/environments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_path: targetPathRef?.value || '',
          environment: envPayload
        })
      })
      if (res.ok) {
        const data = await res.json()
        environments.value = data.environments || []
        if (Array.isArray(data.nodes)) {
          if (isSwitchingToNewActive) {
            syncEditorAfterCollectionChange(data.nodes)
          } else {
            apiNodes.value = data.nodes
          }
        }
        return data.environment
      }
    } catch (err) {
      console.error('Failed to save API environment:', err)
    }
    return null
  }

  const activateEnvironment = async (envId) => {
    if (!envId) return
    if (activeRequest.value.id) {
      await flushAutoSave()
    }
    try {
      const res = await fetch(`/api/api-deck/environments/${encodeURIComponent(envId)}/activate`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_path: targetPathRef?.value || '' })
      })
      if (res.ok) {
        const data = await res.json()
        environments.value = data.environments || []
        syncEditorAfterCollectionChange(data.nodes || [])
      }
    } catch (err) {
      console.error('Failed to activate environment:', err)
    }
  }

  const deleteEnvironment = async (envId) => {
    if (!envId) return
    clearAutoSaveTimer()
    try {
      const tp = encodeURIComponent(targetPathRef?.value || '')
      const res = await fetch(`/api/api-deck/environments/${encodeURIComponent(envId)}?target_path=${tp}`, {
        method: 'DELETE'
      })
      if (res.ok) {
        const data = await res.json()
        environments.value = data.environments || []
        syncEditorAfterCollectionChange(data.nodes || [])
      }
    } catch (err) {
      console.error('Failed to delete environment:', err)
    }
  }

  return {
    environments,
    activeEnv,
    showEnvModal,
    saveEnvironment,
    activateEnvironment,
    deleteEnvironment
  }
}
