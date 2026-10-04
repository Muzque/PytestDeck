<script setup>
import Header from './components/Header.vue'
import TestExplorer from './components/TestExplorer.vue'
import TerminalView from './components/TerminalView.vue'
import MetricsSummary from './components/MetricsSummary.vue'
import RunHistory from './components/RunHistory.vue'
import EnvLogModal from './components/EnvLogModal.vue'
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
  selectHistoryItem
} = useTestRunner()

const { activeTooltip } = useTooltip()
</script>

<template>
  <div class="deck-app">
    <!-- Top Navigation Header -->
    <Header
      v-model:targetPath="targetPath"
      v-model:activeSuite="activeSuite"
      :availableSuites="availableSuites"
      :isDiscovering="isDiscovering"
      :isRunning="isRunning"
      :envStatus="envStatus"
      :selectedCount="selectedNodes.size"
      @discover="discoverTests"
      @run="runTests"
      @stop="stopTests"
      @open-env-logs="showEnvLogModal = true; fetchEnvLogs()"
    />

    <!-- Main Workspace Area -->
    <div class="deck-body">
      <!-- Left Sidebar: Test Explorer -->
      <TestExplorer
        :activeSuite="activeSuite"
        v-model:markerFilter="markerFilter"
        v-model:extraArgs="extraArgs"
        :testTree="testTree"
        :selectedNodes="selectedNodes"
        @toggle-select="toggleSelectNode"
      />

      <!-- Right Main: Tabbed Views -->
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
    </div>

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
