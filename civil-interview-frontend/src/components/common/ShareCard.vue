<template>
  <a-modal
    v-model:open="visible"
    title="分享成绩卡片"
    :footer="null"
    width="400px"
    centered
  >
    <!-- 卡片预览 -->
    <div ref="cardRef" class="share-card">
      <div class="share-card__header">
        <div class="share-card__logo">公考面试AI智能测评</div>
        <div class="share-card__date">{{ formattedDate }}</div>
      </div>

      <div class="share-card__score-area">
        <div class="share-card__score">{{ score }}</div>
        <div class="share-card__label">综合得分</div>
        <div class="share-card__grade" :style="{ color: gradeColor }">{{ gradeName }}</div>
      </div>

      <div class="share-card__dims">
        <div v-for="dim in dimensions" :key="dim.name" class="share-card__dim">
          <span class="share-card__dim-name">{{ dim.name }}</span>
          <div class="share-card__dim-bar">
            <div
              class="share-card__dim-fill"
              :style="{ width: (dim.score / dim.maxScore * 100) + '%', background: dimColor(dim) }"
            ></div>
          </div>
          <span class="share-card__dim-score">{{ dim.score }}/{{ dim.maxScore }}</span>
        </div>
      </div>

      <div class="share-card__footer">
        <span>扫码加入练习</span>
        <div class="share-card__slogan">每日一练，上岸有望</div>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="share-actions">
      <a-button type="primary" block :loading="generating" @click="generateImage">
        <DownloadOutlined /> 保存图片
      </a-button>
      <a-button block @click="copyToClipboard" :loading="copying" style="margin-top: 8px">
        <CopyOutlined /> 复制到剪贴板
      </a-button>
    </div>
  </a-modal>
</template>

<script setup>
import { ref, computed } from 'vue'
import { DownloadOutlined, CopyOutlined } from '@ant-design/icons-vue'
import { getGrade } from '@/utils/constants'
import { message } from 'ant-design-vue'

const props = defineProps({
  score: { type: Number, default: 0 },
  maxScore: { type: Number, default: 100 },
  dimensions: { type: Array, default: () => [] },
  date: { type: String, default: '' }
})

const visible = ref(false)
const cardRef = ref(null)
const generating = ref(false)
const copying = ref(false)

const formattedDate = computed(() => {
  if (!props.date) return new Date().toLocaleDateString('zh-CN')
  return new Date(props.date).toLocaleDateString('zh-CN')
})

const gradeInfo = computed(() => getGrade(props.score, props.maxScore))
const gradeName = computed(() => gradeInfo.value.label)
const gradeColor = computed(() => gradeInfo.value.color)

function dimColor(dim) {
  const ratio = dim.score / dim.maxScore
  if (ratio >= 0.85) return '#389E0D'
  if (ratio >= 0.75) return '#1B5FAA'
  if (ratio >= 0.6) return '#D48806'
  return '#CF1322'
}

function open() {
  visible.value = true
}

async function getCanvas() {
  const { default: html2canvas } = await import('html2canvas')
  return html2canvas(cardRef.value, {
    scale: 2,
    backgroundColor: null,
    useCORS: true
  })
}

async function generateImage() {
  if (!cardRef.value) return
  generating.value = true
  try {
    const canvas = await getCanvas()
    const link = document.createElement('a')
    link.download = `成绩卡片_${Date.now()}.png`
    link.href = canvas.toDataURL('image/png')
    link.click()
    // 释放 canvas 内存
    canvas.width = 0
    canvas.height = 0
    message.success('图片已保存')
  } catch (e) {
    message.error('生成失败')
  } finally {
    generating.value = false
  }
}

async function copyToClipboard() {
  if (!cardRef.value) return
  copying.value = true
  try {
    const canvas = await getCanvas()
    canvas.toBlob(async (blob) => {
      try {
        await navigator.clipboard.write([
          new ClipboardItem({ 'image/png': blob })
        ])
        message.success('已复制到剪贴板')
      } catch {
        message.error('复制失败，请使用保存图片功能')
      }
      // 释放 canvas 内存
      canvas.width = 0
      canvas.height = 0
      copying.value = false
    })
  } catch (e) {
    message.error('生成失败')
    copying.value = false
  }
}

defineExpose({ open })
</script>

<style lang="less" scoped>
.share-card {
  background: linear-gradient(135deg, #1B5FAA 0%, #2B7FD4 50%, #4A90D9 100%);
  border-radius: 16px;
  padding: 24px;
  color: #fff;
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -30%;
    width: 200px;
    height: 200px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.08);
  }

  &::after {
    content: '';
    position: absolute;
    bottom: -40%;
    left: -20%;
    width: 160px;
    height: 160px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.05);
  }
}

.share-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  position: relative;
  z-index: 1;
}

.share-card__logo {
  font-size: 14px;
  font-weight: 600;
  opacity: 0.9;
}

.share-card__date {
  font-size: 12px;
  opacity: 0.7;
}

.share-card__score-area {
  text-align: center;
  margin-bottom: 24px;
  position: relative;
  z-index: 1;
}

.share-card__score {
  font-size: 56px;
  font-weight: 700;
  line-height: 1;
  margin-bottom: 4px;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.share-card__label {
  font-size: 13px;
  opacity: 0.8;
  margin-bottom: 8px;
}

.share-card__grade {
  display: inline-block;
  padding: 2px 16px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  color: #fff !important;
}

.share-card__dims {
  background: rgba(255, 255, 255, 0.12);
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 16px;
  position: relative;
  z-index: 1;
}

.share-card__dim {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;

  &:last-child {
    margin-bottom: 0;
  }
}

.share-card__dim-name {
  font-size: 12px;
  width: 56px;
  flex-shrink: 0;
  opacity: 0.9;
}

.share-card__dim-bar {
  flex: 1;
  height: 6px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 3px;
  overflow: hidden;
}

.share-card__dim-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
}

.share-card__dim-score {
  font-size: 11px;
  width: 40px;
  text-align: right;
  flex-shrink: 0;
  opacity: 0.85;
}

.share-card__footer {
  text-align: center;
  position: relative;
  z-index: 1;

  span {
    font-size: 11px;
    opacity: 0.5;
  }
}

.share-card__slogan {
  font-size: 13px;
  opacity: 0.7;
  margin-top: 4px;
  font-style: italic;
}

.share-actions {
  margin-top: 16px;
}
</style>
