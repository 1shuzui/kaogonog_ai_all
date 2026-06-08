<!--
这个页面容器统一网页端内容宽度和留白，避免不同页面在大屏上散得太开。

@param: 无；页面运行时从 props、路由参数、Pinia 状态和用户点击中拿数据。
@return: 渲染当前业务界面，并把按钮、表单或跳转事件交给既有流程处理。
@raises: 不主动抛业务异常；接口失败、未登录和权限不足由请求层或页面提示承接。
-->
<template>
  <div class="page-container">
    <slot />
  </div>
</template>

<script setup>
</script>
