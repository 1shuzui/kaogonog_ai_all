<template>
  <div class="pricing-page page-container">
    <div class="pricing-hero card">
      <div class="pricing-hero__copy">
        <span class="pricing-hero__eyebrow">套餐方案</span>
        <h1>解锁更完整的面试训练</h1>
        <p>
          普通用户未开通时只能体验 1 道试用题。开通后可解锁完整模拟面试、
          定向备考和专项训练，题库管理仅管理员可用。
        </p>
        <div class="pricing-hero__chips">
          <span>单题试用</span>
          <span>服务端鉴权</span>
          <span>账号级套餐</span>
        </div>
      </div>

      <div class="pricing-hero__status">
        <div class="pricing-status-card">
          <span class="pricing-status-card__label">当前套餐</span>
          <strong>{{ currentPlanLabel }}</strong>
          <p>{{ currentPlanStatus }}</p>
          <a-button
            v-if="canContinue"
            class="pricing-status-card__cta"
            type="primary"
            @click="goNextStep"
          >
            继续使用
          </a-button>
          <a-button
            v-else
            class="pricing-status-card__cta"
            type="primary"
            ghost
            @click="startTrial"
          >
            开始试用
          </a-button>
        </div>
      </div>
    </div>

    <a-alert
      v-if="paywallSource"
      class="pricing-paywall-tip"
      type="warning"
      show-icon
      :message="`你刚刚从“${paywallSource}”跳转到套餐页`"
    />

    <div class="pricing-grid">
      <div
        v-for="plan in plans"
        :key="plan.key"
        class="pricing-card card"
        :class="{
          'pricing-card--trial': plan.key === BILLING_PLAN_KEYS.TRIAL,
          'pricing-card--active': isCurrentPlan(plan.key)
        }"
      >
        <div class="pricing-card__badge">{{ plan.badge }}</div>
        <h3>{{ plan.title }}</h3>
        <div class="pricing-card__price">{{ plan.priceText }}</div>
        <p class="pricing-card__desc">{{ plan.description }}</p>
        <div class="pricing-card__features">
          <div v-for="feature in plan.features" :key="feature" class="pricing-card__feature">
            {{ feature }}
          </div>
        </div>

        <template v-if="plan.key === BILLING_PLAN_KEYS.TRIAL">
          <div class="pricing-card__trial">
            <span>题型：{{ trialQuestion.questionType }}</span>
            <span>维度：{{ trialQuestion.dimension }}</span>
          </div>
          <a-button size="large" block @click="startTrial">体验试用题</a-button>
        </template>

        <template v-else>
          <a-button
            size="large"
            block
            :type="isCurrentPlan(plan.key) ? 'default' : 'primary'"
            @click="activatePlan(plan.key)"
          >
            {{ isCurrentPlan(plan.key) ? '当前套餐' : '立即开通' }}
          </a-button>
        </template>
      </div>
    </div>

    <div class="pricing-support card">
      <div class="pricing-support__header">
        <h3>已解锁模块</h3>
        <span>账号级权限已联动</span>
      </div>
      <div class="pricing-support__grid">
        <div v-for="moduleName in PREMIUM_MODULES" :key="moduleName" class="pricing-support__item">
          {{ moduleName }}
        </div>
      </div>
      <p class="pricing-support__note">
        当前页面仍是演示开通流程，但套餐状态已经写回当前账号，
        并由后端接口统一执行权限校验。
      </p>
    </div>

    <a-modal
      v-model:open="successVisible"
      title="开通成功"
      :footer="null"
      @cancel="successVisible = false"
    >
      <div v-if="latestOrder" class="pricing-success">
        <div class="pricing-success__amount">¥{{ latestOrder.amount }}</div>
        <div class="pricing-success__title">{{ latestOrder.title }}</div>
        <p>{{ latestOrder.summary }}</p>
        <div class="pricing-success__meta">
          <span>订单号：{{ latestOrder.id }}</span>
          <span>状态：已支付</span>
        </div>
        <div class="pricing-success__actions">
          <a-button @click="goOrders">查看订单</a-button>
          <a-button type="primary" @click="goNextStep">继续使用</a-button>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useBillingStore } from '@/stores/billing'
import { useUserStore } from '@/stores/user'
import { BILLING_PLANS, BILLING_PLAN_KEYS, PREMIUM_MODULES } from '@/utils/billing'

const route = useRoute()
const router = useRouter()
const billingStore = useBillingStore()
const userStore = useUserStore()

const plans = BILLING_PLANS
const paywallSource = computed(() => String(route.query.source || billingStore.lastPaywallSource || ''))
const redirectTarget = computed(() => String(route.query.redirect || billingStore.lastIntendedPath || '/'))
const trialQuestion = computed(() => billingStore.trialQuestion)
const currentPlanLabel = computed(() => (userStore.isAdmin ? '管理员' : billingStore.planLabel))
const currentPlanStatus = computed(() => (
  userStore.isAdmin
    ? '管理员账号默认开放全部功能，题库管理仅管理员可用'
    : billingStore.planStatusText
))
const canContinue = computed(() => userStore.isAdmin || billingStore.isPaid)
const successVisible = ref(false)
const latestOrder = ref(null)

function isCurrentPlan(planKey) {
  if (planKey === BILLING_PLAN_KEYS.HOURLY) {
    return billingStore.isHourlyPlan && billingStore.remainingSeconds > 0
  }
  if (planKey === BILLING_PLAN_KEYS.MONTHLY) {
    return billingStore.isMonthlyActive
  }
  return billingStore.isTrialOnly
}

function startTrial() {
  billingStore.clearPaywallIntent()
  router.push({ path: '/exam/prepare', query: { trial: '1' } })
}

function goNextStep() {
  successVisible.value = false
  billingStore.clearPaywallIntent()
  router.push(redirectTarget.value || '/')
}

function goOrders() {
  successVisible.value = false
  router.push('/profile/orders')
}

async function activatePlan(planKey) {
  if (!userStore.isAuthenticated) {
    router.push({ path: '/login', query: { redirect: route.fullPath } })
    return
  }
  latestOrder.value = await billingStore.activatePlan(planKey)
  message.success(`已开通：${latestOrder.value?.title || '套餐'}`)
  successVisible.value = true
}
</script>

<style lang="less" scoped>
@import '@/styles/variables.less';

.pricing-page {
  padding-top: 12px;
}

.pricing-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(240px, 320px);
  gap: 20px;
  padding: 28px;
  border-radius: 24px;
  background:
    radial-gradient(circle at top right, rgba(255, 255, 255, 0.18), transparent 28%),
    linear-gradient(135deg, #15477a 0%, @primary-color 55%, #5fa0e8 100%);
  color: #fff;
  box-shadow: 0 28px 48px rgba(20, 72, 132, 0.2);
}

.pricing-hero__eyebrow {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  margin-bottom: 14px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.12);
  font-size: @font-size-xs;
  letter-spacing: 1.2px;
  text-transform: uppercase;
}

.pricing-hero__copy h1 {
  color: #fff;
  font-size: 36px;
  line-height: 1.14;
  margin-bottom: 10px;
}

.pricing-hero__copy p {
  color: rgba(255, 255, 255, 0.84);
  font-size: @font-size-base;
  line-height: 1.8;
  margin-bottom: 18px;
}

.pricing-hero__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.pricing-hero__chips span {
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  font-size: @font-size-xs;
  color: rgba(255, 255, 255, 0.94);
}

.pricing-status-card {
  height: 100%;
  min-height: 210px;
  padding: 18px;
  border-radius: 22px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(16px);
}

.pricing-status-card__label {
  display: block;
  margin-bottom: 10px;
  color: rgba(255, 255, 255, 0.78);
  font-size: @font-size-xs;
  letter-spacing: 1px;
  text-transform: uppercase;
}

.pricing-status-card strong {
  display: block;
  font-size: 28px;
  line-height: 1.2;
}

.pricing-status-card p {
  margin: 10px 0 18px;
  color: rgba(255, 255, 255, 0.84);
  font-size: @font-size-sm;
  line-height: 1.8;
}

.pricing-status-card__cta {
  height: 44px;
  border-radius: 14px;
}

.pricing-paywall-tip {
  margin-top: 16px;
}

.pricing-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-top: 18px;
}

.pricing-card {
  position: relative;
  overflow: hidden;
  padding: 22px 20px;
  border-radius: 22px;
  border: 1px solid rgba(27, 95, 170, 0.08);
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: 0 18px 32px rgba(21, 66, 126, 0.08);
  transition: transform 0.24s ease, box-shadow 0.24s ease;
}

.pricing-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 22px 36px rgba(21, 66, 126, 0.12);
}

.pricing-card--trial {
  background: linear-gradient(180deg, #ffffff 0%, #fffaf2 100%);
}

.pricing-card--active {
  border-color: rgba(27, 95, 170, 0.28);
  box-shadow: 0 22px 36px rgba(21, 66, 126, 0.14);
}

.pricing-card__badge {
  display: inline-flex;
  align-items: center;
  padding: 5px 10px;
  border-radius: 999px;
  background: rgba(27, 95, 170, 0.08);
  color: @primary-color;
  font-size: @font-size-xs;
  font-weight: 600;
}

.pricing-card h3 {
  margin: 14px 0 8px;
  color: @text-primary;
  font-size: 28px;
  line-height: 1.16;
}

.pricing-card__price {
  color: @primary-color;
  font-size: @font-size-sm;
  font-weight: 700;
}

.pricing-card__desc {
  min-height: 66px;
  margin: 12px 0;
  color: @text-secondary;
  font-size: @font-size-sm;
  line-height: 1.8;
}

.pricing-card__features {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 18px;
}

.pricing-card__feature {
  padding-left: 14px;
  color: @text-regular;
  font-size: @font-size-sm;
  line-height: 1.7;
  position: relative;
}

.pricing-card__feature::before {
  content: '';
  position: absolute;
  top: 9px;
  left: 0;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: linear-gradient(135deg, @primary-color 0%, @secondary-blue 100%);
}

.pricing-card__trial {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 18px;
  color: @text-secondary;
  font-size: @font-size-xs;
}

.pricing-support {
  margin-top: 18px;
  padding: 20px;
  border-radius: 22px;
  border: 1px solid rgba(27, 95, 170, 0.08);
  box-shadow: 0 18px 32px rgba(21, 66, 126, 0.08);
}

.pricing-support__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.pricing-support__header h3 {
  margin: 0;
  color: @text-primary;
  font-size: @font-size-lg;
}

.pricing-support__header span {
  color: @text-secondary;
  font-size: @font-size-xs;
}

.pricing-support__grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.pricing-support__item {
  padding: 12px 10px;
  border-radius: 16px;
  background: linear-gradient(180deg, #f4f8fd 0%, #ffffff 100%);
  text-align: center;
  color: @text-regular;
  font-size: @font-size-sm;
  font-weight: 600;
}

.pricing-support__note {
  margin: 14px 0 0;
  color: @text-secondary;
  font-size: @font-size-sm;
  line-height: 1.8;
}

.pricing-success {
  text-align: center;
}

.pricing-success__amount {
  color: @primary-color;
  font-size: 34px;
  font-weight: 700;
  line-height: 1.1;
}

.pricing-success__title {
  margin-top: 8px;
  color: @text-primary;
  font-size: @font-size-lg;
  font-weight: 600;
}

.pricing-success p {
  margin: 10px 0 12px;
  color: @text-secondary;
  line-height: 1.8;
}

.pricing-success__meta {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: @text-secondary;
  font-size: @font-size-xs;
}

.pricing-success__actions {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-top: 16px;
}

@media (max-width: 992px) {
  .pricing-hero,
  .pricing-grid,
  .pricing-support__grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 576px) {
  .pricing-page {
    padding-top: 8px;
  }

  .pricing-hero {
    padding: 22px 18px;
  }

  .pricing-hero__copy h1 {
    font-size: 30px;
  }

  .pricing-support {
    padding: 18px;
  }

  .pricing-support__header {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
