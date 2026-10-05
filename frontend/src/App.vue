<script setup>
import Header from './components/Header.vue'
import TestExplorer from './components/TestExplorer.vue'
import TerminalView from './components/TerminalView.vue'
import MetricsSummary from './components/MetricsSummary.vue'
import RunHistory from './components/RunHistory.vue'
import EnvLogModal from './components/EnvLogModal.vue'
import TestDetailView from './components/TestDetailView.vue'
import { useTestRunner } from './composables/useTestRunner'
import { useTooltip } from './composables/useTooltip'

const {
  targetPath,
  activeSuite,
  availableSuites,
  isDiscovering,
  isRunning,
  envStatus,
  envLogs,
  showEnvLogModal,
  fetchEnvLogs,
  testTree,
  selectedNodes,
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
  runTests,
  stopTests,
  selectHistoryItem,
  selectedTestDetail,
  isLoadingDetail,
  isDetailSuite,
  singleSelectedNode,
  currentMethodOutput,
  runSingleMethod,
  clearMethodOutput
} = useTestRunner()

import { useSidebarResize } from './composables/useSidebarResize'

const { sidebarWidth, isResizing, startResizing } = useSidebarResize(480)
const { activeTooltip } = useTooltip()
</script>

<template>
  <div class="deck-app">
    <!-- Left-hand Sidebar: Appbar Controls + Test Explorer -->
    <aside class="deck-sidebar" :style="{ width: sidebarWidth + 'px' }">
      <Header
        v-model:targetPath="targetPath"
        v-model:activeSuite="activeSuite"
        :availableSuites="availableSuites"
        :envStatus="envStatus"
        @discover="discoverTests"
        @open-env-logs="showEnvLogModal = true; fetchEnvLogs()"
      />

      <TestExplorer
        :activeSuite="activeSuite"
        :isDiscovering="isDiscovering"
        :isRunning="isRunning"
        :selectedCount="selectedNodes.size"
        v-model:markerFilter="markerFilter"
        v-model:extraArgs="extraArgs"
        :testTree="testTree"
        :selectedNodes="selectedNodes"
        @toggle-select="toggleSelectNode"
        @discover="discoverTests"
        @run="runTests"
        @stop="stopTests"
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
            Metrics & Summary
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
            <TerminalView :logs="logs" />
          </div>

          <!-- Detail Info Tab (for Integration & Behave suites) -->
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
  </div>
</template>
