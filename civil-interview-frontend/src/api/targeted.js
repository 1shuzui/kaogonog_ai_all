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
      { code: 'diplomacy', name: '外交系统' },
      { code: 'prison', name: '监狱系统' }
    ]
  }
  const result = await http.get('/positions')
  return (Array.isArray(result) ? result : []).map((item) => ({
    code: item.code || item.id || '',
    name: item.name || ''
  })).filter((item) => item.code && item.name)
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

export async function generateQuestions(data, sourceMode = 'local') {
  const payload = {
    ...data,
    sourceMode
  }
  const result = await http.post('/targeted/generate', payload)
  return {
    questions: Array.isArray(result) ? result : (result?.questions || []),
    province: result?.province || data?.province || '',
    position: result?.position || data?.position || '',
    sourceMode: result?.sourceMode || sourceMode
  }
}
