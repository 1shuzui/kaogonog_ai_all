<template>
  <a-modal
    :open="billingStore.paywallVisible"
    title="功能受限"
    :footer="null"
    @cancel="billingStore.closePaywall()"
  >
    <div class="billing-paywall">
      <span class="billing-paywall__eyebrow">需要开通</span>
      <h3>{{ billingStore.paywallSource || billingStore.lastPaywallSource || '付费功能' }}</h3>
      <p>
        当前试用模式下暂未开放该功能。你可以先免费体验 1 道试用题，
        或前往套餐页开通完整训练能力。
      </p>
      <div class="billing-paywall__actions">
        <a-button @click="startTrial">先试用</a-button>
        <a-button type="primary" @click="goPricing">查看套餐</a-button>
      </div>
    </div>
  </a-modal>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useBillingStore } from '@/stores/billing'

const router = useRouter()
const billingStore = useBillingStore()

function startTrial() {
  billingStore.closePaywall()
  router.push({ path: '/exam/prepare', query: { trial: '1' } })
}

function goPricing() {
  billingStore.closePaywall()
  router.push({
    path: '/pricing',
    query: {
      redirect: billingStore.lastIntendedPath || '/',
      source: billingStore.lastPaywallSource || billingStore.paywallSource || '付费功能'
    }
  })
}
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.billing-paywall {
  text-align: center;
}

.billing-paywall__eyebrow {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(27, 95, 170, 0.08);
  color: @primary-color;
  font-size: @font-size-xs;
  font-weight: 600;
}

.billing-paywall h3 {
  margin: 12px 0 8px;
  color: @text-primary;
  font-size: @font-size-lg;
}

.billing-paywall p {
  margin: 0;
  color: @text-secondary;
  line-height: 1.8;
}

.billing-paywall__actions {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-top: 18px;
}
</style>
