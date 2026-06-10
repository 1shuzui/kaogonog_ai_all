<!--
页面容器组件，统一留白、宽度和背景，让页面只关心业务内容。

@param: 通过 props、slot 和事件接收页面上下文；不直接拥有业务真源。
@return: 渲染可复用 UI，并通过 emit 或插槽把操作交还给父页面。
@raises: 不主动抛业务异常；异常状态应由父页面、请求层或兜底 UI 承接。
-->
<template>
  <div class="page-container">
    <slot />
  </div>
</template>

<script setup>
</script>
