import { mockDelay } from './index'
import { DIMENSIONS } from '@/utils/constants'

function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min
}

function generateDimensionScores() {
  return DIMENSIONS.map(d => ({
    name: d.name,
    key: d.key,
    score: randomInt(Math.floor(d.maxScore * 0.5), d.maxScore),
    maxScore: d.maxScore,
    lostReasons: generateLostReasons(d.key)
  }))
}

function generateLostReasons(dimensionKey) {
  const reasons = {
    legal: ['未提及具体法律条款', '法治思维论述不够深入', '缺少法律依据的引用'],
    practical: ['方案缺乏可操作性', '未考虑资源约束', '实施步骤不够具体'],
    logic: ['论述结构不够清晰', '论点之间缺乏逻辑衔接', '总分总结构不完整'],
    expression: ['语言不够简洁', '用词不够准确规范', '口头禅较多'],
    analysis: ['分析角度单一', '未能多维度展开', '缺少辩证分析'],
    emergency: ['应对措施缺乏针对性', '优先级判断不当', '缺少后续跟进措施']
  }
  const pool = reasons[dimensionKey] || ['无特定原因']
  return pool.slice(0, randomInt(1, 2))
}

const sampleTranscript = `我认为"街长制"管理模式是基层治理创新的一种有益探索。首先，这种模式有利于实现精细化管理，将责任落实到具体的人，有助于提高基层治理效能。通过明确街长的职责范围，可以实现网格化管理，做到问题发现在一线、处理在一线。

但同时我们也要看到，推行"街长制"需要注意避免形式主义，不能让基层干部疲于应付，增加不必要的负担。要做好顶层设计，明确街长的权责边界，避免出现推诿扯皮的情况。

因此，我建议：第一，完善配套制度，明确考核标准；第二，加强培训，提升街长的综合治理能力；第三，建立群众参与机制，实现共建共治共享的社会治理格局。`

export async function getMockTranscript() {
  await mockDelay(2000)
  return {
    transcript: sampleTranscript,
    duration: 165
  }
}

export async function getMockScoringResult(questionId) {
  await mockDelay(3000)
  const dimensions = generateDimensionScores()
  const totalScore = dimensions.reduce((sum, d) => sum + d.score, 0)
  const maxScore = dimensions.reduce((sum, d) => sum + d.maxScore, 0)

  return {
    totalScore,
    maxScore,
    grade: totalScore >= 90 ? 'A' : totalScore >= 75 ? 'B' : totalScore >= 60 ? 'C' : 'D',
    dimensions,
    matchedKeywords: {
      scoring: [
        { word: '基层治理', inTranscript: true, score: 3 },
        { word: '精细化管理', inTranscript: true, score: 3 },
        { word: '网格化', inTranscript: true, score: 2 },
        { word: '责任到人', inTranscript: true, score: 2 },
        { word: '综合治理', inTranscript: true, score: 2 }
      ],
      deducting: [
        { word: '形式主义', inTranscript: true, penalty: -2 },
        { word: '一刀切', inTranscript: false, penalty: 0 }
      ],
      bonus: [
        { word: '共建共治共享', inTranscript: true, bonus: 3 },
        { word: '社会治理现代化', inTranscript: false, bonus: 0 }
      ]
    },
    aiComment: '整体回答思路清晰，能够辩证看待"街长制"的利弊。在基层治理创新方面有较好的理解，提出的建议具有一定的可操作性。建议加强法律条文的引用，在实务落地层面可以更加具体。语言表达较为流畅，逻辑结构完整。',
    highlightedTranscript: sampleTranscript
  }
}

export async function getMockExamStart(questionIds) {
  await mockDelay(500)
  return {
    examId: `exam_${Date.now()}`,
    questionIds,
    startTime: new Date().toISOString()
  }
}

export async function getMockUploadResult() {
  await mockDelay(1000)
  return { success: true, fileUrl: '/mock/recording.webm' }
}
