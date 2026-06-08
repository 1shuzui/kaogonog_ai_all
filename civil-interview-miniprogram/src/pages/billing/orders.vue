<!--
这个小程序订单页展示虚拟支付订单状态，方便用户确认开通、待支付或退款进度。

@param: 无；页面运行时从 props、路由参数、Pinia 状态和用户点击中拿数据。
@return: 渲染当前业务界面，并把按钮、表单或跳转事件交给既有流程处理。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
<template>
  <view class="page">
    <view class="page-head">
      <view>
        <text class="page-title">订单记录</text>
        <text class="page-desc">支付状态以服务端订单与微信官方小程序虚拟支付结果为准。</text>
      </view>
      <button class="secondary-button page-head__button" :loading="loading" @tap="fetchOrders">刷新</button>
    </view>

    <view v-if="orders.length">
      <view
        v-for="order in orders"
        :key="order.orderNo || order.order_no"
        class="card order-card"
        @tap="selectOrder(order)"
      >
        <view class="order-card__main">
          <view>
            <text class="order-card__title">{{ order.packageName || order.planName || order.packageCode || '套餐订单' }}</text>
            <text class="order-card__meta">{{ order.orderNo || order.order_no }}</text>
          </view>
          <view class="order-card__side">
            <text class="order-card__amount">¥{{ formatAmount(order.amount || order.amountYuan || order.amountTotal) }}</text>
            <text class="order-card__status" :class="`order-card__status--${order.status || 'created'}`">
              {{ statusText(order.status) }}
            </text>
          </view>
        </view>
        <text class="order-card__time">{{ formatDate(order.createdAt || order.created_at || order.paidAt || order.paid_at) }}</text>
      </view>
    </view>
    <view v-else class="card">
      <EmptyState title="暂无订单" desc="开通套餐后可在这里查看支付记录。" />
    </view>

    <view v-if="selectedOrder" class="card detail-card">
      <view class="section-head">
        <text class="section-title">订单详情</text>
        <text class="muted">{{ statusText(selectedOrder.status) }}</text>
      </view>
      <view class="detail-row">
        <text>订单号</text>
        <text>{{ selectedOrder.orderNo || selectedOrder.order_no }}</text>
      </view>
      <view class="detail-row">
        <text>套餐</text>
        <text>{{ selectedOrder.packageName || selectedOrder.planName || selectedOrder.packageCode || '-' }}</text>
      </view>
      <view class="detail-row">
        <text>金额</text>
        <text>¥{{ formatAmount(selectedOrder.amount || selectedOrder.amountYuan || selectedOrder.amountTotal) }}</text>
      </view>
      <view class="detail-row">
        <text>支付渠道</text>
        <text>{{ selectedOrder.payChannel || selectedOrder.pay_channel || 'wechat_virtual' }}</text>
      </view>
      <view class="detail-row">
        <text>支付时间</text>
        <text>{{ formatDate(selectedOrder.paidAt || selectedOrder.paid_at) || '-' }}</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import EmptyState from '../../components/EmptyState.vue'
import { getMyPaymentOrders, getPaymentOrder } from '../../api/payment'
import { formatDate, normalizeListResponse } from '../../utils/format'
import { hideLoading, requireLogin, showLoading, toast } from '../../utils/navigation'

const orders = ref([])
const selectedOrder = ref(null)
const loading = ref(false)

onShow(() => {
  if (!requireLogin()) return
  fetchOrders()
})

function normalizeOrders(payload) {
  return normalizeListResponse(payload).list
}

function formatAmount(value) {
  const amount = Number(value || 0)
  if (amount > 1000 && Number.isInteger(amount)) return (amount / 100).toFixed(2)
  return amount.toFixed(2)
}

function statusText(status = '') {
  const map = {
    created: '待支付',
    pending: '待支付',
    paid: '已支付',
    failed: '支付失败',
    closed: '已关闭',
    refunded: '已退款',
    partial_refunded: '部分退款'
  }
  return map[status] || status || '待支付'
}

async function fetchOrders() {
  loading.value = true
  try {
    orders.value = normalizeOrders(await getMyPaymentOrders())
    if (!orders.value.some((item) => (item.orderNo || item.order_no) === (selectedOrder.value?.orderNo || selectedOrder.value?.order_no))) {
      selectedOrder.value = null
    }
  } catch (error) {
    toast(error?.message || '订单加载失败')
  } finally {
    loading.value = false
  }
}

async function selectOrder(order) {
  const orderNo = order.orderNo || order.order_no
  if (!orderNo) return
  showLoading('加载订单')
  try {
    selectedOrder.value = await getPaymentOrder(orderNo)
  } catch (error) {
    selectedOrder.value = order
    toast(error?.message || '订单详情加载失败')
  } finally {
    hideLoading()
  }
}
</script>

<style scoped>
.page-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 140rpx;
  gap: 18rpx;
  align-items: start;
}

.page-head__button {
  min-height: 76rpx;
}

.order-card {
  padding: 24rpx;
}

.order-card__main {
  display: flex;
  justify-content: space-between;
  gap: 18rpx;
}

.order-card__title,
.order-card__meta,
.order-card__amount,
.order-card__status,
.order-card__time {
  display: block;
}

.order-card__title {
  color: #1a1a2e;
  font-size: 30rpx;
  font-weight: 800;
}

.order-card__meta,
.order-card__time {
  margin-top: 8rpx;
  color: #6f7c8f;
  font-size: 23rpx;
}

.order-card__side {
  min-width: 150rpx;
  text-align: right;
}

.order-card__amount {
  color: #1b5faa;
  font-size: 32rpx;
  font-weight: 900;
}

.order-card__status {
  margin-top: 8rpx;
  color: #6f7c8f;
  font-size: 23rpx;
  font-weight: 700;
}

.order-card__status--paid {
  color: #389e0d;
}

.order-card__status--failed,
.order-card__status--closed {
  color: #cf1322;
}

.detail-card {
  margin-top: 8rpx;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  gap: 20rpx;
  padding: 16rpx 0;
  border-bottom: 1rpx solid #eef2f6;
  color: #2a3648;
  font-size: 25rpx;
}

.detail-row:last-child {
  border-bottom: 0;
}

.detail-row text:last-child {
  flex: 1;
  color: #1a1a2e;
  font-weight: 700;
  text-align: right;
  word-break: break-all;
}
</style>
