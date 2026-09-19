// Local-only component preview. No real login, exam, media upload or paid model calls.
// Vite's production entry remains index.html; this harness is never bundled for users.
import { createApp, h, ref } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import '../../src/styles/global.less'
import http from '../../src/api/index'
import { useExamStore } from '../../src/stores/exam'
import { useUserStore } from '../../src/stores/user'
import { useHistoryStore } from '../../src/stores/history'
import Home from '../../src/views/Home/HomePage.vue'
import Prepare from '../../src/views/Exam/ExamPrepare.vue'
import Room from '../../src/components/exam/FullExamRoom.vue'
import Result from '../../src/views/Result/ResultPage.vue'

const question = { id: 'visual-demo-question', stem: '【界面演示题】社区计划向周边群众开放食堂。有人认为方便群众，也有人担心影响日常工作。作为负责人，你将如何沟通并组织落实？请说明你的工作思路。', province: 'jiangsu', category: 'practical', prepTime: 90, answerTime: 180, assignedScore: 25 }
http.defaults.adapter = async (config) => ({ config, status: 200, statusText: 'OK', headers: {}, data: config.url?.includes('/questions/') ? question : [] })
const pinia = createPinia()
const exam = useExamStore(pinia)
exam.examId = 'visual-demo-exam'
exam.questionList = [question, { ...question, id: 'visual-demo-question-2' }]
exam.consumeStream = () => new MediaStream()
exam.answers = [{ examId: exam.examId, questionId: question.id, questionIndex: 0, questionStem: question.stem, processingStatus: 'failed', processingError: '演示：网络波动，文字稿仍在，可重试。', transcript: '【演示原文】我会先了解群众的实际需求，再协调食堂人员安排，明确开放时段、容量和服务规范。试运行后收集意见，及时优化。', scoringResult: null }]
exam.retryAnswer = async (answer) => {
  answer.processingStatus = 'scoring'
  answer.processingError = ''
}
const user = useUserStore(pinia)
user.selectedProvince = 'jiangsu'
user.loadProvinces = async () => {}
const history = useHistoryStore(pinia)
history.fetchRecords = history.fetchStats = history.fetchTrend = async () => {}
const params = new URLSearchParams(location.search)
const page = ref(params.get('page') || 'home')
const routes = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: { render: () => null } }] })
await routes.push('/result/visual-demo-exam')
const components = { home: Home, prepare: Prepare, room: Room, result: Result }
const app = createApp({ setup: () => () => h('div', [
  !params.has('compact') && h('nav', { style: 'padding:12px 24px;background:#fff;border-bottom:1px solid #dbe3ee;display:flex;gap:16px;flex-wrap:wrap;align-items:center' }, [
    h('strong', '本机验收 · 演示数据，不访问真实账号'),
    ...Object.entries({ home: '首页', prepare: '准备', room: '考场', result: '待点评结果' }).map(([key, label]) => h('button', { style: 'padding:10px 16px;border:1px solid #dbe3ee;border-radius:8px;background:#edf3ff;color:#203047;cursor:pointer', onClick: () => { page.value = key } }, label))
  ]),
  h(components[page.value], { key: page.value })
]) })
app.use(pinia).use(routes).use(Antd).mount('#app')
