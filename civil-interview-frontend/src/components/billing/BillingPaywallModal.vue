<!--
这个弹窗在用户权益不足时出现，负责把“不能继续练习”的原因和套餐入口讲清楚，避免页面各自写一套拦截提示。

@param: 无；页面运行时从 props、路由参数、Pinia 状态和用户点击中拿数据。
@return: 渲染当前业务界面，并把按钮、表单或跳转事件交给既有流程处理。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
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
      <p>{{ paywallDescription }}</p>
      <div class="billing-paywall__actions">
        <a-button v-if="showTrialAction" @click="startTrial">先试用</a-button>
        <a-button type="primary" @click="goPricing">查看套餐</a-button>
      </div>
    </div>
  </a-modal>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useBillingStore } from '@/stores/billing'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const billingStore = useBillingStore()
const userStore = useUserStore()

const hasPaidHistory = computed(() => {
  const billing = userStore.userInfo?.billing || {}
  return billing.isPaid === true
    || billing.hasActivePlan === true
    || billing.trialCompleted === true
    || billingStore.isPaid
    || billingStore.recentOrders.some((order) => order.status === 'paid')
})

const showTrialAction = computed(() => !hasPaidHistory.value)
const paywallDescription = computed(() => {
  if (showTrialAction.value) {
    return '当前试用模式下暂未开放该功能。你可以先免费体验 1 道试用题，或前往套餐页开通完整训练能力。'
  }
  return '当前套餐额度不足或已到期，请前往套餐页开通、续费或查看订单权益。'
})

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
