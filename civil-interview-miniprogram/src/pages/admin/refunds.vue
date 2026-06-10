<!--
小程序退款管理页用于管理员临时核对可退额度并发起微信虚拟支付退款，支付真源必须以后端和微信结果为准。
页面不能修改权益余额或伪造支付状态；退款成功后的权益扣减、流水和订单状态由服务端统一处理。

@param: 无；页面读取管理员身份、查询条件、退款表单和后端返回的可退额度。
@return: 渲染额度查询、订单摘要和退款提交表单。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
<template>
  <view class="page">
    <text class="page-title">退款管理</text>
    <text class="page-desc">按用户或订单查询可退额度，并通过微信官方小程序虚拟支付退款接口处理。</text>

    <view v-if="!userStore.isAdmin" class="card">
      <EmptyState title="无管理员权限" desc="请使用管理员账号登录后再访问。" />
    </view>

    <template v-else>
      <view class="card">
        <view class="section-head">
          <text class="section-title">退款额度</text>
        </view>
        <input v-model="statsForm.username" class="field" placeholder="用户名，可留空" />
        <input v-model="statsForm.orderNo" class="field field--mt" placeholder="订单号，可留空" />
        <button class="primary-button form-button" :loading="statsLoading" @tap="fetchStats">查询额度</button>
      </view>

      <view v-if="stats" class="card">
        <view class="section-head">
          <text class="section-title">查询结果</text>
          <text class="muted">{{ stats.username || statsForm.username || '-' }}</text>
        </view>
        <view class="metric-grid">
          <view class="metric">
            <text class="metric__value">{{ stats.summary?.refundableHours ?? 0 }}</text>
            <text class="metric__label">可退小时</text>
          </view>
          <view class="metric">
            <text class="metric__value">¥{{ formatMoney(stats.summary?.refundableAmount) }}</text>
            <text class="metric__label">可退金额</text>
          </view>
          <view class="metric">
            <text class="metric__value">{{ stats.total ?? 0 }}</text>
            <text class="metric__label">订单数</text>
          </view>
        </view>
        <view v-for="item in stats.list || []" :key="item.orderNo" class="refund-order" @tap="fillRefundOrder(item)">
          <text class="refund-order__no">{{ item.orderNo }}</text>
          <text class="refund-order__amount">可退 {{ item.refundableHours || 0 }} 小时 / ¥{{ formatMoney(item.refundableAmount) }}</text>
        </view>
      </view>

      <view class="card">
        <view class="section-head">
          <text class="section-title">微信虚拟支付退款</text>
        </view>
        <input v-model="refundForm.orderNo" class="field" placeholder="订单号" />
        <input v-model="refundForm.refundedHours" class="field field--mt" type="number" placeholder="退款小时数，可留空" />
        <input v-model="refundForm.refundReason" class="field field--mt" placeholder="退款原因" />
        <textarea v-model="refundForm.refundRemark" class="textarea-field field--mt" placeholder="退款备注" />
        <button class="primary-button form-button" :loading="refundLoading" @tap="submitRefund">提交退款</button>
      </view>
    </template>
  </view>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import EmptyState from '../../components/EmptyState.vue'
import { applyRefund, getRefundBalanceStats } from '../../api/payment'
import { useUserStore } from '../../stores/user'
import { requireLogin, toast } from '../../utils/navigation'

const userStore = useUserStore()
const statsLoading = ref(false)
const refundLoading = ref(false)
const stats = ref(null)
const statsForm = reactive({
  username: '',
  orderNo: ''
})
const refundForm = reactive({
  orderNo: '',
  refundedHours: '',
  refundReason: '',
  refundRemark: ''
})

onShow(() => {
  if (!requireLogin()) return
  userStore.loadUserInfo().catch(() => null)
})

async function fetchStats() {
  statsLoading.value = true
  try {
    stats.value = await getRefundBalanceStats({
      username: statsForm.username.trim() || undefined,
      orderNo: statsForm.orderNo.trim() || undefined
    })
    if (!refundForm.orderNo && statsForm.orderNo) refundForm.orderNo = statsForm.orderNo.trim()
  } catch (error) {
    toast(error?.message || '退款额度查询失败')
  } finally {
    statsLoading.value = false
  }
}

function formatMoney(value) {
  return Number(value || 0).toFixed(2)
}

function fillRefundOrder(item = {}) {
  refundForm.orderNo = item.orderNo || ''
  if (item.refundableHours !== undefined) {
    refundForm.refundedHours = String(item.refundableHours)
  }
}

function confirmModal(options) {
  return new Promise((resolve) => {
    uni.showModal({
      ...options,
      success(res) {
        resolve(res.confirm)
      },
      fail() {
        resolve(false)
      }
    })
  })
}

async function submitRefund() {
  const orderNo = refundForm.orderNo.trim()
  if (!orderNo) {
    toast('请填写订单号')
    return
  }
  const confirmed = await confirmModal({
    title: '确认退款',
    content: '提交后将调用微信官方小程序虚拟支付退款接口，并按比例扣减订阅时长。',
    confirmText: '确认'
  })
  if (!confirmed) return

  refundLoading.value = true
  try {
    const refundedHours = refundForm.refundedHours === '' ? undefined : Number(refundForm.refundedHours)
    await applyRefund({
      orderNo,
      refundedHours,
      refundReason: refundForm.refundReason.trim() || undefined,
      refundRemark: refundForm.refundRemark.trim() || undefined
    })
    toast('退款已提交', 'success')
    fetchStats()
  } catch (error) {
    toast(error?.message || '退款提交失败')
  } finally {
    refundLoading.value = false
  }
}
</script>

<style scoped>
.field--mt {
  margin-top: 16rpx;
}

.form-button {
  margin-top: 18rpx;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14rpx;
}

.metric {
  padding: 20rpx 8rpx;
  border-radius: 14rpx;
  background: #f6f8fb;
  text-align: center;
}

.metric__value,
.metric__label {
  display: block;
}

.metric__value {
  color: #2F7FD6;
  font-size: 32rpx;
  font-weight: 900;
}

.metric__label {
  margin-top: 6rpx;
  color: #64748B;
  font-size: 22rpx;
}

.refund-order {
  margin-top: 18rpx;
  padding-top: 18rpx;
  border-top: 1rpx solid #eef2f6;
}

.refund-order__no,
.refund-order__amount {
  display: block;
}

.refund-order__no {
  color: #172033;
  font-size: 25rpx;
  font-weight: 800;
}

.refund-order__amount {
  margin-top: 6rpx;
  color: #64748B;
  font-size: 23rpx;
}
</style>
