import { ref, computed, watch, nextTick } from 'vue'
import { useApiEnvironments } from './useApiEnvironments'
import { useApiExecution } from './useApiExecution'

export function useApiDeck(externalTargetPathRef = null) {
  const internalTargetPath = ref('')
  const targetPathRef = externalTargetPathRef || internalTargetPath
  const activeMode = ref('tests')
  const apiActiveTab = ref('request')

  const initDefaultTargetPath = async () => {
    if (targetPathRef.value) return
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search)
      const fromUrl = params.get('target_path')
      if (fromUrl) {
        targetPathRef.value = fromUrl
        return
      }
    }
    try {
      const res = await fetch('/api/config')
      if (res.ok) {
        const data = await res.json()
        if (data.default_target_path && !targetPathRef.value) {
          targetPathRef.value = data.default_target_path
        }
      }
    } catch {
      // Ignore config fetch error
    }
  }
  initDefaultTargetPath()

  const apiNodes = ref([])
  const selectedApiIds = ref(new Set())
  const activeRequestId = ref(null)

  const activeRequest = ref({
    id: '',
    parent_id: null,
    node_type: 'request',
    name: 'New API Request',
    method: 'GET',
    path: '/api/health',
    query_params: [{ key: '', value: '', enabled: true }],
    headers: [{ key: '', value: '', enabled: true }],
    body_type: 'json',
    body: '',
    expected_status: 200
  })

  const saveStatus = ref('saved')

  let autoSaveTimer = null
  let isHydratingRequest = false

  const clearAutoSaveTimer = () => {
    if (autoSaveTimer) {
      clearTimeout(autoSaveTimer)
      autoSaveTimer = null
    }
  }

  const apiTree = computed(() => {
    const map = new Map()
    const roots = []
    for (const n of apiNodes.value) {
      map.set(n.id, { ...n, children: [] })
    }
    for (const n of apiNodes.value) {
      const item = map.get(n.id)
      if (n.parent_id && map.has(n.parent_id)) {
        map.get(n.parent_id).children.push(item)
      } else {
        roots.push(item)
      }
    }
    return roots
  })

  const selectedApiCount = computed(() => {
    let count = 0
    for (const n of apiNodes.value) {
      if (n.node_type === 'request' && selectedApiIds.value.has(n.id)) {
        count++
      }
    }
    return count
  })

  const hydrateEditorFromNode = (node) => {
    if (!node) return
    isHydratingRequest = true
    activeRequestId.value = node.id
    const qParams = Array.isArray(node.query_params) && node.query_params.length > 0
      ? node.query_params.map((q) => ({ ...q }))
      : [{ key: '', value: '', enabled: true }]
    const hdrs = Array.isArray(node.headers) && node.headers.length > 0
      ? node.headers.map((h) => ({ ...h }))
      : [{ key: '', value: '', enabled: true }]

    activeRequest.value = {
      id: node.id,
      parent_id: node.parent_id || null,
      node_type: 'request',
      name: node.name || 'Untitled API',
      method: node.method || 'GET',
      path: node.path || '',
      query_params: qParams,
      headers: hdrs,
      body_type: node.body_type || 'json',
      body: node.body || '',
      expected_status: Number(node.expected_status || 200)
    }
    nextTick(() => {
      isHydratingRequest = false
    })
  }

  const serializeActiveRequest = () => {
    const req = activeRequest.value
    const cleanParams = (req.query_params || []).filter(
      (q) => String(q.key || '').trim() !== '' || String(q.value || '').trim() !== ''
    )
    const cleanHeaders = (req.headers || []).filter(
      (h) => String(h.key || '').trim() !== '' || String(h.value || '').trim() !== ''
    )
    return {
      id: req.id || undefined,
      parent_id: req.parent_id || null,
      node_type: 'request',
      name: req.name || 'Untitled API',
      method: req.method || 'GET',
      path: req.path || '',
      query_params: cleanParams,
      headers: cleanHeaders,
      body_type: req.body_type || 'json',
      body: req.body || '',
      expected_status: Number(req.expected_status || 200)
    }
  }

  const resetActiveRequestToEmpty = () => {
    isHydratingRequest = true
    activeRequestId.value = null
    activeRequest.value = {
      id: '',
      parent_id: null,
      node_type: 'request',
      name: 'New API Request',
      method: 'GET',
      path: '/api/health',
      query_params: [{ key: '', value: '', enabled: true }],
      headers: [{ key: '', value: '', enabled: true }],
      body_type: 'json',
      body: '',
      expected_status: 200
    }
    nextTick(() => {
      isHydratingRequest = false
    })
  }

  const syncEditorAfterCollectionChange = (nextNodes) => {
    apiNodes.value = nextNodes || []
    selectedApiIds.value = new Set()
    batchSummary.value = null
    currentResponse.value = null
    const existing = activeRequestId.value
      ? apiNodes.value.find((n) => n.id === activeRequestId.value)
      : null
    if (existing) {
      hydrateEditorFromNode(existing)
      return
    }
    const firstReq = apiNodes.value.find((n) => n.node_type === 'request')
    if (firstReq) {
      hydrateEditorFromNode(firstReq)
    } else {
      resetActiveRequestToEmpty()
    }
  }

  const loadApiDeckState = async () => {
    try {
      const tp = encodeURIComponent(targetPathRef?.value || '')
      const res = await fetch(`/api/api-deck/state?target_path=${tp}`)
      if (!res.ok) return
      const data = await res.json()
      environments.value = data.environments || []
      apiNodes.value = data.nodes || []

      const firstReq = apiNodes.value.find((n) => n.node_type === 'request')
      if (firstReq && (!activeRequestId.value || !apiNodes.value.some((n) => n.id === activeRequestId.value))) {
        hydrateEditorFromNode(firstReq)
      } else if (!firstReq && activeRequestId.value && !apiNodes.value.some((n) => n.id === activeRequestId.value)) {
        resetActiveRequestToEmpty()
      }
    } catch (err) {
      console.error('Failed to load API Deck state:', err)
    }
  }

  const flushAutoSave = async () => {
    if (autoSaveTimer) {
      clearTimeout(autoSaveTimer)
      autoSaveTimer = null
    }
    if (!activeRequest.value.id) return null
    saveStatus.value = 'saving'
    try {
      const payload = serializeActiveRequest()
      const res = await fetch('/api/api-deck/nodes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_path: targetPathRef?.value || '',
          node: payload
        })
      })
      if (res.ok) {
        const data = await res.json()
        apiNodes.value = data.nodes || apiNodes.value
        saveStatus.value = 'saved'
        return data.node
      }
    } catch (err) {
      console.error('Failed to auto-save API request:', err)
    }
    saveStatus.value = 'saved'
    return null
  }

  const scheduleAutoSave = () => {
    if (isHydratingRequest || !activeRequest.value.id) return
    saveStatus.value = 'saving'
    // Optimistically sync name/method/path in sidebar list immediately
    const idx = apiNodes.value.findIndex((n) => n.id === activeRequest.value.id)
    if (idx !== -1) {
      apiNodes.value[idx] = {
        ...apiNodes.value[idx],
        name: activeRequest.value.name,
        method: activeRequest.value.method,
        path: activeRequest.value.path,
        expected_status: Number(activeRequest.value.expected_status || 200)
      }
    }
    if (autoSaveTimer) clearTimeout(autoSaveTimer)
    autoSaveTimer = setTimeout(() => {
      flushAutoSave()
    }, 250)
  }

  watch(
    () => [
      activeRequest.value.name,
      activeRequest.value.method,
      activeRequest.value.path,
      activeRequest.value.body_type,
      activeRequest.value.body,
      activeRequest.value.expected_status,
      JSON.stringify(activeRequest.value.query_params),
      JSON.stringify(activeRequest.value.headers)
    ],
    () => {
      if (!isHydratingRequest && activeRequest.value.id) {
        scheduleAutoSave()
      }
    }
  )

  watch(
    () => targetPathRef?.value,
    () => {
      loadApiDeckState()
    },
    { immediate: true }
  )

  const createNewRequest = async (parentId = null) => {
    const prevPayload = activeRequest.value.id ? serializeActiveRequest() : null
    if (autoSaveTimer) {
      clearTimeout(autoSaveTimer)
      autoSaveTimer = null
    }
    const count = apiNodes.value.filter((n) => n.node_type === 'request').length + 1
    const clientId = `api-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`
    const newNode = {
      id: clientId,
      node_type: 'request',
      parent_id: parentId,
      name: `API Request #${count}`,
      method: 'GET',
      path: '/api/health',
      query_params: [],
      headers: [],
      body_type: 'json',
      body: '',
      expected_status: 200
    }
    apiNodes.value = [...apiNodes.value, newNode]
    hydrateEditorFromNode(newNode)
    try {
      if (prevPayload) {
        await fetch('/api/api-deck/nodes', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            target_path: targetPathRef?.value || '',
            node: prevPayload
          })
        })
      }
      const res = await fetch('/api/api-deck/nodes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_path: targetPathRef?.value || '',
          node: activeRequest.value.id === clientId ? serializeActiveRequest() : newNode
        })
      })
      if (res.ok) {
        const data = await res.json()
        if (data.environments) {
          environments.value = data.environments
        }
        if (data.nodes && activeRequest.value.id === clientId) {
          apiNodes.value = data.nodes.map((n) =>
            n.id === clientId
              ? {
                  ...n,
                  name: activeRequest.value.name,
                  method: activeRequest.value.method,
                  path: activeRequest.value.path,
                  expected_status: activeRequest.value.expected_status
                }
              : n
          )
        }
      }
    } catch (err) {
      console.error('Failed to create API request:', err)
    }
  }

  const createNewGroup = async (groupName = 'New API Group') => {
    try {
      const res = await fetch('/api/api-deck/nodes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_path: targetPathRef?.value || '',
          node: {
            node_type: 'group',
            name: groupName
          }
        })
      })
      if (res.ok) {
        const data = await res.json()
        apiNodes.value = data.nodes || []
        if (data.environments) {
          environments.value = data.environments
        }
        return data.node
      }
    } catch (err) {
      console.error('Failed to create API group:', err)
    }
    return null
  }

  const selectRequestForEdit = async (node) => {
    if (!node || node.node_type !== 'request') return
    if (activeRequest.value.id && activeRequest.value.id !== node.id) {
      await flushAutoSave()
    }
    const fresh = apiNodes.value.find((n) => n.id === node.id) || node
    hydrateEditorFromNode(fresh)
  }

  const deleteApiNode = async (nodeId) => {
    if (!nodeId) return
    try {
      const tp = encodeURIComponent(targetPathRef?.value || '')
      const res = await fetch(`/api/api-deck/nodes/${encodeURIComponent(nodeId)}?target_path=${tp}`, {
        method: 'DELETE'
      })
      if (res.ok) {
        const data = await res.json()
        apiNodes.value = data.nodes || []
        const nextSet = new Set(selectedApiIds.value)
        nextSet.delete(nodeId)
        selectedApiIds.value = nextSet
        if (activeRequestId.value === nodeId) {
          const nextReq = apiNodes.value.find((n) => n.node_type === 'request')
          if (nextReq) {
            hydrateEditorFromNode(nextReq)
          } else {
            activeRequestId.value = null
            activeRequest.value.id = ''
          }
        }
      }
    } catch (err) {
      console.error('Failed to delete API node:', err)
    }
  }

  const moveApiNode = async ({
    nodeId,
    targetParentId = null,
    targetIndex = 0,
    targetNodeId = null,
    position = null
  }) => {
    let resolvedIndex = targetIndex
    if (targetNodeId && (position === 'before' || position === 'after')) {
      const parentKey = targetParentId || null
      const siblings = apiNodes.value.filter(
        (n) => (n.parent_id || null) === parentKey && n.id !== nodeId
      )
      const targetIdx = siblings.findIndex((n) => n.id === targetNodeId)
      if (targetIdx !== -1) {
        resolvedIndex = position === 'before' ? targetIdx : targetIdx + 1
      }
    }
    try {
      const res = await fetch('/api/api-deck/nodes/move', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_path: targetPathRef?.value || '',
          node_id: nodeId,
          target_parent_id: targetParentId,
          target_index: resolvedIndex
        })
      })
      if (res.ok) {
        const data = await res.json()
        apiNodes.value = data.nodes || []
        return data
      }
    } catch (err) {
      console.error('Failed to move API node:', err)
    }
    return null
  }

  const renameApiNode = async ({ node, name }) => {
    const trimmed = String(name || '').trim()
    if (!node?.id || !trimmed) return null
    const current = apiNodes.value.find((n) => n.id === node.id) || node
    if (trimmed === current.name) return current

    let payload
    if (activeRequest.value.id === current.id) {
      if (autoSaveTimer) {
        clearTimeout(autoSaveTimer)
        autoSaveTimer = null
      }
      isHydratingRequest = true
      activeRequest.value.name = trimmed
      nextTick(() => {
        isHydratingRequest = false
      })
      payload = serializeActiveRequest()
      payload.name = trimmed
      payload.sort_order = current.sort_order
    } else {
      payload = {
        id: current.id,
        parent_id: current.parent_id || null,
        node_type: current.node_type || 'request',
        name: trimmed,
        sort_order: current.sort_order,
        method: current.method || 'GET',
        path: current.path || '',
        query_params: current.query_params || [],
        headers: current.headers || [],
        body_type: current.body_type || 'json',
        body: current.body ?? '',
        expected_status: Number(current.expected_status || 200)
      }
    }

    try {
      const res = await fetch('/api/api-deck/nodes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_path: targetPathRef?.value || '',
          node: payload
        })
      })
      if (res.ok) {
        const data = await res.json()
        apiNodes.value = data.nodes || apiNodes.value
        if (activeRequest.value.id === current.id && activeRequest.value.name !== trimmed) {
          isHydratingRequest = true
          activeRequest.value.name = trimmed
          nextTick(() => {
            isHydratingRequest = false
          })
        }
        saveStatus.value = 'saved'
        return data.node
      }
    } catch (err) {
      console.error('Failed to rename API node:', err)
    }
    return null
  }

  const toggleSelectApiNode = (node) => {
    if (!node) return
    const next = new Set(selectedApiIds.value)
    const collectLeafIds = (item) => {
      const ids = []
      if (item.node_type === 'request') {
        ids.push(item.id)
      }
      if (item.children && item.children.length > 0) {
        for (const c of item.children) {
          ids.push(...collectLeafIds(c))
        }
      }
      return ids
    }

    const leafIds = collectLeafIds(node)
    if (leafIds.length === 0 && node.node_type === 'group') {
      if (next.has(node.id)) next.delete(node.id)
      else next.add(node.id)
      selectedApiIds.value = next
      return
    }

    const allSelected = leafIds.every((id) => next.has(id))
    if (allSelected) {
      for (const id of leafIds) next.delete(id)
      next.delete(node.id)
    } else {
      for (const id of leafIds) next.add(id)
      if (node.node_type === 'group') next.add(node.id)
    }
    selectedApiIds.value = next
  }

  const clearApiSelections = () => {
    selectedApiIds.value = new Set()
  }

  const {
    environments,
    activeEnv,
    showEnvModal,
    saveEnvironment,
    activateEnvironment,
    deleteEnvironment
  } = useApiEnvironments({
    targetPathRef,
    activeRequest,
    apiNodes,
    flushAutoSave,
    clearAutoSaveTimer,
    syncEditorAfterCollectionChange
  })

  const {
    isSending,
    currentResponse,
    isRunningBatch,
    batchSummary,
    isRunningStress,
    stressConfig,
    stressResult,
    sendCurrentRequest,
    runSelectedApis,
    runStressTest
  } = useApiExecution({
    targetPathRef,
    apiActiveTab,
    activeEnv,
    apiNodes,
    selectedApiIds,
    activeRequestId,
    activeRequest,
    saveStatus,
    serializeActiveRequest,
    flushAutoSave
  })

  return {
    targetPath: targetPathRef,
    activeMode,
    apiActiveTab,
    environments,
    activeEnv,
    showEnvModal,
    apiNodes,
    apiTree,
    selectedApiIds,
    selectedApiCount,
    activeRequestId,
    activeRequest,
    saveStatus,
    isSending,
    currentResponse,
    isRunningBatch,
    batchSummary,
    isRunningStress,
    stressConfig,
    stressResult,
    loadApiDeckState,
    createNewRequest,
    createNewGroup,
    selectRequestForEdit,
    deleteApiNode,
    moveApiNode,
    renameApiNode,
    toggleSelectApiNode,
    clearApiSelections,
    saveEnvironment,
    activateEnvironment,
    deleteEnvironment,
    sendCurrentRequest,
    runSelectedApis,
    runStressTest,
    flushAutoSave
  }
}
