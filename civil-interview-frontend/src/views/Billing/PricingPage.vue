<!--
PC 套餐中心页面，负责展示可开通的虚拟训练权益、当前权益状态和支付入口。

套餐价格和道具口径由后端与微信虚拟支付配置决定，前端只展示和发起开通，不在页面里硬编码真实到账逻辑。
支付前必须确认登录，支付成功后的权益刷新走订阅接口，避免页面自己推算余额。

@param: 无；套餐和权益状态来自 billing/subscription 相关 store 与 API。
@return: 渲染套餐列表、当前权益、开通按钮和支付状态提示。
@raises: 不主动抛业务异常；支付失败、未登录和接口错误由请求层与页面提示承接。
-->
<template>
  <div class="pricing-page page-container">
    <div class="pricing-hero card">
      <div class="pricing-hero__copy">
        <span class="pricing-hero__eyebrow">套餐方案</span>
        <h1>解锁更完整的面试训练</h1>
        <p>
          试用用户可以先体验 1 道引导题。所有付费虚拟训练权益
          均需在微信小程序套餐中心通过官方小程序虚拟支付开通。
        </p>
        <div class="pricing-hero__chips">
          <span>单题试用</span>
          <span>小程序虚拟支付</span>
          <span>权益同步</span>
          <span>录音/录像评分</span>
        </div>
      </div>

      <div class="pricing-hero__status">
        <div class="pricing-status-card">
          <span class="pricing-status-card__label">当前套餐</span>
          <strong>{{ billingStore.planLabel }}</strong>
          <p>{{ billingStore.planStatusText }}</p>
          <a-button
            v-if="billingStore.isPaid"
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

    <div class="pricing-risk card">
      <div class="pricing-risk__head">
        <h3>开通前风险提示</h3>
        <span>请务必阅读</span>
      </div>
      <div class="pricing-risk__list">
        <div class="pricing-risk__item">账号权益建议仅限本人使用，不建议多人共用。</div>
        <div class="pricing-risk__item">付费套餐允许叠加，系统会优先消耗更早到期或更早开通的权益余额。</div>
        <div class="pricing-risk__item">多设备同时登录或多人切换使用，可能导致练习记录、录音、评分结果出现错位或覆盖。</div>
        <div class="pricing-risk__item">付费虚拟训练权益只能在微信小程序内通过官方小程序虚拟支付开通；PC 端仅用于查看套餐与核对权益。</div>
        <div class="pricing-risk__item">如果出现订单、权限或设备异常，请通过个人中心的客服反馈入口联系管理员处理。</div>
      </div>
      <div class="pricing-risk__actions">
        <a-button @click="router.push('/profile')">前往客服反馈</a-button>
      </div>
    </div>

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
            :loading="purchasingPlanKey === plan.key"
            :disabled="isCurrentPlan(plan.key)"
            @click="activatePlan(plan)"
          >
            {{ isCurrentPlan(plan.key) ? '当前套餐' : '小程序虚拟支付开通' }}
          </a-button>
        </template>
      </div>
    </div>

    <div class="pricing-support card">
      <div class="pricing-support__header">
        <h3>已解锁模块</h3>
        <span>后端权益联动</span>
      </div>
      <div class="pricing-support__grid">
        <div v-for="moduleName in PREMIUM_MODULES" :key="moduleName" class="pricing-support__item">
          {{ moduleName }}
        </div>
      </div>
      <p class="pricing-support__note">
        PC 端用于查看套餐和核对权益；所有付费套餐均在微信小程序套餐中心通过官方小程序虚拟支付开通，
        支付完成后以服务端虚拟支付订单与账户权益同步结果为准，重复开通会叠加到同一账号。
      </p>
    </div>
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
const purchasingPlanKey = ref('')
const MINI_PROGRAM_PRICING_PATH = '/pages/pricing/index'

function resolvePostPurchaseTarget() {
  const target = redirectTarget.value || '/'
  if (!billingStore.isPaid) return target
  if (!target.startsWith('/exam/prepare')) return target
  return '/exam/prepare'
}

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
  billingStore.clearPaywallIntent()
  router.push(resolvePostPurchaseTarget())
}

async function activatePlan(plan) {
  if (!userStore.isAuthenticated) {
    router.push({ path: '/login', query: { redirect: '/pricing' } })
    return
  }
  if (!plan?.packageCode) {
    message.warning('当前套餐暂未配置后端套餐编码')
    return
  }
  purchasingPlanKey.value = plan.key
  try {
    await navigator.clipboard?.writeText(MINI_PROGRAM_PRICING_PATH)
    message.success(`请在微信小程序套餐中心完成官方虚拟支付，路径已复制：${MINI_PROGRAM_PRICING_PATH}`)
  } catch {
    message.info(`请在微信小程序套餐中心完成官方虚拟支付：${MINI_PROGRAM_PRICING_PATH}`)
  } finally {
    purchasingPlanKey.value = ''
  }
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

.pricing-risk {
  margin-top: 18px;
  padding: 18px 20px;
  border-radius: 22px;
  border: 1px solid rgba(212, 135, 25, 0.18);
  background: linear-gradient(180deg, #fffaf1 0%, #fffefb 100%);
}

.pricing-risk__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.pricing-risk__head h3 {
  margin: 0;
  color: @text-primary;
  font-size: @font-size-lg;
}

.pricing-risk__head span {
  color: #8a4d17;
  font-size: @font-size-xs;
  font-weight: 600;
}

.pricing-risk__list {
  display: grid;
  gap: 10px;
}

.pricing-risk__actions {
  margin-top: 14px;
}

.pricing-risk__item {
  position: relative;
  padding-left: 16px;
  color: @text-regular;
  font-size: @font-size-sm;
  line-height: 1.8;
}

.pricing-risk__item::before {
  content: '';
  position: absolute;
  top: 10px;
  left: 0;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #d48806;
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
