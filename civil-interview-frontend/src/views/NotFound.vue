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
