import { ref, watch, onMounted } from 'vue'

const THEME_KEY = 'pytestdeck_theme'
export const THEMES = [
  { id: 'apple-glass-dark', label: '🍏 Apple Glass Dark' },
  { id: 'apple-glass-light', label: '🍎 Apple Glass Light' },
  { id: 'midnight', label: '🌙 Midnight Dark' }
]

export function useTheme() {
  const currentTheme = ref('apple-glass-dark')

  const setTheme = (themeId) => {
    currentTheme.value = themeId
    document.documentElement.setAttribute('data-theme', themeId)
    try {
      localStorage.setItem(THEME_KEY, themeId)
    } catch {
      // Ignore storage errors in sandbox
    }
  }

  onMounted(() => {
    const savedTheme = localStorage.getItem(THEME_KEY)
    if (savedTheme && THEMES.some(t => t.id === savedTheme)) {
      setTheme(savedTheme)
    } else {
      setTheme('apple-glass-dark')
    }
  })

  watch(currentTheme, (newTheme) => {
    setTheme(newTheme)
  })

  return {
    currentTheme,
    themes: THEMES,
    setTheme
  }
}
