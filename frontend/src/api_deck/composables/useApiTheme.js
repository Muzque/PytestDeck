import { ref, watch } from 'vue'

const THEME_STORAGE_KEY = 'pytestdeck_theme'

const themes = [
  { id: 'apple-glass-dark', label: 'Apple Glass (Dark)' },
  { id: 'apple-glass-light', label: 'Apple Glass (Light)' },
  { id: 'midnight', label: 'Midnight' }
]

const currentTheme = ref(
  (typeof localStorage !== 'undefined' && localStorage.getItem(THEME_STORAGE_KEY)) ||
    'apple-glass-dark'
)

const applyTheme = (themeId) => {
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('data-theme', themeId)
  }
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem(THEME_STORAGE_KEY, themeId)
  }
}

watch(
  currentTheme,
  (val) => {
    applyTheme(val)
  },
  { immediate: true }
)

export function useApiTheme() {
  if (typeof localStorage !== 'undefined') {
    const saved = localStorage.getItem(THEME_STORAGE_KEY)
    if (saved && saved !== currentTheme.value) {
      currentTheme.value = saved
    }
  }
  return {
    currentTheme,
    themes
  }
}
