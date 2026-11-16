<script setup>
import { ref } from 'vue'
import ApiHeader from './components/ApiHeader.vue'
import ApiExplorer from './components/ApiExplorer.vue'
import ApiRequestView from './components/ApiRequestView.vue'
import ApiStressTestView from './components/ApiStressTestView.vue'
import ApiBatchSummaryView from './components/ApiBatchSummaryView.vue'
import ApiEnvModal from './components/ApiEnvModal.vue'
import { useApiDeck } from './composables/useApiDeck'

const emit = defineEmits(['switch-mode'])

const {
  targetPath,
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
  runStressTest
} = useApiDeck()

const onInspectBatchResult = (item) => {
  const node = apiNodes.value.find((n) => n.id === item.node_id)
  if (node) {
    selectRequestForEdit(node)
  }
  currentResponse.value = item
  apiActiveTab.value = 'request'
}

const sidebarWidth = ref(480)
const isResizing = ref(false)

const startResizing = () => {
  isResizing.value = true
  const onMove = (e) => {
    sidebarWidth.value = Math.max(280, Math.min(1400, e.clientX))
  }
  const onUp = () => {
    isResizing.value = false
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
  }
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}
</script>

<template>
  <div class="deck-app">
    <aside class="deck-sidebar" :style="{ width: sidebarWidth + 'px' }">
      <ApiHeader
        v-model:targetPath="targetPath"
        :apiEnvironments="environments"
        :activeApiEnv="activeEnv"
        @open-api-env-modal="showEnvModal = true"
        @select-api-env="activateEnvironment"
        @switch-mode="emit('switch-mode', $event)"
      />

      <ApiExplorer
        :apiTree="apiTree"
        :selectedIds="selectedApiIds"
        :selectedCount="selectedApiCount"
        :activeRequestId="activeRequestId"
        :isRunningBatch="isRunningBatch"
        @new-request="createNewRequest(); apiActiveTab = 'request'"
        @new-group="createNewGroup()"
        @select-request="selectRequestForEdit($event); apiActiveTab = 'request'"
        @toggle-check="toggleSelectApiNode"
        @clear-selection="clearApiSelections"
        @delete-node="deleteApiNode"
        @drop-node="moveApiNode"
        @run-selected="runSelectedApis"
      />

      <div 
        class="sidebar-resizer" 
        :class="{ 'is-active': isResizing }"
        @mousedown.prevent="startResizing"
        title="Drag to resize explorer sidebar (up to 1400px)"
      ></div>
    </aside>

    <main class="deck-main">
      <div class="tabs-header">
        <button
          id="tab-api-request"
          class="tab-btn"
          :class="{ active: apiActiveTab === 'request' }"
          @click="apiActiveTab = 'request'"
        >
          Request &amp; Response
        </button>
        <button
          id="tab-api-stress"
          class="tab-btn"
          :class="{ active: apiActiveTab === 'stress' }"
          @click="apiActiveTab = 'stress'"
        >
          Parallel / Stress Test
        </button>
        <button
          id="tab-api-batch"
          class="tab-btn"
          :class="{ active: apiActiveTab === 'batch' }"
          @click="apiActiveTab = 'batch'"
        >
          Batch Run Results
        </button>
      </div>

      <div class="tab-content">
        <div v-show="apiActiveTab === 'request'" class="tab-pane">
          <ApiRequestView
            v-model:request="activeRequest"
            :activeEnv="activeEnv"
            :saveStatus="saveStatus"
            :isSending="isSending"
            :response="currentResponse"
            @send="sendCurrentRequest"
            @open-stress="apiActiveTab = 'stress'"
          />
        </div>

        <div v-show="apiActiveTab === 'stress'" class="tab-pane">
          <ApiStressTestView
            v-model:stressConfig="stressConfig"
            :request="activeRequest"
            :activeEnv="activeEnv"
            :stressResult="stressResult"
            :isRunningStress="isRunningStress"
            @run-stress="runStressTest"
          />
        </div>

        <div v-show="apiActiveTab === 'batch'" class="tab-pane">
          <ApiBatchSummaryView
            :batchSummary="batchSummary"
            :isRunningBatch="isRunningBatch"
            @inspect-result="onInspectBatchResult"
          />
        </div>
      </div>
    </main>

    <ApiEnvModal
      :show="showEnvModal"
      :environments="environments"
      :activeEnv="activeEnv"
      @close="showEnvModal = false"
      @save="saveEnvironment"
      @activate="activateEnvironment"
      @delete="deleteEnvironment"
    />
  </div>
</template>
