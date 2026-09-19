<template>
  <image class="learner-icon" :src="`/static/learner-icons/${name}.svg`" :style="{ width: `${size}px`, height: `${size}px` }" mode="aspectFit" aria-hidden="true" />
</template>
<script setup>
defineProps({ name: { type: String, required: true }, size: { type: Number, default: 24 } })
</script>
<style scoped>
.learner-icon { display: inline-block; flex-shrink: 0; vertical-align: middle; }
</style>
