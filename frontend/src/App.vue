<script setup>
import Header from './components/Header.vue'
import TestExplorer from './components/TestExplorer.vue'
import TerminalView from './components/TerminalView.vue'
import MetricsSummary from './components/MetricsSummary.vue'
import RunHistory from './components/RunHistory.vue'
import EnvLogModal from './components/EnvLogModal.vue'
import TestDetailView from './components/TestDetailView.vue'
import ApiExplorer from './components/ApiExplorer.vue'
import ApiRequestView from './components/ApiRequestView.vue'
import ApiStressTestView from './components/ApiStressTestView.vue'
import ApiBatchSummaryView from './components/ApiBatchSummaryView.vue'
import ApiEnvModal from './components/ApiEnvModal.vue'
import { useTestRunner } from './composables/useTestRunner'
import { useApiDeck } from './composables/useApiDeck'
import { useTooltip } from './composables/useTooltip'
import { useSidebarResize } from './composables/useSidebarResize'

const {
  targetPath,
  activeSuite,
  availableSuites,
  isDiscovering,
  isRunning,
  liveRunProgress,
  envStatus,
  envLogs,
  showEnvLogModal,
  fetchEnvLogs,
  testTree,
  selectedNodes,
  selectedCount,
  failedCount,
  runFailedTests,
  activeTab,

  logs,
  exitCode,
  summary,
  markerFilter,
  extraArgs,
  runHistory,
  selectedHistoryId,
  discoverTests,
  toggleSelectNode,
  clearSelections,
  runTests,
  stopTests,
  selectHistoryItem,
  selectedTestDetail,
  isLoadingDetail,
  isDetailSuite,
  singleSelectedNode,
  currentMethodOutput,
  runSingleMethod,
  clearMethodOutput,
  clearAllMethodOutputs,
  pruneMergedAndDeletedBranches,
  methodOutputs
} = useTestRunner()

const {
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
} = useApiDeck(targetPath)

const onInspectBatchResult = (item) => {
  const node = apiNodes.value.find((n) => n.id === item.node_id)
  if (node) {
    selectRequestForEdit(node)
  }
  currentResponse.value = item
  apiActiveTab.value = 'request'
}

const { sidebarWidth, isResizing, startResizing } = useSidebarResize(480)
const { activeTooltip } = useTooltip()
</script>

<template>
  <div class="deck-app">
    <!-- Left-hand Sidebar: Appbar Controls + Test Explorer or API Explorer -->
    <aside class="deck-sidebar" :style="{ width: sidebarWidth + 'px' }">
      <Header
        v-model:targetPath="targetPath"
        v-model:activeSuite="activeSuite"
        v-model:activeMode="activeMode"
        :availableSuites="availableSuites"
        :envStatus="envStatus"
        :apiEnvironments="environments"
        :activeApiEnv="activeEnv"
        @discover="discoverTests"
        @open-env-logs="showEnvLogModal = true; fetchEnvLogs()"
        @open-api-env-modal="showEnvModal = true"
        @select-api-env="activateEnvironment"
      />

      <TestExplorer
        v-if="activeMode === 'tests'"
        :activeSuite="activeSuite"
        :isDiscovering="isDiscovering"
        :isRunning="isRunning"
        :selectedCount="selectedCount"
        :failedCount="failedCount"
        v-model:markerFilter="markerFilter"
        v-model:extraArgs="extraArgs"
        :testTree="testTree"
        :selectedNodes="selectedNodes"
        :methodOutputs="methodOutputs"
        @toggle-select="toggleSelectNode"
        @clear-selection="clearSelections"
        @discover="discoverTests"
        @run="runTests"
        @run-failed="runFailedTests"
        @stop="stopTests"
        @clear-all-history="clearAllMethodOutputs"
        @prune-branches="pruneMergedAndDeletedBranches"
      />

      <ApiExplorer
        v-else
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

      <!-- Drag handle to adjust sidebar width -->
      <div 
        class="sidebar-resizer" 
        :class="{ 'is-active': isResizing }"
        @mousedown.prevent="startResizing"
        title="Drag to resize explorer sidebar (up to 1400px)"
      ></div>
    </aside>

    <!-- Right Main: Full-Height Tabbed Views -->
    <main class="deck-main">
      <!-- TEST DECK MODE -->
      <template v-if="activeMode === 'tests'">
        <div class="tabs-header">
          <button 
            class="tab-btn" 
            :class="{ active: activeTab === 'live' }"
            @click="activeTab = 'live'"
          >
            Terminal Output
          </button>
          <button 
            v-if="isDetailSuite && singleSelectedNode"
            class="tab-btn tab-btn-detail" 
            :class="{ active: activeTab === 'detail' }"
            @click="activeTab = 'detail'"
          >
            <span class="tab-indicator-dot"></span>
            Detail Info
          </button>
          <button 
            class="tab-btn" 
            :class="{ active: activeTab === 'summary' }"
            @click="activeTab = 'summary'"
          >
            Metrics &amp; Summary
          </button>
          <button 
            class="tab-btn" 
            :class="{ active: activeTab === 'report' }"
            @click="activeTab = 'report'"
          >
            JSON Report
          </button>
          <button 
            class="tab-btn" 
            :class="{ active: activeTab === 'history' }"
            @click="activeTab = 'history'"
          >
            Execution History ({{ runHistory.length }})
          </button>
        </div>

        <div class="tab-content">
          <!-- Terminal Output Tab -->
          <div v-show="activeTab === 'live'" class="tab-pane">
            <TerminalView :logs="logs" :isRunning="isRunning" :liveProgress="liveRunProgress" />
          </div>

          <!-- Detail Info Tab -->
          <div v-show="activeTab === 'detail'" class="tab-pane detail-pane">
            <TestDetailView 
              :detail="selectedTestDetail" 
              :isLoading="isLoadingDetail" 
              :latestRun="currentMethodOutput"
              :isRunning="isRunning"
              @run-test="runTests"
              @run-single-method="runSingleMethod"
              @clear-single-output="clearMethodOutput"
            />
          </div>

          <!-- Metrics & Summary Tab -->
          <div v-show="activeTab === 'summary'" class="tab-pane summary-pane">
            <MetricsSummary :summary="summary" :exitCode="exitCode" />
          </div>

          <!-- JSON Report Tab -->
          <div v-show="activeTab === 'report'" class="tab-pane report-pane">
            <pre v-if="summary?.report" class="json-code">{{ JSON.stringify(summary.report, null, 2) }}</pre>
            <div v-else class="no-summary">
              No JSON report available. Run tests to generate report content.
            </div>
          </div>

          <!-- History Tab -->
          <div v-show="activeTab === 'history'" class="tab-pane history-pane">
            <RunHistory 
              :runHistory="runHistory" 
              :selectedHistoryId="selectedHistoryId" 
              @select-history="selectHistoryItem" 
            />
          </div>
        </div>
      </template>

      <!-- API DECK MODE -->
      <template v-else>
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
      </template>
    </main>

    <!-- Floating Glass Tooltip -->
    <Teleport to="body">
      <div 
        v-if="activeTooltip.visible" 
        class="custom-glass-tooltip"
        :style="{ top: activeTooltip.y + 'px', left: activeTooltip.x + 'px' }"
      >
        <div class="tooltip-header">
          <span class="tooltip-badge" :class="activeTooltip.type">
            {{ (activeTooltip.type || 'NODE').substring(0, 3).toUpperCase() }}
          </span>
          <span class="tooltip-name">{{ activeTooltip.name }}</span>
        </div>
        <div v-if="activeTooltip.id && activeTooltip.id !== activeTooltip.name" class="tooltip-path">
          {{ activeTooltip.id }}
        </div>
      </div>
    </Teleport>

    <!-- Target Environment Logs Modal -->
    <EnvLogModal 
      :show="showEnvLogModal" 
      :envStatus="envStatus" 
      :logs="envLogs" 
      @close="showEnvLogModal = false" 
      @refresh="fetchEnvLogs" 
    />

    <!-- API Environment & Auth Settings Modal -->
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
