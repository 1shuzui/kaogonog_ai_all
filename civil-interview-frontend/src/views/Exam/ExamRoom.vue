<template>
  <MockInterviewRoom v-if="examStore.mockMode" />
  <StandardExamRoom v-else />
</template>

<script setup>
import { useExamStore } from '@/stores/exam'
import MockInterviewRoom from '@/components/exam/MockInterviewRoom.vue'
import StandardExamRoom from '@/components/exam/StandardExamRoom.vue'

const examStore = useExamStore()
</script>
