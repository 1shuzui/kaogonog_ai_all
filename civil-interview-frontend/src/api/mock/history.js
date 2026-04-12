import { mockDelay } from './index'
import { DIMENSIONS } from '@/utils/constants'

function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min
}

const mockRecords = Array.from({ length: 15 }, (_, i) => {
  const date = new Date()
  date.setDate(date.getDate() - (14 - i))
  const baseScore = 55 + i * 2 + randomInt(-3, 3)
  const totalScore = Math.min(Math.max(baseScore, 45), 98)

  return {
    examId: `exam_${1000 + i}`,
    date: date.toISOString(),
    questionCount: randomInt(3, 5),
    totalScore,
    maxScore: 100,
    grade: totalScore >= 90 ? 'A' : totalScore >= 75 ? 'B' : totalScore >= 60 ? 'C' : 'D',
    province: ['national', 'beijing', 'guangdong', 'zhejiang'][i % 4],
    dimensions: DIMENSIONS.map(d => ({
      name: d.name,
      score: randomInt(Math.floor(d.maxScore * 0.4), d.maxScore),
      maxScore: d.maxScore
    })),
    questionSummary: [
      '某市推行"街长制"管理模式...',
      '组织一次法律法规宣讲活动...',
      '发现同事执法不规范的行为...',
      '政务公开过程中的问题...',
      '推进"最多跑一次"改革...'
    ][i % 5]
  }
})

export async function getMockHistory(params = {}) {
  await mockDelay(600)
  const page = params.page || 1
  const pageSize = params.pageSize || 10
  let filtered = [...mockRecords].reverse()
  if (params.province) {
    filtered = filtered.filter(r => r.province === params.province)
  }
  const start = (page - 1) * pageSize
  return {
    list: filtered.slice(start, start + pageSize),
    total: filtered.length,
    page,
    pageSize
  }
}

export async function getMockHistoryDetail(examId) {
  await mockDelay(400)
  return mockRecords.find(r => r.examId === examId) || null
}

export async function getMockTrend() {
  await mockDelay(500)
  return mockRecords.map(r => ({
    date: r.date.split('T')[0],
    score: r.totalScore
  }))
}

export async function getMockStats() {
  await mockDelay(400)
  const scores = mockRecords.map(r => r.totalScore)
  const avgScore = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length)
  const bestScore = Math.max(...scores)
  const dimAvgs = DIMENSIONS.map(d => {
    const avg = mockRecords.reduce((sum, r) => {
      const dim = r.dimensions.find(dd => dd.name === d.name)
      return sum + (dim ? dim.score : 0)
    }, 0) / mockRecords.length
    return { name: d.name, avg: Math.round(avg * 10) / 10, maxScore: d.maxScore }
  })
  const weakest = dimAvgs.reduce((min, d) =>
    (d.avg / d.maxScore) < (min.avg / min.maxScore) ? d : min
  )

  return {
    totalExams: mockRecords.length,
    avgScore,
    bestScore,
    weakestDimension: weakest.name,
    dimensionAverages: dimAvgs
  }
}
