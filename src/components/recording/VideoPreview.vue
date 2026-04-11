<template>
  <div class="video-preview">
    <!-- 只有这层做镜像，文字不在里面 -->
    <div class="video-preview__mirror">
      <video ref="videoEl" autoplay muted playsinline></video>
    </div>
    <!-- 文字覆盖层在镜像层之外，不受翻转影响 -->
    <div class="recording-indicator" v-if="recording">
      <span class="dot"></span>
      <span>REC {{ formattedDuration }}</span>
    </div>
    <div class="video-preview__off" v-if="!active">
      <VideoCameraOutlined />
      <span>摄像头未开启</span>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onUnmounted, computed } from 'vue'
import { VideoCameraOutlined } from '@ant-design/icons-vue'
import { formatTime } from '@/utils/formatter'

const props = defineProps({
  stream: { type: Object, default: null },
  recording: { type: Boolean, default: false },
  duration: { type: Number, default: 0 }
})

const videoEl = ref(null)
const active = ref(false)

const formattedDuration = computed(() => formatTime(props.duration))

watch(() => props.stream, (stream) => {
  if (videoEl.value && stream) {
    videoEl.value.srcObject = stream
    active.value = true
  } else {
    active.value = false
  }
}, { immediate: true })

onUnmounted(() => {
  if (videoEl.value) {
    videoEl.value.srcObject = null
  }
})
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.video-preview {
  position: relative;
  width: 100%;
  height: 100%;
  background: #000;
  border-radius: @border-radius;
  overflow: hidden;
}

/* 只有这一层做镜像，视频画面翻转，文字不受影响 */
.video-preview__mirror {
  position: absolute;
  inset: 0;
  transform: scaleX(-1);

  video {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.video-preview__off {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: rgba(255, 255, 255, 0.4);
  font-size: 14px;

  .anticon {
    font-size: 32px;
  }
}

.recording-indicator {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: rgba(207, 19, 34, 0.8);
  border-radius: 12px;
  font-size: 12px;
  color: #fff;

  .dot {
    width: 8px;
    height: 8px;
    background: #ff4d4f;
    border-radius: 50%;
    animation: blink 1s infinite;
  }
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
</style>
