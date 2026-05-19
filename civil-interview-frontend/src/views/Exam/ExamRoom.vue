<template>
  <FullExamRoom v-if="examStore.fullExamMode" />
  <StandardExamRoom v-else />
</template>

<script setup>
import { useExamStore } from '@/stores/exam'
import FullExamRoom from '@/components/exam/FullExamRoom.vue'
import StandardExamRoom from '@/components/exam/StandardExamRoom.vue'

const examStore = useExamStore()
</script>
