import { mockDelay } from './index'

const mockQuestions = [
  {
    id: 'q001',
    stem: '某市推行"街长制"管理模式，由街道干部担任街长，负责辖区内市容环境、安全秩序等综合治理工作。有人认为这是基层治理创新，也有人认为增加了基层负担。请谈谈你的看法。',
    dimension: 'analysis',
    province: 'national',
    prepTime: 90,
    answerTime: 180,
    scoringPoints: [
      { content: '辩证分析"街长制"的积极意义', score: 5 },
      { content: '指出可能存在的问题与风险', score: 5 },
      { content: '提出完善建议或解决对策', score: 5 },
      { content: '结合基层治理实际展开论述', score: 5 }
    ],
    synonyms: ['网格化管理', '基层治理创新', '街道综合治理'],
    keywords: {
      scoring: ['基层治理', '网格化', '精细化管理', '责任到人', '综合治理'],
      deducting: ['一刀切', '形式主义', '增加负担'],
      bonus: ['共建共治共享', '社会治理现代化', '新时代枫桥经验']
    }
  },
  {
    id: 'q002',
    stem: '你是某局新入职的公务员，领导让你负责组织一次面向辖区企业的法律法规宣讲活动。你将如何开展这项工作？',
    dimension: 'practical',
    province: 'national',
    prepTime: 90,
    answerTime: 180,
    scoringPoints: [
      { content: '明确活动目标和对象', score: 4 },
      { content: '制定详细工作方案', score: 5 },
      { content: '做好组织协调和资源整合', score: 4 },
      { content: '活动实施的关键环节', score: 4 },
      { content: '总结评估和后续跟进', score: 3 }
    ],
    synonyms: ['法治宣传', '普法教育', '法律宣讲'],
    keywords: {
      scoring: ['调研需求', '制定方案', '邀请专家', '宣传发动', '总结评估'],
      deducting: ['脱离实际', '走过场'],
      bonus: ['以案释法', '线上线下结合', '长效机制']
    }
  },
  {
    id: 'q003',
    stem: '在一次联合执法行动中，你发现同事存在执法不规范的行为，可能引发群众投诉。你会怎么做？',
    dimension: 'emergency',
    province: 'national',
    prepTime: 90,
    answerTime: 180,
    scoringPoints: [
      { content: '保持冷静,快速判断情况严重性', score: 4 },
      { content: '当场适当提醒或制止不规范行为', score: 5 },
      { content: '做好群众安抚和解释工作', score: 4 },
      { content: '事后向领导如实汇报', score: 4 },
      { content: '推动建立执法规范的长效机制', score: 3 }
    ],
    synonyms: ['执法规范', '联合执法', '同事关系'],
    keywords: {
      scoring: ['依法执法', '规范执法', '及时制止', '安抚群众', '汇报领导'],
      deducting: ['袒护同事', '隐瞒不报', '当众批评'],
      bonus: ['执法全过程记录', '建章立制', '举一反三']
    }
  },
  {
    id: 'q004',
    stem: '近年来，一些地方政府在推行政务公开过程中，出现了"公开不及时、公开不完整、公开走形式"等问题。对此你怎么看？',
    dimension: 'legal',
    province: 'beijing',
    prepTime: 90,
    answerTime: 180,
    scoringPoints: [
      { content: '阐述政务公开的重要意义', score: 5 },
      { content: '分析问题产生的原因', score: 5 },
      { content: '提出有针对性的解决措施', score: 5 },
      { content: '体现法治思维和依法行政理念', score: 5 }
    ],
    synonyms: ['信息公开', '阳光政务', '透明政府'],
    keywords: {
      scoring: ['知情权', '监督权', '政府信息公开条例', '制度建设', '问责机制'],
      deducting: ['空谈', '脱离法律依据'],
      bonus: ['数字政府', '主动公开', '回应关切', '政府公信力']
    }
  },
  {
    id: 'q005',
    stem: '你所在单位要推进"最多跑一次"改革，但部分老同志认为传统流程更稳妥，对改革有抵触情绪。作为改革推进小组成员，你怎么办？',
    dimension: 'practical',
    province: 'zhejiang',
    prepTime: 90,
    answerTime: 180,
    scoringPoints: [
      { content: '理解老同志的顾虑,换位思考', score: 4 },
      { content: '做好沟通和思想引导工作', score: 5 },
      { content: '制定科学的改革推进方案', score: 4 },
      { content: '提供培训和支持帮助适应', score: 4 },
      { content: '建立激励和反馈机制', score: 3 }
    ],
    synonyms: ['放管服改革', '简政放权', '优化营商环境'],
    keywords: {
      scoring: ['换位思考', '耐心沟通', '循序渐进', '培训帮扶', '示范引领'],
      deducting: ['强制推行', '忽视老同志感受', '急于求成'],
      bonus: ['数字化转型', '群众满意度', '营商环境优化']
    }
  },
  {
    id: 'q006',
    stem: '请你就"基层干部既要\'身入\'基层，更要\'心入\'基层"这句话，谈谈你的理解。',
    dimension: 'analysis',
    province: 'guangdong',
    prepTime: 90,
    answerTime: 180,
    scoringPoints: [
      { content: '准确理解"身入"和"心入"的含义', score: 5 },
      { content: '分析当前基层工作中存在的问题', score: 5 },
      { content: '阐述如何做到"心入"基层', score: 5 },
      { content: '结合自身谈认识或做法', score: 5 }
    ],
    synonyms: ['深入基层', '群众路线', '为民服务'],
    keywords: {
      scoring: ['群众路线', '为民服务', '调查研究', '真抓实干', '民生'],
      deducting: ['假大空', '脱离实际'],
      bonus: ['初心使命', '人民至上', '脚下有泥心中有光']
    }
  },
  {
    id: 'q007',
    stem: '某地在扶贫工作中引入"积分制"管理，贫困户通过参加技能培训、主动就业、环境整治等获得积分，兑换生活物资。你认为这种做法是否合理？',
    dimension: 'legal',
    province: 'sichuan',
    prepTime: 90,
    answerTime: 180,
    scoringPoints: [
      { content: '肯定积分制的积极作用', score: 5 },
      { content: '分析可能存在的争议和问题', score: 5 },
      { content: '提出完善建议', score: 5 },
      { content: '体现公平公正的法治理念', score: 5 }
    ],
    synonyms: ['精准扶贫', '扶贫扶志', '激励机制'],
    keywords: {
      scoring: ['扶贫扶志', '内生动力', '公平公正', '制度设计', '群众参与'],
      deducting: ['歧视贫困户', '一刀切'],
      bonus: ['乡村振兴', '社会治理创新', '志智双扶']
    }
  },
  {
    id: 'q008',
    stem: '你负责一个重点项目的推进工作，但在执行过程中，你发现上级制定的某项政策在本地执行存在明显的水土不服。你会怎么处理？',
    dimension: 'emergency',
    province: 'jiangsu',
    prepTime: 90,
    answerTime: 180,
    scoringPoints: [
      { content: '深入调研分析政策执行的具体困难', score: 5 },
      { content: '在坚决执行的前提下灵活应对', score: 4 },
      { content: '及时向上级反映情况并提出建议', score: 5 },
      { content: '做好与相关部门和群众的沟通协调', score: 3 },
      { content: '体现政治意识和大局观', score: 3 }
    ],
    synonyms: ['政策执行', '因地制宜', '请示汇报'],
    keywords: {
      scoring: ['调查研究', '实事求是', '请示汇报', '灵活执行', '政治意识'],
      deducting: ['擅自变通', '消极执行', '阳奉阴违'],
      bonus: ['创造性落实', '试点先行', '总结推广']
    }
  }
]

export async function getMockQuestions(params = {}) {
  await mockDelay(600)
  let filtered = [...mockQuestions]
  if (params.province && params.province !== 'all') {
    filtered = filtered.filter(q => q.province === params.province)
  }
  if (params.dimension) {
    filtered = filtered.filter(q => q.dimension === params.dimension)
  }
  if (params.keyword) {
    filtered = filtered.filter(q => q.stem.includes(params.keyword))
  }
  const page = params.page || 1
  const pageSize = params.pageSize || 10
  const start = (page - 1) * pageSize
  return {
    list: filtered.slice(start, start + pageSize),
    total: filtered.length,
    page,
    pageSize
  }
}

export async function getMockQuestionById(id) {
  await mockDelay(300)
  return mockQuestions.find(q => q.id === id) || null
}

export async function getMockRandomQuestions(params = {}) {
  await mockDelay(400)
  let pool = [...mockQuestions]
  if (params.province && params.province !== 'all') {
    pool = pool.filter(q => q.province === params.province || q.province === 'national')
  }
  const count = Math.min(params.count || 5, pool.length)
  const shuffled = pool.sort(() => Math.random() - 0.5)
  return shuffled.slice(0, count)
}

export { mockQuestions }
