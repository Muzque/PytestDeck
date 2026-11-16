<script setup>
import { ref } from 'vue'
import TestDeckView from './test_deck/TestDeckView.vue'
import ApiDeckView from './api_deck/ApiDeckView.vue'

const activeMode = ref('tests')
</script>

<template>
  <KeepAlive>
    <TestDeckView
      v-if="activeMode === 'tests'"
      @switch-mode="activeMode = $event"
    />
    <ApiDeckView
      v-else
      @switch-mode="activeMode = $event"
    />
  </KeepAlive>
</template>
