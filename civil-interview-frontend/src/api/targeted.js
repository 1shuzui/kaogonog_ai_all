import { http, USE_MOCK } from './index'

export async function getPositions() {
  if (USE_MOCK) {
    return [
      { code: 'tax', name: '税务系统' },
      { code: 'customs', name: '海关系统' },
      { code: 'police', name: '公安系统' },
      { code: 'court', name: '法院系统' },
      { code: 'procurate', name: '检察系统' },
      { code: 'market', name: '市场监管' },
      { code: 'general', name: '综合管理' },
      { code: 'township', name: '乡镇基层' },
      { code: 'finance', name: '银保监会' },
      { code: 'diplomacy', name: '外交系统' }
    ]
  }
  return http.get('/positions')
}

export async function getFocusAnalysis(data) {
  if (USE_MOCK) {
    return {
      coreFocus: [
        { name: '税法应用能力', weight: 30, desc: '考察考生对税收法律法规的理解和实际应用能力' },
        { name: '纳税服务意识', weight: 25, desc: '考察为纳税人提供优质服务的意识和方法' },
        { name: '廉政风险防范', weight: 20, desc: '考察在执法过程中的廉洁自律意识' }
      ],
      highFreqTypes: [
        { type: '综合分析', frequency: '高', example: '谈谈你对"放管服"改革在税务领域落地的看法' },
        { type: '应急应变', frequency: '高', example: '纳税人对税务处理决定不满并情绪激动，你如何处理？' }
      ],
      hotTopics: ['数电发票推广', '税费优惠政策落实', '税收营商环境优化'],
      strategy: ['熟悉最新税收政策和法规', '关注本省经济发展重点', '练习服务类和执法类场景题']
    }
  }
  return http.post('/targeted/focus', data)
}

export async function generateQuestions(data) {
  if (USE_MOCK) {
    return [
      {
        id: `gen_${Date.now()}_1`,
        stem: '某地税务局推行"非接触式"办税服务，但部分老年纳税人反映操作困难，你作为窗口工作人员，如何解决这一问题？',
        dimension: 'practical',
        province: data.province,
        prepTime: 90,
        answerTime: 180,
        scoringPoints: [
          { content: '准确识别老年群体数字鸿沟问题', score: 6 },
          { content: '提出兼顾效率与公平的具体措施', score: 8 },
          { content: '体现为民服务意识', score: 6 }
        ],
        keywords: {
          scoring: ['适老化改造', '专人辅导', '保留传统渠道', '服务温度'],
          deducting: ['一刀切', '忽视老年人需求'],
          bonus: ['志愿者服务', '预约上门', '大字版界面']
        }
      }
    ]
  }
  return http.post('/questions/generate', data)
}
