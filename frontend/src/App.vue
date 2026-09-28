<script setup>
import Header from './components/Header.vue'
import TestExplorer from './components/TestExplorer.vue'
import TerminalView from './components/TerminalView.vue'
import MetricsSummary from './components/MetricsSummary.vue'
import RunHistory from './components/RunHistory.vue'
import { useTestRunner } from './composables/useTestRunner'

const {
  targetPath,
  activeSuite,
  availableSuites,
  isDiscovering,
  isRunning,
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
      :selectedCount="selectedNodes.size"
      @discover="discoverTests"
      @run="runTests"
      @stop="stopTests"
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
  </div>
</template>
