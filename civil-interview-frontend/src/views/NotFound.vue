<!--
这个网页 404 页在路由找不到时出现；它给用户一个回首页的出口，避免空白页被误以为系统崩了。

@param: 无；页面运行时从 props、路由参数、Pinia 状态和用户点击中拿数据。
@return: 渲染当前业务界面，并把按钮、表单或跳转事件交给既有流程处理。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
<template>
  <div class="not-found">
    <div class="content">
      <h1>404</h1>
      <p>页面未找到</p>
      <a-button type="primary" @click="$router.push('/')">
        返回首页
      </a-button>
    </div>
  </div>
</template>

<style scoped>
.not-found {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  text-align: center;
}

.content h1 {
  font-size: 120px;
  color: #1B5FAA;
  margin: 0;
}

.content p {
  font-size: 20px;
  color: #666;
  margin: 20px 0 30px;
}
</style>
