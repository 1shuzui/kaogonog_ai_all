export const JIANGSU_JOB_CATEGORIES = [
  { key: 'a', code: 'A', title: '综合管理岗', shortTitle: '综合管理岗', subtitle: '省属 / 地市事业单位真题', scope: '综合管理', rank: 1, hot: '报考热度最高' },
  { key: 'b', code: 'B', title: '社会科学专技岗', shortTitle: '社会科学专技岗', subtitle: '法律 / 经济 / 会计', scope: '社科专技', rank: 2, hot: '专业岗高频' },
  { key: 'c', code: 'C', title: '自然科学专技岗', shortTitle: '自然科学专技岗', subtitle: '计算机 / 工程 / 农技', scope: '自然科学', rank: 3, hot: '理工农技' },
  { key: 'e', code: 'E', title: '医疗卫生岗', shortTitle: '医疗卫生岗', subtitle: '', scope: '医疗卫生', rank: 4, hot: '医疗岗专项' },
  { key: 'worker', code: '工勤', title: '工勤技能岗', shortTitle: '工勤', subtitle: '', scope: '工勤技能', rank: 5, hot: '技能岗' }
]

export const JIANGSU_TARGETED_POSITIONS = JIANGSU_JOB_CATEGORIES.map((item) => ({
  code: `jiangsu_${item.key}`,
  name: item.title,
  desc: item.subtitle,
  categoryKey: item.key,
  rank: item.rank
}))

export const JIANGSU_CITY_FILTERS = [
  { key: 'all', name: '全部' },
  { key: 'provincial', name: '省属' },
  { key: 'nanjing', name: '南京' },
  { key: 'suzhou', name: '苏州' },
  { key: 'wuxi', name: '无锡' },
  { key: 'changzhou', name: '常州' },
  { key: 'nantong', name: '南通' },
  { key: 'xuzhou', name: '徐州' },
  { key: 'yancheng', name: '盐城' },
  { key: 'yangzhou', name: '扬州' },
  { key: 'zhenjiang', name: '镇江' },
  { key: 'taizhou', name: '泰州' },
  { key: 'huaian', name: '淮安' },
  { key: 'lianyungang', name: '连云港' },
  { key: 'suqian', name: '宿迁' }
]

export const JIANGSU_YEAR_FILTERS = ['2025', '2024', '2023', '2022', '2021', '2020', '2019', '2018', '2017']

export const JIANGSU_QUESTION_TYPES = [
  { key: 'analysis', name: '综合分析' },
  { key: 'practical', name: '组织管理' },
  { key: 'emergency', name: '应急应变' },
  { key: 'logic', name: '人际沟通' },
  { key: 'expression', name: '情景模拟' },
  { key: 'legal', name: '岗位认知' }
]

const CITY_POOL = JIANGSU_CITY_FILTERS.filter((item) => item.key !== 'all')
const TYPE_STEMS = {
  analysis: '请结合事业单位服务群众职责，谈谈你对基层治理精细化的理解。',
  practical: '单位准备开展便民服务专项活动，领导交由你负责，你会如何组织。',
  emergency: '窗口大厅突发设备故障，群众等待时间较长，你会如何处置。',
  logic: '同事对你负责的材料反复提出修改意见，你会如何沟通处理。',
  expression: '窗口群众因排队时间过长情绪激动，请你现场安抚并解决问题。',
  legal: '请谈谈你对事业单位工作人员岗位职责和服务意识的理解。'
}

export function getJiangsuJobCategory(key = 'a') {
  return JIANGSU_JOB_CATEGORIES.find((item) => item.key === key) || JIANGSU_JOB_CATEGORIES[0]
}

export function getJiangsuTargetedPosition(code = '') {
  return JIANGSU_TARGETED_POSITIONS.find((item) => item.code === code) || null
}

export function buildJiangsuQuestionItems(categoryKey = 'a') {
  const category = getJiangsuJobCategory(categoryKey)
  const items = []

  JIANGSU_YEAR_FILTERS.forEach((year, yearIndex) => {
    JIANGSU_QUESTION_TYPES.forEach((type, typeIndex) => {
      const city = CITY_POOL[(yearIndex * 3 + typeIndex) % CITY_POOL.length]
      const month = typeIndex < 2 ? '05' : '06'
      const day = String(21 + typeIndex).padStart(2, '0')
      items.push({
        id: `${category.key}-${year}-${city.key}-${type.key}`,
        categoryKey: category.key,
        cityKey: city.key,
        cityName: city.name,
        year,
        date: `${year}-${month}-${day}`,
        typeKey: type.key,
        typeName: type.name,
        title: `${year}-${month}-${day} 江苏${city.name} · ${category.shortTitle} · ${type.name}题`,
        stem: `${TYPE_STEMS[type.key]}（${category.title}方向）`
      })
    })
  })

  return items.sort((a, b) => b.date.localeCompare(a.date))
}

export function filterJiangsuQuestionItems(items, filters = {}) {
  return items.filter((item) => {
    if (filters.city && filters.city !== 'all' && item.cityKey !== filters.city) return false
    if (filters.year && item.year !== filters.year) return false
    if (filters.type && item.typeKey !== filters.type) return false
    return true
  })
}
