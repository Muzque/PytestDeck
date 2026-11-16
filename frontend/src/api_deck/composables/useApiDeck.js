import { ref, computed, watch, nextTick } from 'vue'

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

  const environments = ref([])
  const showEnvModal = ref(false)
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
  const isSending = ref(false)
  const currentResponse = ref(null)

  const isRunningBatch = ref(false)
  const batchSummary = ref(null)

  const isRunningStress = ref(false)
  const stressConfig = ref({
    totalRequests: 20,
    concurrency: 5
  })
  const stressResult = ref(null)

  let autoSaveTimer = null
  let isHydratingRequest = false

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
    createGroupWithNodeId = null,
    groupName = null
  }) => {
    try {
      const res = await fetch('/api/api-deck/nodes/move', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_path: targetPathRef?.value || '',
          node_id: nodeId,
          target_parent_id: targetParentId,
          target_index: targetIndex,
          create_group_with_node_id: createGroupWithNodeId,
          group_name: groupName
        })
      })
      if (res.ok) {
        const data = await res.json()
        apiNodes.value = data.nodes || []
        return data
      }
    } catch (err) {
      console.error('Failed to move/group API node:', err)
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

  const saveEnvironment = async (envPayload) => {
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
        return data.environment
      }
    } catch (err) {
      console.error('Failed to save API environment:', err)
    }
    return null
  }

  const activateEnvironment = async (envId) => {
    if (!envId) return
    try {
      const res = await fetch(`/api/api-deck/environments/${encodeURIComponent(envId)}/activate`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_path: targetPathRef?.value || '' })
      })
      if (res.ok) {
        const data = await res.json()
        environments.value = data.environments || []
      }
    } catch (err) {
      console.error('Failed to activate environment:', err)
    }
  }

  const deleteEnvironment = async (envId) => {
    if (!envId) return
    try {
      const tp = encodeURIComponent(targetPathRef?.value || '')
      const res = await fetch(`/api/api-deck/environments/${encodeURIComponent(envId)}?target_path=${tp}`, {
        method: 'DELETE'
      })
      if (res.ok) {
        const data = await res.json()
        environments.value = data.environments || []
      }
    } catch (err) {
      console.error('Failed to delete environment:', err)
    }
  }

  const sendCurrentRequest = async () => {
    if (isSending.value) return
    isSending.value = true
    try {
      const payload = serializeActiveRequest()
      const res = await fetch('/api/api-deck/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_path: targetPathRef?.value || '',
          node: payload,
          environment: activeEnv.value
        })
      })
      if (res.ok) {
        const data = await res.json()
        currentResponse.value = data.result
        apiNodes.value = data.nodes || apiNodes.value
        if (!activeRequest.value.id && data.result?.node_id) {
          activeRequest.value.id = data.result.node_id
          activeRequestId.value = data.result.node_id
        }
        saveStatus.value = 'saved'
      }
    } catch (err) {
      console.error('Failed to send API request:', err)
    } finally {
      isSending.value = false
    }
  }

  const runSelectedApis = async () => {
    if (isRunningBatch.value) return
    await flushAutoSave()
    isRunningBatch.value = true
    apiActiveTab.value = 'batch'
    try {
      const ids = Array.from(selectedApiIds.value)
      const res = await fetch('/api/api-deck/run-batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_path: targetPathRef?.value || '',
          node_ids: ids,
          environment: activeEnv.value
        })
      })
      if (res.ok) {
        const data = await res.json()
        batchSummary.value = data.batch
        apiNodes.value = data.nodes || apiNodes.value
      }
    } catch (err) {
      console.error('Failed to run batch APIs:', err)
    } finally {
      isRunningBatch.value = false
    }
  }

  const runStressTest = async () => {
    if (isRunningStress.value) return
    isRunningStress.value = true
    try {
      const payload = serializeActiveRequest()
      const res = await fetch('/api/api-deck/stress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_path: targetPathRef?.value || '',
          node: payload,
          environment: activeEnv.value,
          total_requests: Number(stressConfig.value.totalRequests || 20),
          concurrency: Number(stressConfig.value.concurrency || 5)
        })
      })
      if (res.ok) {
        const data = await res.json()
        stressResult.value = data.stress
        saveStatus.value = 'saved'
      }
    } catch (err) {
      console.error('Failed to run stress test:', err)
    } finally {
      isRunningStress.value = false
    }
  }

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
