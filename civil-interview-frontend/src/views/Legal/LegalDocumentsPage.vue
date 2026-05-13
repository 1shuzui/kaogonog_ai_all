<template>
  <div class="legal-page page-container">
    <div class="legal-page__header card">
      <a-button type="text" @click="goBack">返回</a-button>
      <div>
        <h2>用户协议与隐私协议</h2>
        <p>版本 {{ documents.latestVersion || '-' }}，更新于 {{ documents.updatedAt || '-' }}</p>
      </div>
      <a-button v-if="showAgreeAction" type="primary" :loading="agreeLoading" @click="agreeLatest">
        同意最新版
      </a-button>
    </div>

    <a-spin :spinning="loading">
      <a-empty v-if="!documentList.length && !loading" description="协议内容加载失败" :image="false" />

      <div v-else class="legal-page__content">
        <div class="legal-page__toc card">
          <div
            v-for="item in documentList"
            :key="item.type"
            class="legal-page__toc-item"
            :class="{ 'legal-page__toc-item--active': activeTab === item.type }"
            @click="activeTab = item.type"
          >
            <strong>{{ item.title }}</strong>
            <span>{{ item.updatedAt }}</span>
          </div>
        </div>

        <div class="legal-page__doc card" v-if="currentDocument">
          <div class="legal-page__doc-head">
            <h3>{{ currentDocument.title }}</h3>
            <p>生效日期：{{ currentDocument.effectiveAt || '-' }}</p>
          </div>
          <p
            v-for="(paragraph, index) in currentDocument.intro || []"
            :key="`intro-${index}`"
            class="legal-page__paragraph"
          >
            {{ paragraph }}
          </p>

          <section
            v-for="section in currentDocument.sections || []"
            :key="section.heading"
            class="legal-page__section"
          >
            <h4>{{ section.heading }}</h4>
            <p
              v-for="(paragraph, index) in section.paragraphs || []"
              :key="`${section.heading}-${index}`"
              class="legal-page__paragraph"
            >
              {{ paragraph }}
            </p>
          </section>
        </div>
      </div>
    </a-spin>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { getLegalDocuments } from '@/api/legal'
import http from '@/api/index'

const router = useRouter()
const loading = ref(false)
const agreeLoading = ref(false)
const documents = ref({
  latestVersion: '',
  updatedAt: '',
  effectiveAt: '',
  documents: []
})
const activeTab = ref('user_agreement')

const documentList = computed(() => documents.value?.documents || [])
const currentDocument = computed(() => documentList.value.find((item) => item.type === activeTab.value) || documentList.value[0] || null)
const showAgreeAction = computed(() => !!localStorage.getItem('token'))

onMounted(loadDocuments)

async function loadDocuments() {
  loading.value = true
  try {
    documents.value = await getLegalDocuments()
    if (!documentList.value.find((item) => item.type === activeTab.value) && documentList.value.length) {
      activeTab.value = documentList.value[0].type
    }
  } catch (error) {
    message.error(error?.normalizedMessage || error?.message || '协议内容加载失败')
  } finally {
    loading.value = false
  }
}

async function agreeLatest() {
  if (!documents.value.latestVersion) return
  agreeLoading.value = true
  try {
    await http.post('/user/agree-terms', {
      version: documents.value.latestVersion
    })
    message.success('已同意最新版协议')
  } catch {
    // handled by interceptor
  } finally {
    agreeLoading.value = false
  }
}

function goBack() {
  if (window.history.length > 1) {
    router.back()
    return
  }
  router.push('/profile/account')
}
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.legal-page {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.legal-page__header {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  padding: 16px 18px;

  h2 {
    margin: 0;
    color: @text-primary;
    font-size: @font-size-xl;
  }

  p {
    margin: 6px 0 0;
    color: @text-secondary;
  }
}

.legal-page__content {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 14px;
}

.legal-page__toc {
  padding: 12px;
  align-self: start;
}

.legal-page__toc-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  border-radius: 10px;
  cursor: pointer;

  strong {
    color: @text-primary;
  }

  span {
    color: @text-secondary;
    font-size: @font-size-xs;
  }
}

.legal-page__toc-item--active {
  background: rgba(27, 95, 170, 0.08);
}

.legal-page__doc {
  padding: 20px;
}

.legal-page__doc-head {
  margin-bottom: 18px;

  h3 {
    margin: 0;
    color: @text-primary;
    font-size: @font-size-lg;
  }

  p {
    margin: 6px 0 0;
    color: @text-secondary;
  }
}

.legal-page__section + .legal-page__section {
  margin-top: 18px;
}

.legal-page__section h4 {
  margin: 0 0 10px;
  color: @text-primary;
  font-size: @font-size-base;
}

.legal-page__paragraph {
  margin: 0 0 10px;
  color: @text-regular;
  line-height: 1.9;
  white-space: pre-wrap;
}

@media (max-width: 960px) {
  .legal-page__header,
  .legal-page__content {
    grid-template-columns: 1fr;
  }
}
</style>
