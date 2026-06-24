<!--
小程序应用外壳，只记录全局启动日志和基础样式，不在启动阶段索取手机号、头像、昵称或支付授权。

首页、定向页和题库入口需要允许未登录浏览，所以全局 onLaunch 只能做轻量日志和环境确认。
登录、权益、试用和支付都必须由用户点击具体功能后再触发，避免微信审核判定为进入首页即强制授权。

@param: 无；生命周期由微信小程序运行时触发。
@return: 渲染全局样式并把具体页面交给 pages 配置。
@raises: 不主动抛业务异常；页面级接口和权限错误由对应页面或请求层承接。
-->
<script>
import { API_BASE } from './api/request'
import { reportDashboardHeartbeat } from './api/dashboard'
import { TOKEN_STORAGE_KEY } from './utils/constants'
import { logger } from './utils/logger'

const HEARTBEAT_INTERVAL_MS = 60 * 1000
let heartbeatTimer = null
let heartbeatSessionId = ''
let heartbeatLastAt = Date.now()
let heartbeatBootstrapTimer = null
let appVisible = true

function createHeartbeatId() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}

function getHeartbeatSessionId() {
  if (!heartbeatSessionId) {
    heartbeatSessionId = createHeartbeatId()
  }
  return heartbeatSessionId
}

function hasLoginToken() {
  try {
    return !!uni.getStorageSync(TOKEN_STORAGE_KEY)
  } catch {
    return false
  }
}

function getRoutePath() {
  try {
    const pages = typeof getCurrentPages === 'function' ? getCurrentPages() : []
    const current = pages[pages.length - 1]
    const route = current?.route || ''
    const query = current?.options || {}
    const queryString = Object.entries(query)
      .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
      .join('&')
    return route ? `/${route}${queryString ? `?${queryString}` : ''}` : ''
  } catch {
    return ''
  }
}

async function flushDashboardHeartbeat(forceSeconds = 0) {
  if (!hasLoginToken()) {
    heartbeatLastAt = Date.now()
    return
  }
  const now = Date.now()
  const elapsedSeconds = forceSeconds || Math.round((now - heartbeatLastAt) / 1000)
  heartbeatLastAt = now
  if (elapsedSeconds <= 0) return

  try {
    await reportDashboardHeartbeat({
      sessionId: getHeartbeatSessionId(),
      eventId: createHeartbeatId(),
      clientType: 'mp-weixin',
      routePath: getRoutePath(),
      durationSeconds: elapsedSeconds,
      activeAt: new Date(now).toISOString()
    })
  } catch {
    // best-effort heartbeat, keep mini program flows quiet on network failure
  }
}

function stopDashboardHeartbeat() {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer)
    heartbeatTimer = null
  }
}

function startDashboardHeartbeat() {
  if (!hasLoginToken() || heartbeatTimer) return
  heartbeatLastAt = Date.now()
  heartbeatTimer = setInterval(() => {
    if (!hasLoginToken()) return
    flushDashboardHeartbeat(60)
  }, HEARTBEAT_INTERVAL_MS)
}

function startHeartbeatBootstrap() {
  if (heartbeatBootstrapTimer) return
  heartbeatBootstrapTimer = setInterval(() => {
    if (!appVisible) return
    if (hasLoginToken()) {
      startDashboardHeartbeat()
    } else {
      stopDashboardHeartbeat()
    }
  }, 5000)
}

function stopHeartbeatBootstrap() {
  if (heartbeatBootstrapTimer) {
    clearInterval(heartbeatBootstrapTimer)
    heartbeatBootstrapTimer = null
  }
}

export default {
  onLaunch() {
    logger.info('Mini program launched', {
      event: 'miniapp.launch',
      api_base: API_BASE
    })
    appVisible = true
    startHeartbeatBootstrap()
  },
  onShow() {
    appVisible = true
    startDashboardHeartbeat()
  },
  onHide() {
    appVisible = false
    flushDashboardHeartbeat()
    stopDashboardHeartbeat()
  },
  onUnload() {
    appVisible = false
    flushDashboardHeartbeat()
    stopDashboardHeartbeat()
    stopHeartbeatBootstrap()
  }
}
</script>

<style>
page {
  min-height: 100%;
  background: #F6FAFE;
  color: #172033;
  color-scheme: light;
  font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
  font-size: 30rpx;
}

view,
text,
button,
input,
textarea,
picker,
scroll-view {
  box-sizing: border-box;
}

button {
  margin: 0;
  border-radius: 12rpx;
  line-height: 1.3;
  transition: transform 180ms ease, opacity 180ms ease, box-shadow 180ms ease, background-color 180ms ease, border-color 180ms ease;
  transform: translateZ(0);
}

button::after {
  border: 0;
}

.page {
  min-height: 100vh;
  padding: 28rpx;
  padding-bottom: calc(32rpx + env(safe-area-inset-bottom));
  animation: motion-page-in 220ms ease-out both;
}

.page--tab {
  padding-bottom: calc(130rpx + env(safe-area-inset-bottom));
}

.page-title {
  display: block;
  margin-bottom: 8rpx;
  color: #172033;
  font-size: 40rpx;
  font-weight: 700;
}

.page-desc {
  display: block;
  margin-bottom: 28rpx;
  color: #64748B;
  font-size: 26rpx;
  line-height: 1.6;
}

.card {
  margin-bottom: 20rpx;
  padding: 28rpx;
  border: 1rpx solid #DCEAF7;
  border-radius: 16rpx;
  background: #ffffff;
  box-shadow: 0 6rpx 18rpx rgba(47, 127, 214, 0.05);
  animation: motion-fade-up 240ms ease-out both;
  transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease, opacity 180ms ease;
  transform: translateZ(0);
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18rpx;
}

.section-title {
  color: #172033;
  font-size: 32rpx;
  font-weight: 700;
}

.muted {
  color: #64748B;
  font-size: 24rpx;
}

.primary-button {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 88rpx;
  border-radius: 14rpx;
  background: #2F7FD6;
  color: #ffffff;
  font-size: 30rpx;
  font-weight: 600;
}

.primary-button:active {
  opacity: 0.92;
  transform: scale(0.985);
  box-shadow: 0 8rpx 20rpx rgba(47, 127, 214, 0.14);
}

.secondary-button {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 84rpx;
  border: 1rpx solid #DCEAF7;
  border-radius: 14rpx;
  background: #ffffff;
  color: #2F7FD6;
  font-size: 28rpx;
}

.secondary-button:active {
  background: #EAF5FF;
  opacity: 0.94;
  transform: scale(0.985);
}

.danger-button {
  color: #cf1322;
  background: #fff5f5;
}

.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 14rpx;
}

.chip {
  padding: 12rpx 22rpx;
  border: 1rpx solid #DCEAF7;
  border-radius: 999rpx;
  background: #ffffff;
  color: #2a3648;
  font-size: 25rpx;
  transition: transform 160ms ease, background-color 160ms ease, border-color 160ms ease, color 160ms ease;
}

.chip:active {
  transform: scale(0.96);
}

.chip--active {
  border-color: #2F7FD6;
  background: #EAF5FF;
  color: #2F7FD6;
  font-weight: 600;
}

.form-label {
  display: block;
  margin: 18rpx 0 10rpx;
  color: #2a3648;
  font-size: 26rpx;
  font-weight: 600;
}

.field {
  width: 100%;
  min-height: 88rpx;
  padding: 0 24rpx;
  border: 1rpx solid #DCEAF7;
  border-radius: 14rpx;
  background: #ffffff;
  color: #172033;
  font-size: 28rpx;
}

.textarea-field {
  width: 100%;
  min-height: 240rpx;
  padding: 22rpx 24rpx;
  border: 1rpx solid #DCEAF7;
  border-radius: 14rpx;
  background: #ffffff;
  color: #172033;
  font-size: 28rpx;
  line-height: 1.6;
}

.motion-fade-up {
  animation: motion-fade-up 240ms ease-out both;
}

.motion-shimmer {
  position: relative;
  overflow: hidden;
}

.motion-shimmer::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: -60%;
  width: 45%;
  background: linear-gradient(90deg, transparent 0%, rgba(47, 127, 214, 0.12) 48%, transparent 100%);
  animation: motion-shimmer 1.45s ease-in-out infinite;
}

.recording-pulse {
  animation: motion-recording-pulse 1.4s ease-in-out infinite;
}

@keyframes motion-page-in {
  from {
    opacity: 0.96;
  }
  to {
    opacity: 1;
  }
}

@keyframes motion-fade-up {
  from {
    opacity: 0;
    transform: translate3d(0, 14rpx, 0);
  }
  to {
    opacity: 1;
    transform: translate3d(0, 0, 0);
  }
}

@keyframes motion-sheet-up {
  from {
    opacity: 0;
    transform: translate3d(0, 36rpx, 0);
  }
  to {
    opacity: 1;
    transform: translate3d(0, 0, 0);
  }
}

@keyframes motion-shimmer {
  0% {
    transform: translateX(0);
  }
  100% {
    transform: translateX(360%);
  }
}

@keyframes motion-recording-pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(47, 127, 214, 0.20);
  }
  50% {
    box-shadow: 0 0 0 12rpx rgba(47, 127, 214, 0);
  }
}
</style>
