<!--
404 页面，给错误路由一个温和回退入口，避免用户停在空白页。

这个页面不做权限判断，也不尝试修复路由；只提供回首页或返回上一页，减少错误链接带来的困惑。

@param: 无；仅使用当前路由和浏览器历史。
@return: 渲染 404 提示和返回入口。
@raises: 不主动抛业务异常。
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
