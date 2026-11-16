import { ref, watch, onMounted } from 'vue'

const THEME_KEY = 'pytestdeck_theme'
const TERM_THEME_KEY = 'pytestdeck_term_theme'
const TERM_FONT_KEY = 'pytestdeck_term_font'

export const THEMES = [
  { id: 'apple-glass-dark', label: '🍏 Apple Glass Dark' },
  { id: 'apple-glass-light', label: '🍎 Apple Glass Light' },
  { id: 'midnight', label: '🌙 Midnight Dark' }
]

export const TERMINAL_FONTS = [
  { id: 'fira-code', label: '🔤 Fira Code', family: '"Fira Code", Menlo, Monaco, Consolas, monospace' },
  { id: 'jetbrains-mono', label: '🔤 JetBrains Mono', family: '"JetBrains Mono", Menlo, Monaco, "Courier New", monospace' },
  { id: 'sf-mono', label: '🔤 SF Mono', family: '"SF Mono", -apple-system, BlinkMacSystemFont, Menlo, monospace' },
  { id: 'cascadia-code', label: '🔤 Cascadia Code', family: '"Cascadia Code", "Segoe UI Mono", monospace' },
  { id: 'classic-courier', label: '🔤 Courier Classic', family: '"Courier New", Courier, monospace' },
]

export const TERMINAL_THEMES = {
  'apple-dark': {
    id: 'apple-dark',
    label: '🍏 macOS Glass Dark',
    options: {
      background: '#090d16',
      foreground: '#e6edf3',
      cursor: '#38bdf8',
      selectionBackground: 'rgba(56, 189, 248, 0.3)',
      black: '#1e222a',
      red: '#f87171',
      green: '#34d399',
      yellow: '#fbbf24',
      blue: '#60a5fa',
      magenta: '#c084fc',
      cyan: '#38bdf8',
      white: '#f1f5f9',
      brightBlack: '#475569',
      brightRed: '#ef4444',
      brightGreen: '#22c55e',
      brightYellow: '#eab308',
      brightBlue: '#3b82f6',
      brightMagenta: '#a855f7',
      brightCyan: '#06b6d4',
      brightWhite: '#ffffff'
    }
  },
  'apple-light': {
    id: 'apple-light',
    label: '🍎 macOS Glass Light',
    options: {
      background: '#f8fafc',
      foreground: '#0f172a',
      cursor: '#0284c7',
      selectionBackground: 'rgba(2, 132, 199, 0.25)',
      black: '#0f172a',
      red: '#dc2626',
      green: '#059669',
      yellow: '#d97706',
      blue: '#2563eb',
      magenta: '#9333ea',
      cyan: '#0284c7',
      white: '#ffffff',
      brightBlack: '#475569',
      brightRed: '#b91c1c',
      brightGreen: '#047857',
      brightYellow: '#b45309',
      brightBlue: '#1d4ed8',
      brightMagenta: '#7e22ce',
      brightCyan: '#0369a1',
      brightWhite: '#ffffff'
    }
  },
  'synthwave': {
    id: 'synthwave',
    label: '👾 Synthwave Neon',
    options: {
      background: '#1a102f',
      foreground: '#f4eee0',
      cursor: '#f43f5e',
      selectionBackground: 'rgba(244, 63, 94, 0.3)',
      black: '#120b22',
      red: '#f43f5e',
      green: '#34d399',
      yellow: '#fbbf24',
      blue: '#a855f7',
      magenta: '#ec4899',
      cyan: '#22d3ee',
      white: '#f4eee0',
      brightBlack: '#4c3575',
      brightRed: '#fb7185',
      brightGreen: '#6ee7b7',
      brightYellow: '#fde047',
      brightBlue: '#c084fc',
      brightMagenta: '#f472b6',
      brightCyan: '#67e8f9',
      brightWhite: '#ffffff'
    }
  },
  'matrix': {
    id: 'matrix',
    label: '🟢 Matrix Hacker',
    options: {
      background: '#040d06',
      foreground: '#22c55e',
      cursor: '#4ade80',
      selectionBackground: 'rgba(34, 197, 94, 0.3)',
      black: '#020703',
      red: '#ef4444',
      green: '#22c55e',
      yellow: '#86efac',
      blue: '#10b981',
      magenta: '#34d399',
      cyan: '#4ade80',
      white: '#bbf7d0',
      brightBlack: '#14532d',
      brightRed: '#f87171',
      brightGreen: '#4ade80',
      brightYellow: '#a7f3d0',
      brightBlue: '#34d399',
      brightMagenta: '#6ee7b7',
      brightCyan: '#86efac',
      brightWhite: '#f0fdf4'
    }
  },
  'one-dark': {
    id: 'one-dark',
    label: '🔥 One Dark Pro',
    options: {
      background: '#1e1e1e',
      foreground: '#abb2bf',
      cursor: '#528bff',
      selectionBackground: 'rgba(82, 139, 255, 0.3)',
      black: '#282c34',
      red: '#e06c75',
      green: '#98c379',
      yellow: '#e5c07b',
      blue: '#61afef',
      magenta: '#c678dd',
      cyan: '#56b6c2',
      white: '#abb2bf',
      brightBlack: '#5c6370',
      brightRed: '#be5046',
      brightGreen: '#a3d87b',
      brightYellow: '#e8c88c',
      brightBlue: '#7cb7f5',
      brightMagenta: '#d38aea',
      brightCyan: '#6dc5d1',
      brightWhite: '#ffffff'
    }
  }
}

export function useTheme() {
  const currentTheme = ref('apple-glass-dark')
  const currentTerminalTheme = ref('apple-dark')
  const currentTerminalFont = ref('fira-code')

  const setTheme = (themeId) => {
    currentTheme.value = themeId
    document.documentElement.setAttribute('data-theme', themeId)
    try {
      localStorage.setItem(THEME_KEY, themeId)
    } catch {
      // Ignore storage errors in sandbox
    }

    // Auto update terminal default match if user hasn't explicitly set custom
    if (themeId === 'apple-glass-light') {
      setTerminalTheme('apple-light')
    } else if (themeId === 'apple-glass-dark') {
      setTerminalTheme('apple-dark')
    }
  }

  const setTerminalTheme = (termThemeId) => {
    if (TERMINAL_THEMES[termThemeId]) {
      currentTerminalTheme.value = termThemeId
      try {
        localStorage.setItem(TERM_THEME_KEY, termThemeId)
      } catch {
        // Ignore
      }
    }
  }

  const setTerminalFont = (fontId) => {
    if (TERMINAL_FONTS.some(f => f.id === fontId)) {
      currentTerminalFont.value = fontId
      try {
        localStorage.setItem(TERM_FONT_KEY, fontId)
      } catch {
        // Ignore
      }
    }
  }

  onMounted(() => {
    const savedTheme = localStorage.getItem(THEME_KEY)
    if (savedTheme && THEMES.some(t => t.id === savedTheme)) {
      setTheme(savedTheme)
    } else {
      setTheme('apple-glass-dark')
    }

    const savedTermTheme = localStorage.getItem(TERM_THEME_KEY)
    if (savedTermTheme && TERMINAL_THEMES[savedTermTheme]) {
      currentTerminalTheme.value = savedTermTheme
    }

    const savedTermFont = localStorage.getItem(TERM_FONT_KEY)
    if (savedTermFont && TERMINAL_FONTS.some(f => f.id === savedTermFont)) {
      currentTerminalFont.value = savedTermFont
    }
  })

  watch(currentTheme, (newTheme) => {
    setTheme(newTheme)
  })

  watch(currentTerminalTheme, (newTermTheme) => {
    setTerminalTheme(newTermTheme)
  })

  watch(currentTerminalFont, (newFont) => {
    setTerminalFont(newFont)
  })

  return {
    currentTheme,
    themes: THEMES,
    setTheme,
    currentTerminalTheme,
    terminalThemes: Object.values(TERMINAL_THEMES),
    setTerminalTheme,
    currentTerminalFont,
    terminalFonts: TERMINAL_FONTS,
    setTerminalFont
  }
}
