import { http, USE_MOCK } from './index'

export async function generateTrainingQuestions(data) {
  if (USE_MOCK) {
    return [
      {
        id: `train_${Date.now()}_1`,
        stem: '请谈谈你对基层治理法治化的理解，以及如何推进？',
        dimension: data.dimension,
        province: 'national',
        prepTime: 90,
        answerTime: 180,
        scoringPoints: [
          { content: '对法治化有清晰理解', score: 7 },
          { content: '结合基层实际提出措施', score: 8 },
          { content: '逻辑清晰、表达规范', score: 5 }
        ],
        keywords: {
          scoring: ['依法行政', '法治意识', '基层治理'],
          deducting: ['内容空泛'],
          bonus: ['典型案例', '制度创新']
        }
      }
    ]
  }
  const response = await http.post('/training/generate', data)
  return Array.isArray(response?.questions) ? response.questions : []
}
