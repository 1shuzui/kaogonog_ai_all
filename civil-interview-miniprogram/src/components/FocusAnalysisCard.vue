<template>
  <MotionCollapse class="focus-analysis-card" :open="status !== 'idle' || !!data" :revision="[status, data, error, slow]" @settled="observe">
    <view class="analysis-card card" :style="theme" aria-live="polite">
      <view v-if="status === 'loading'" class="analysis-status">
        <view class="analysis-illustration" :class="{ 'analysis-illustration--playing': playing, 'analysis-illustration--static': mode !== 'full' }">
          <view class="analysis-paper"><view class="analysis-paper__fold" /><view class="analysis-line" /><view class="analysis-line" /><view class="analysis-line analysis-line--short" /><view class="analysis-scan" /></view>
          <view class="analysis-dot" />
        </view>
        <view class="analysis-status__copy">
          <text class="analysis-title">正在生成面试重点</text>
          <text class="analysis-caption">{{ data ? '正在更新，下面保留上次可用结果。' : '依据真实题库与已发布的重点内容整理。' }}</text>
          <text v-if="slow" class="analysis-slow">这次分析需要一点时间</text>
          <button class="analysis-link" @tap="$emit('cancel')">停止等待</button>
        </view>
      </view>
      <view v-else-if="['error', 'timeout', 'cancelled'].includes(status)" class="analysis-feedback">
        <text class="analysis-title">{{ status === 'timeout' ? '本次分析等待超时' : status === 'cancelled' ? '已停止等待' : '暂时没有完成分析' }}</text>
        <text class="analysis-caption">{{ error || '请稍后重试，所选条件已保留。' }}</text>
        <button class="secondary-button analysis-retry" @tap="$emit('retry')">重试分析</button>
      </view>
      <view v-if="data" class="analysis-results" :class="{ 'analysis-results--fresh': status === 'success' }">
        <view class="analysis-result-head"><text class="analysis-title">{{ status === 'success' ? '面试重点' : '上次可用结果' }}</text><text v-if="data.questionCount > 0" class="analysis-count">{{ data.questionCount }} 道题库样本</text></view>
        <text v-if="targetLabel" class="analysis-target">对应方向：{{ targetLabel }}</text>
        <view v-if="empty" class="analysis-empty"><LearnerIcon name="read" :size="30" /><text>{{ data.emptyMessage || '暂无足够题库数据，请选择已有真实题库的方向后重试。' }}</text></view>
        <view v-else>
          <view v-if="data.coreFocus?.length" class="analysis-section">
            <text class="analysis-section__title">核心能力重点</text>
            <view v-for="(item, index) in data.coreFocus" :key="item.dimensionKey || index" class="analysis-focus-row">
              <view class="analysis-focus-row__head"><text>{{ item.name }}</text><text>{{ item.weight }}%</text></view>
              <view class="analysis-track"><view :style="{ width: Math.max(0, Math.min(100, Number(item.weight) || 0)) + '%' }" /></view>
              <text class="analysis-caption">{{ item.desc }}</text>
            </view>
          </view>
          <view v-if="data.highFreqTypes?.length" class="analysis-section"><text class="analysis-section__title">高频题型</text><view v-for="(item, index) in data.highFreqTypes" :key="index" class="analysis-list-row"><text>{{ item.type }} · {{ item.frequency || '未标注' }}频</text><text class="analysis-caption">{{ item.example }}</text></view></view>
          <view v-if="data.hotTopics?.length" class="analysis-section"><text class="analysis-section__title">热门话题</text><view class="analysis-topics"><text v-for="topic in data.hotTopics" :key="topic">{{ topic }}</text></view></view>
          <view v-if="data.strategy?.length" class="analysis-section"><text class="analysis-section__title">备考策略</text><view v-for="(item, index) in data.strategy" :key="index" class="analysis-strategy"><text class="analysis-strategy__index">{{ index + 1 }}</text><text>{{ item }}</text></view></view>
        </view>
      </view>
    </view>
  </MotionCollapse>
</template>
<script setup>
import { computed, getCurrentInstance, nextTick, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import MotionCollapse from './MotionCollapse.vue'
import LearnerIcon from './LearnerIcon.vue'
import { useMotion } from '../motion/useMotion'
import { motionStyle } from '../motion/policy.mjs'
const props = defineProps({ status: { type: String, default: 'idle' }, data: { default: null }, error: { type: String, default: '' }, slow: Boolean, targetLabel: { type: String, default: '' } })
defineEmits(['retry', 'cancel'])
const { proxy } = getCurrentInstance()
const { mode, visible } = useMotion()
const inView = ref(false)
let observer, generation = 0, mounted = false
const theme = computed(() => motionStyle(mode.value))
const empty = computed(() => props.data?.isFallback || Number(props.data?.questionCount || 0) <= 0)
const playing = computed(() => visible.value && inView.value && mode.value === 'full' && props.status === 'loading')
function stop() { generation++; observer?.disconnect(); observer = null; inView.value = false }
async function observe() {
  stop()
  const id = generation
  if (!mounted || !visible.value || props.status !== 'loading' || mode.value !== 'full') return
  await nextTick()
  if (id !== generation) return
  try {
    observer = uni.createIntersectionObserver(proxy, { thresholds: [0, .05] })
    observer.relativeToViewport().observe('.analysis-status', result => { if (id === generation) inView.value = result.intersectionRatio > 0 })
  } catch { stop() }
}
watch([() => props.status, visible, mode], observe, { flush: 'post' })
onMounted(() => { mounted = true; observe() })
onBeforeUnmount(() => { mounted = false; stop() })
</script>
<style scoped>
.analysis-card { border:1px solid #dce6f5; padding:22px 18px; background:#fff; border-radius:16px; margin:4px 0 18px; }
.analysis-status { display:flex; align-items:center; gap:18px; min-height:126px; }
.analysis-status__copy { flex:1; min-width:0; }
.analysis-title { display:block; font-size:30rpx; font-weight:700; color:#203047; line-height:1.5; }
.analysis-caption { display:block; font-size:24rpx; line-height:1.7; color:#64748b; margin-top:7px; }
.analysis-slow { display:block; color:#526783; font-size:24rpx; margin-top:8px; }
.analysis-link { margin:8px 0 0; padding:4px 0; width:auto; display:inline-block; color:#326be5; background:transparent; font-size:25rpx; line-height:1.6; }
.analysis-link::after { border:0; }
.analysis-illustration { position:relative; width:62px; height:88px; flex:none; --analysis-play:paused; }
.analysis-illustration--playing { --analysis-play:running; }
.analysis-paper { position:absolute; inset:6px 5px; padding:24px 9px 10px; box-sizing:border-box; background:#f2f6ff; border:1px solid #cddcf7; border-radius:8px; overflow:hidden; animation:analysis-float var(--motion-float) ease-in-out infinite; animation-play-state:var(--analysis-play); }
.analysis-paper__fold { position:absolute; right:0; top:0; width:12px; height:12px; background:#d9e6ff; border-radius:0 0 0 5px; }
.analysis-line { height:3px; margin-bottom:9px; border-radius:2px; background:#bdcff0; }
.analysis-line--short { width:68%; }
.analysis-scan { position:absolute; inset:0 0 auto; height:20px; background:linear-gradient(transparent,rgba(50,107,229,.15),transparent); animation:analysis-scan var(--motion-scan) ease-in-out infinite; animation-play-state:var(--analysis-play); }
.analysis-dot { position:absolute; right:0; bottom:3px; width:7px; height:7px; border-radius:50%; background:#a6dcd5; animation:analysis-float var(--motion-float) ease-in-out infinite reverse; animation-play-state:var(--analysis-play); }
.analysis-illustration--static .analysis-paper,.analysis-illustration--static .analysis-dot,.analysis-illustration--static .analysis-scan { animation:none; }
.analysis-illustration--static .analysis-scan { display:none; }
.analysis-retry { margin:14px 0 0; font-size:26rpx; min-height:40px; }
.analysis-results { margin-top:6px; }
.analysis-status + .analysis-results,.analysis-feedback + .analysis-results { margin-top:22px; padding-top:18px; border-top:1px solid #e7edf5; }
.analysis-results--fresh { animation:analysis-result-in var(--motion-enter) var(--motion-ease) both; }
.analysis-result-head { display:flex; justify-content:space-between; align-items:center; gap:8px; }
.analysis-count,.analysis-target { color:#64748b; font-size:22rpx; line-height:1.6; }
.analysis-target { display:block; margin-top:6px; }
.analysis-section { margin-top:22px; }
.analysis-section__title { display:block; font-size:27rpx; font-weight:700; color:#203047; margin-bottom:12px; }
.analysis-focus-row { margin-top:16px; }
.analysis-focus-row__head { display:flex; justify-content:space-between; color:#35455a; font-size:25rpx; }
.analysis-track { height:5px; margin-top:8px; background:#edf2fa; border-radius:5px; overflow:hidden; }
.analysis-track view { height:100%; background:#326be5; border-radius:5px; }
.analysis-list-row { margin-top:12px; font-size:25rpx; }
.analysis-topics { display:flex; flex-wrap:wrap; gap:8px; }
.analysis-topics text { background:#edf3ff; color:#326be5; padding:5px 9px; border-radius:7px; font-size:23rpx; }
.analysis-strategy { display:flex; gap:10px; margin-top:13px; font-size:25rpx; color:#35455a; line-height:1.75; }
.analysis-strategy__index { flex:none; color:#326be5; font-weight:700; }
.analysis-empty { display:flex; align-items:center; gap:14px; padding:25px 0; color:#64748b; font-size:25rpx; line-height:1.7; }
@keyframes analysis-scan { 0% { transform:translateY(-20px); opacity:0; } 20%,75% { opacity:1; } 100% { transform:translateY(76px); opacity:0; } }
@keyframes analysis-float { 0%,100% { transform:translateY(0); } 50% { transform:translateY(-3px); } }
@keyframes analysis-result-in { from { opacity:.3; transform:translateY(4px); } to { opacity:1; transform:translateY(0); } }
</style>
