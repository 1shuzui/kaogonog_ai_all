<!--
这个小程序协议页展示服务协议和隐私政策，是登录授权和审核检查都会访问的页面。

@param: 无；页面运行时从 props、路由参数、Pinia 状态和用户点击中拿数据。
@return: 渲染当前业务界面，并把按钮、表单或跳转事件交给既有流程处理。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
<template>
  <view class="page">
    <view class="card page-head">
      <view>
        <text class="page-title">用户协议与隐私协议</text>
        <text class="page-desc">版本 {{ documents.latestVersion || '-' }}，更新于 {{ documents.updatedAt || '-' }}</text>
      </view>
      <button
        v-if="userStore.isAuthenticated"
        class="primary-button page-head__button"
        :loading="agreeLoading"
        @tap="agreeLatest"
      >
        同意最新版
      </button>
    </view>

    <view class="card tab-card">
      <view
        v-for="item in documentList"
        :key="item.type"
        class="tab-card__item"
        :class="{ 'tab-card__item--active': activeType === item.type }"
        @tap="activeType = item.type"
      >
        <text class="tab-card__title">{{ item.title }}</text>
        <text class="tab-card__meta">{{ item.updatedAt }}</text>
      </view>
    </view>

    <view v-if="currentDocument" class="card document-card">
      <text class="document-card__title">{{ currentDocument.title }}</text>
      <text class="document-card__meta">生效日期：{{ currentDocument.effectiveAt || '-' }}</text>

      <text
        v-for="(paragraph, index) in currentDocument.intro || []"
        :key="`intro-${index}`"
        class="document-card__paragraph"
      >
        {{ paragraph }}
      </text>

      <view
        v-for="section in currentDocument.sections || []"
        :key="section.heading"
        class="document-card__section"
      >
        <text class="document-card__heading">{{ section.heading }}</text>
        <text
          v-for="(paragraph, index) in section.paragraphs || []"
          :key="`${section.heading}-${index}`"
          class="document-card__paragraph"
        >
          {{ paragraph }}
        </text>
      </view>
    </view>

    <view v-else class="card">
      <EmptyState title="协议加载失败" desc="请稍后重试。" />
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import EmptyState from '../../components/EmptyState.vue'
import { getLegalDocuments } from '../../api/legal'
import { agreeTerms } from '../../api/user'
import { useUserStore } from '../../stores/user'
import { toast } from '../../utils/navigation'

const userStore = useUserStore()
const documents = ref({
  latestVersion: '',
  updatedAt: '',
  effectiveAt: '',
  documents: []
})
const activeType = ref('user_agreement')
const agreeLoading = ref(false)

const documentList = computed(() => documents.value.documents || [])
const currentDocument = computed(() => documentList.value.find((item) => item.type === activeType.value) || documentList.value[0] || null)

onLoad(() => {
  loadDocuments()
})

async function loadDocuments() {
  try {
    documents.value = await getLegalDocuments()
    if (!documentList.value.find((item) => item.type === activeType.value) && documentList.value.length) {
      activeType.value = documentList.value[0].type
    }
  } catch (error) {
    toast(error?.message || '协议内容加载失败')
  }
}

async function agreeLatest() {
  if (!documents.value.latestVersion) return
  agreeLoading.value = true
  try {
    await agreeTerms(documents.value.latestVersion)
    await userStore.loadUserInfo().catch(() => null)
    toast('已同意最新版', 'success')
  } catch (error) {
    toast(error?.message || '协议确认失败')
  } finally {
    agreeLoading.value = false
  }
}
</script>

<style scoped>
.page-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 180rpx;
  gap: 16rpx;
  align-items: start;
}

.page-head__button {
  min-height: 76rpx;
}

.tab-card {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}

.tab-card__item {
  padding: 20rpx;
  border-radius: 16rpx;
  background: #f8fbff;
}

.tab-card__item--active {
  background: #EAF5FF;
}

.tab-card__title,
.tab-card__meta,
.document-card__title,
.document-card__meta,
.document-card__heading,
.document-card__paragraph {
  display: block;
}

.tab-card__title,
.document-card__title,
.document-card__heading {
  color: #172033;
  font-weight: 800;
}

.tab-card__title {
  font-size: 28rpx;
}

.tab-card__meta,
.document-card__meta {
  margin-top: 8rpx;
  color: #64748B;
  font-size: 23rpx;
}

.document-card__title {
  font-size: 34rpx;
}

.document-card__section + .document-card__section {
  margin-top: 18rpx;
}

.document-card__heading {
  margin-bottom: 10rpx;
  font-size: 29rpx;
}

.document-card__paragraph {
  margin-top: 10rpx;
  color: #2a3648;
  font-size: 25rpx;
  line-height: 1.8;
  white-space: pre-wrap;
}
</style>
