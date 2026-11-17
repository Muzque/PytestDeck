import { ref } from 'vue'

export function useApiExecution({
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
}) {
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
  }
}
