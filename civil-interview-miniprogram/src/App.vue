<script>
export default {
  onLaunch() {
    const apiBase = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8050'
    console.log(`[miniapp] API base: ${apiBase}`)
  }
}
</script>

<style>
page {
  min-height: 100%;
  background: #f0f5fa;
  color: #1a1a2e;
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
}

button::after {
  border: 0;
}

.page {
  min-height: 100vh;
  padding: 28rpx;
  padding-bottom: calc(32rpx + env(safe-area-inset-bottom));
}

.page--tab {
  padding-bottom: calc(130rpx + env(safe-area-inset-bottom));
}

.page-title {
  display: block;
  margin-bottom: 8rpx;
  color: #1a1a2e;
  font-size: 40rpx;
  font-weight: 700;
}

.page-desc {
  display: block;
  margin-bottom: 28rpx;
  color: #6f7c8f;
  font-size: 26rpx;
  line-height: 1.6;
}

.card {
  margin-bottom: 20rpx;
  padding: 28rpx;
  border: 1rpx solid rgba(27, 95, 170, 0.08);
  border-radius: 16rpx;
  background: #ffffff;
  box-shadow: 0 6rpx 18rpx rgba(23, 48, 78, 0.06);
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18rpx;
}

.section-title {
  color: #1a1a2e;
  font-size: 32rpx;
  font-weight: 700;
}

.muted {
  color: #6f7c8f;
  font-size: 24rpx;
}

.primary-button {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 88rpx;
  border-radius: 14rpx;
  background: #1b5faa;
  color: #ffffff;
  font-size: 30rpx;
  font-weight: 600;
}

.secondary-button {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 84rpx;
  border: 1rpx solid #cbd9ea;
  border-radius: 14rpx;
  background: #ffffff;
  color: #1b5faa;
  font-size: 28rpx;
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
  border: 1rpx solid #d9e3ef;
  border-radius: 999rpx;
  background: #ffffff;
  color: #2a3648;
  font-size: 25rpx;
}

.chip--active {
  border-color: #1b5faa;
  background: #e8f4fd;
  color: #1b5faa;
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
  border: 1rpx solid #d9e3ef;
  border-radius: 14rpx;
  background: #ffffff;
  color: #1a1a2e;
  font-size: 28rpx;
}

.textarea-field {
  width: 100%;
  min-height: 240rpx;
  padding: 22rpx 24rpx;
  border: 1rpx solid #d9e3ef;
  border-radius: 14rpx;
  background: #ffffff;
  color: #1a1a2e;
  font-size: 28rpx;
  line-height: 1.6;
}
</style>
