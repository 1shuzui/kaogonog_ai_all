import tokens from './tokens.json' with { type: 'json' }

export function normalizeMode(mode) {
  return ['full', 'reduced', 'off'].includes(mode) ? mode : tokens.defaultMode
}

export function motionStyle(mode, safeBottom = 0) {
  mode = normalizeMode(mode)
  const duration = (key) => mode === 'off' ? 0 : mode === 'reduced' ? (key === 'segment' ? 0 : Math.min(tokens[key], 100)) : tokens[key]
  return ['press', 'enter', 'exit', 'segment', 'summary', 'collapse', 'arrow', 'scan'].map(key => `--motion-${key}:${duration(key)}ms;`).join('') +
    `--motion-ease:${tokens.easing};--motion-offset:${mode === 'full' ? tokens.offsetPx : 0}px;` +
    `--motion-scale:${mode === 'full' ? tokens.pressScale : 1};--motion-float:${tokens.float}ms;` +
    `--motion-summary-height:${tokens.summaryHeightPx}px;--motion-safe-bottom:${safeBottom}px;` +
    `--motion-nav-inset:${tokens.navHeightPx + tokens.navGapPx + tokens.navContentGapPx + safeBottom}px;`
}

export function bottomInset(info = {}) {
  const value = info.safeAreaInsets?.bottom ?? (info.safeArea ? info.screenHeight - info.safeArea.bottom : 0)
  return Number.isFinite(value) ? Math.max(0, value) : 0
}

export function summaryState(compact, scrollTop, threshold, hysteresis = tokens.summaryHysteresisPx) {
  return compact ? scrollTop > threshold - hysteresis : scrollTop > threshold
}
