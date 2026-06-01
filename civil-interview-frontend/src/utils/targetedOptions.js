const TARGET_FIELDS = [
  'province',
  'position',
  'examCategory',
  'examSubcategory',
  'subcategory',
  'subcategory2',
  'year',
  'targetCode',
  'targetName',
  'interviewFormat',
  'timingMode',
  'questionCount',
  'prepTime',
  'answerTime',
  'questionTypeScope',
  'notes'
]

const TARGETED_PROVINCES = [
  ['beijing', '北京'],
  ['shanghai', '上海'],
  ['guangdong', '广东'],
  ['jiangsu', '江苏'],
  ['zhejiang', '浙江'],
  ['shandong', '山东'],
  ['sichuan', '四川'],
  ['hubei', '湖北'],
  ['hunan', '湖南'],
  ['henan', '河南'],
  ['hebei', '河北'],
  ['fujian', '福建'],
  ['anhui', '安徽'],
  ['liaoning', '辽宁'],
  ['shanxi', '陕西']
]

const JIANGSU_SIDW_CITY_DIRECTIONS = [
  ['nanjing', '南京'],
  ['wuxi', '无锡'],
  ['changzhou', '常州'],
  ['tongzhou', '通州'],
  ['yangzhou', '扬州'],
  ['zhenjiang', '镇江'],
  ['taizhou', '泰州'],
  ['huaian', '淮安'],
  ['xuzhou', '徐州'],
  ['suqian', '宿迁'],
  ['lianyungang', '连云港']
]

const BANK_SYSTEM_DIRECTIONS = [
  ['state_owned', '国有银行'],
  ['joint_stock', '股份制银行'],
  ['city_commercial', '城市商业银行'],
  ['rural_commercial', '农村商业银行']
]

const MEDICAL_JOB_DIRECTIONS = [
  ['doctor', '医师岗'],
  ['nurse', '护理岗'],
  ['technician', '医技岗'],
  ['pharmacist', '药师岗'],
  ['admin', '行政岗']
]

const ANHUI_SIDW_CITY_DIRECTIONS = [
  '合肥', '芜湖', '蚌埠', '淮南', '马鞍山', '淮北', '铜陵', '安庆',
  '黄山', '滁州', '阜阳', '宿州', '六安', '亳州', '池州', '宣城'
]

const SHANDONG_SIDW_STANDARD_CITIES = [
  '淄博', '潍坊', '济宁', '泰安', '德州', '聊城', '滨州', '菏泽', '东营', '枣庄'
]

const CLERK_SOURCE_PROVINCES = [
  ['hubei', '湖北'],
  ['hunan', '湖南'],
  ['anhui', '安徽'],
  ['shandong', '山东'],
  ['zhejiang', '浙江']
]

const CLERK_STRUCTURED_PROVINCES = [
  ['beijing', '北京'],
  ['shanghai', '上海'],
  ['guangdong', '广东'],
  ['jiangsu', '江苏'],
  ['zhejiang', '浙江'],
  ['shandong', '山东'],
  ['sichuan', '四川'],
  ['hubei', '湖北'],
  ['hunan', '湖南'],
  ['anhui', '安徽'],
  ['fujian', '福建'],
  ['jiangxi', '江西'],
  ['henan', '河南'],
  ['hebei', '河北'],
  ['liaoning', '辽宁'],
  ['heilongjiang', '黑龙江'],
  ['jilin', '吉林'],
  ['shanxi', '陕西'],
  ['guizhou', '贵州'],
  ['yunnan', '云南'],
  ['guangxi', '广西'],
  ['hainan', '海南'],
  ['neimenggu', '内蒙古'],
  ['xinjiang', '新疆'],
  ['ningxia', '宁夏'],
  ['gansu', '甘肃'],
  ['qinghai', '青海']
]

function provinceName(shortName) {
  return ['北京', '上海'].includes(shortName) ? `${shortName}市` : `${shortName}省`
}

function reservedAdminHint(label) {
  return `${label}方向已保留；如需开放练习，请在题库管理中补充并确认真实题目。`
}

export const DEFAULT_TARGETED_POSITION_TREE = [
  {
    id: 'institution',
    name: '事业单位考试',
    desc: '按真实事业单位套题、地区和岗位方向统计。',
    children: [
      {
        id: 'institution_jiangsu',
        name: '江苏省',
        province: 'jiangsu',
        examCategory: '事业单位考试',
        examSubcategory: '江苏省',
        directions: [
          { id: 'js_sydw_all', name: '江苏事业单位真题', province: 'jiangsu', position: '', examCategory: '事业单位考试', examSubcategory: '江苏省' },
          { id: 'js_sydw_general', name: '综合管理岗', province: 'jiangsu', position: 'general', examCategory: '事业单位考试', examSubcategory: '江苏省', positionType: '综合管理岗' },
          { id: 'js_sydw_grassroots', name: '基层方向', province: 'jiangsu', position: 'township', examCategory: '事业单位考试', examSubcategory: '江苏省', positionType: '基层岗' },
          { id: 'js_sydw_township', name: '乡镇方向', province: 'jiangsu', position: 'township', examCategory: '事业单位考试', examSubcategory: '江苏省', positionType: '乡镇岗' },
          { id: 'js_sydw_medical', name: '医疗卫生相关岗位', province: 'jiangsu', position: 'medical', examCategory: '事业单位考试', examSubcategory: '江苏省' },
          ...JIANGSU_SIDW_CITY_DIRECTIONS.map(([code, city]) => ({
            id: `js_sydw_city_${code}`,
            name: city,
            province: 'jiangsu',
            position: 'general',
            examCategory: '事业单位考试',
            examSubcategory: '江苏省',
            subcategory: city,
            positionType: `${city}事业单位`,
            interviewFormat: '8+12',
            questionCount: '3',
            prepTime: '480',
            answerTime: '720',
            timingMode: '8分钟读题+12分钟答题'
          }))
        ]
      },
      {
        id: 'institution_anhui',
        name: '安徽省',
        province: 'anhui',
        examCategory: '事业单位考试',
        examSubcategory: '安徽省',
        directions: [
          { id: 'ah_sydw_provincial', name: '省直', province: 'anhui', position: 'general', examCategory: '事业单位考试', examSubcategory: '安徽省', positionType: '省直事业单位', interviewFormat: '15-20分钟包干', questionCount: '3-4', timingMode: '15-20分钟包干', questionTypeScope: '综合分析/组织/应急/人际/岗位匹配' },
          ...ANHUI_SIDW_CITY_DIRECTIONS.map((city, index) => ({
            id: `ah_sydw_city_${index + 1}`,
            name: city,
            province: 'anhui',
            position: 'general',
            examCategory: '事业单位考试',
            examSubcategory: '安徽省',
            subcategory: city,
            positionType: `${city}事业单位`,
            interviewFormat: '15分钟包干',
            questionCount: '3',
            timingMode: '15分钟包干'
          }))
        ]
      },
      {
        id: 'institution_shandong',
        name: '山东省',
        province: 'shandong',
        examCategory: '事业单位考试',
        examSubcategory: '山东省',
        directions: [
          { id: 'sd_sydw_provincial', name: '省属', province: 'shandong', position: 'general', examCategory: '事业单位考试', examSubcategory: '山东省', positionType: '省属事业单位', interviewFormat: '15分钟包干', questionCount: '3', timingMode: '15分钟包干' },
          { id: 'sd_sydw_jinan', name: '济南', province: 'shandong', position: 'general', examCategory: '事业单位考试', examSubcategory: '山东省', subcategory: '济南', interviewFormat: '7+7', questionCount: '2-3', prepTime: '420', answerTime: '420', timingMode: '7分钟读题+7分钟答题' },
          { id: 'sd_sydw_qingdao', name: '青岛', province: 'shandong', position: 'general', examCategory: '事业单位考试', examSubcategory: '山东省', subcategory: '青岛', interviewFormat: '5+5/15分钟包干', questionCount: '2-3', timingMode: '5+5或15分钟包干' },
          { id: 'sd_sydw_yantai', name: '烟台', province: 'shandong', position: 'general', examCategory: '事业单位考试', examSubcategory: '山东省', subcategory: '烟台', interviewFormat: '6+6', questionCount: '2', prepTime: '360', answerTime: '360', timingMode: '6分钟读题+6分钟答题' },
          { id: 'sd_sydw_weihai', name: '威海', province: 'shandong', position: 'general', examCategory: '事业单位考试', examSubcategory: '山东省', subcategory: '威海', interviewFormat: '6+6', questionCount: '2', prepTime: '360', answerTime: '360', timingMode: '6分钟读题+6分钟答题' },
          { id: 'sd_sydw_linyi', name: '临沂', province: 'shandong', position: 'general', examCategory: '事业单位考试', examSubcategory: '山东省', subcategory: '临沂', interviewFormat: '10分钟包干无纸笔', questionCount: '2', timingMode: '10分钟包干无纸笔' },
          ...SHANDONG_SIDW_STANDARD_CITIES.map((city, index) => ({
            id: `sd_sydw_city_${index + 1}`,
            name: city,
            province: 'shandong',
            position: 'general',
            examCategory: '事业单位考试',
            examSubcategory: '山东省',
            subcategory: city,
            positionType: `${city}事业单位`,
            interviewFormat: '15分钟包干',
            questionCount: '3',
            timingMode: '15分钟包干'
          }))
        ]
      }
    ]
  },
  {
    id: 'provincial_civil',
    name: '省级公务员考试',
    desc: '按省级公务员考试体系、地区和岗位方向统计。',
    children: [
      {
        id: 'provincial_anhui',
        name: '安徽省',
        province: 'anhui',
        examCategory: '省级公务员考试',
        examSubcategory: '安徽省',
        positionType: '综合管理类',
        questionCount: '3',
        interviewFormat: '综合管理类；15分钟包干',
        timingMode: '15分钟包干',
        directions: []
      },
      {
        id: 'provincial_guangdong',
        name: '广东省',
        province: 'guangdong',
        examCategory: '省级公务员考试',
        examSubcategory: '广东省',
        positionType: '综合类、执法类',
        questionCount: '3',
        interviewFormat: '综合类、执法类一材三题；10+10模式',
        prepTime: '600',
        answerTime: '600',
        timingMode: '10分钟读题+10分钟答题',
        directions: []
      },
      {
        id: 'provincial_shandong',
        name: '山东省',
        province: 'shandong',
        examCategory: '省级公务员考试',
        examSubcategory: '山东省',
        questionCount: '3',
        interviewFormat: '统一考试；省直15分钟包干，济南7+7，烟台6+6',
        timingMode: '按地区套题规则切换',
        directions: []
      },
      {
        id: 'provincial_henan',
        name: '河南省',
        province: 'henan',
        position: 'township',
        examCategory: '省级公务员考试',
        examSubcategory: '河南省',
        positionType: '县乡、省直分类',
        questionCount: '4',
        interviewFormat: '县乡、省直分类；20分钟包干',
        timingMode: '20分钟包干',
        directions: []
      },
      {
        id: 'provincial_hubei',
        name: '湖北省',
        province: 'hubei',
        position: 'township',
        examCategory: '省级公务员考试',
        examSubcategory: '湖北省',
        positionType: '县以上、乡镇、公安三类',
        questionCount: '3',
        interviewFormat: '县以上、乡镇、公安三类；县乡15分钟，省直18分钟',
        timingMode: '县乡15分钟包干或省直18分钟包干',
        directions: []
      },
      {
        id: 'provincial_hebei',
        name: '河北省',
        province: 'hebei',
        examCategory: '省级公务员考试',
        examSubcategory: '河北省',
        questionCount: '3',
        interviewFormat: '统一考试，含演讲、漫画特色；10分钟包干',
        timingMode: '10分钟包干',
        questionTypeScope: '结构化、演讲、漫画',
        directions: []
      },
      {
        id: 'provincial_hunan',
        name: '湖南省',
        province: 'hunan',
        examCategory: '省级公务员考试',
        examSubcategory: '湖南省',
        positionType: '通用岗、乡镇岗、监狱系统、税务系统补录',
        interviewFormat: '按湖南省考真实套题规则组织',
        directions: []
      },
      {
        id: 'provincial_jiangsu',
        name: '江苏省',
        province: 'jiangsu',
        examCategory: '省级公务员考试',
        examSubcategory: '江苏省',
        positionType: 'A、B、C三类分别命题',
        questionCount: '4',
        interviewFormat: 'A、B、C三类分别命题；10+15模式或20分钟包干',
        prepTime: '600',
        answerTime: '900',
        timingMode: '10分钟读题+15分钟答题或20分钟包干',
        directions: []
      }
    ]
  },
  {
    id: 'national_civil',
    name: '国家公务员考试',
    desc: '按国考系统和直属机构方向统计。',
    children: [
      {
        id: 'national_all',
        name: '中央/国家直属系统',
        province: 'national',
        examCategory: '国家公务员考试',
        examSubcategory: '中央/国家直属系统',
        adminHint: reservedAdminHint('国考'),
        directions: [
          { id: 'gk_all', name: '国考通用', province: 'national', position: '', examCategory: '国家公务员考试', examSubcategory: '中央/国家直属系统' }
        ]
      }
    ]
  },
  {
    id: 'medical_portal',
    name: '医疗卫生面试',
    desc: '按已确认题源展示，题目真实主分类仍保留原考试体系。',
    children: [
      {
        id: 'medical_sichuan_partial',
        name: '四川省 / 部分地区',
        province: 'sichuan',
        // portalTag_removed: '医疗卫生面试',
        directions: MEDICAL_JOB_DIRECTIONS.map(([code, name]) => ({
          id: `medical_sc_partial_${code}`,
          name,
          province: 'sichuan',
          position: 'medical',
          // portalTag_removed: '医疗卫生面试',
          positionType: name,
          interviewFormat: '医疗背景结构化'
        }))
      },
      {
        id: 'medical_e_class',
        name: 'E类联考省份',
        province: 'all',
        // portalTag_removed: '医疗卫生面试',
        directions: MEDICAL_JOB_DIRECTIONS.map(([code, name]) => ({
          id: `medical_e_class_${code}`,
          name,
          province: 'all',
          position: 'medical',
          // portalTag_removed: '医疗卫生面试',
          positionType: name,
          interviewFormat: 'E类联考分岗考核'
        }))
      }
    ]
  },
  {
    id: 'bank_portal',
    name: '银行招考面试',
    desc: '按银行招考面试方向统计。',
    children: [
      ...[
        ['beijing', '北京市'], ['shanghai', '上海市'], ['guangdong', '广东省'], ['jiangsu', '江苏省'],
        ['zhejiang', '浙江省'], ['shandong', '山东省'], ['henan', '河南省'], ['sichuan', '四川省'],
        ['anhui', '安徽省'], ['fujian', '福建省'], ['gansu', '甘肃省'],
        ['guangxi', '广西壮族自治区'], ['guizhou', '贵州省'], ['hainan', '海南省'],
        ['hebei', '河北省'], ['heilongjiang', '黑龙江省'], ['hubei', '湖北省'],
        ['hunan', '湖南省'], ['jilin', '吉林省'], ['jiangxi', '江西省'],
        ['liaoning', '辽宁省'], ['neimenggu', '内蒙古自治区'], ['ningxia', '宁夏回族自治区'],
        ['qinghai', '青海省'], ['shaanxi', '陕西省'], ['shanxi', '山西省'],
        ['tianjin', '天津市'], ['xinjiang', '新疆维吾尔自治区'], ['xizang', '西藏自治区'],
        ['yunnan', '云南省'], ['chongqing', '重庆市'],
      ].map(([code, province]) => ({
        id: `bank_${code}`,
        name: province,
        province: code,
        adminHint: reservedAdminHint(`${province}银行招考`),
        directions: BANK_SYSTEM_DIRECTIONS.map(([sysCode, sysName]) => ({
          id: `bank_${code}_${sysCode}`,
          name: sysName,
          province: code,
          position: 'bank',
          subcategory: sysName
        }))
      }))
    ]
  },
  {
    id: 'clerk_portal',
    name: '法检书记员面试',
    desc: '按已确认题源展示，监狱/税务等系统不会归入此类。',
    levelLabels: { region: '岗位方向', direction: '地区/来源' },
    children: [
      ...[
        ['court', '法院书记员'],
        ['procurate', '检察院书记员']
      ].map(([roleCode, roleName]) => ({
        id: `clerk_${roleCode}`,
        name: roleName,
        province: 'all',
        adminHint: reservedAdminHint(roleName),
        directions: [
          ...CLERK_SOURCE_PROVINCES.map(([code, name]) => ({
            id: `clerk_${roleCode}_${code}_professional`,
            name,
            province: code,
            position: roleCode,
            // portalTag_removed: '法检书记员面试',
            positionType: roleName,
            interviewFormat: '结构化+专业知识',
            timingMode: '15分钟包干',
            prepTime: 0,
            answerTime: 900,
            questionCount: '2-3'
          })),
          ...CLERK_STRUCTURED_PROVINCES
            .filter(([code]) => !CLERK_SOURCE_PROVINCES.some(([sourceCode]) => sourceCode === code))
            .map(([code, name]) => ({
              id: `clerk_${roleCode}_${code}_structured`,
              name,
              province: code,
              position: roleCode,
              // portalTag_removed: '法检书记员面试',
              positionType: roleName,
              interviewFormat: '结构化面试',
              timingMode: '15分钟包干',
              prepTime: 0,
              answerTime: 900,
              questionCount: '2-3'
            }))
        ]
      }))
    ]
  }
]

function ensureReservedProvinceEntries(tree = DEFAULT_TARGETED_POSITION_TREE) {
  const institution = tree.find((item) => item.id === 'institution')
  const provincial = tree.find((item) => item.id === 'provincial_civil')
  if (!institution || !provincial) return tree

  institution.children = institution.children || []
  provincial.children = provincial.children || []
  const institutionCodes = new Set(institution.children.map((item) => item.province))
  const provincialCodes = new Set(provincial.children.map((item) => item.province))

  TARGETED_PROVINCES.forEach(([code, shortName]) => {
    const fullName = provinceName(shortName)
    if (!institutionCodes.has(code)) {
      institution.children.push({
        id: `institution_${code}`,
        name: fullName,
        province: code,
        examCategory: '事业单位考试',
        examSubcategory: fullName,
        adminHint: reservedAdminHint(`${fullName}事业单位`),
        directions: [
          { id: `sydw_${code}_all`, name: `${shortName}事业单位`, province: code, position: '', examCategory: '事业单位考试', examSubcategory: fullName }
        ]
      })
    }
    if (!provincialCodes.has(code)) {
      provincial.children.push({
        id: `provincial_${code}`,
        name: fullName,
        province: code,
        examCategory: '省级公务员考试',
        examSubcategory: fullName,
        adminHint: reservedAdminHint(`${fullName}省考`),
        directions: []
      })
    }
  })
  return tree
}

ensureReservedProvinceEntries()

export function parseTimingFormat(text) {
  if (!text) return null
  const trimmed = String(text).trim()
  // "8+12" → prep=480s, answer=720s
  const plusMatch = /^(\d+)\+(\d+)$/.exec(trimmed)
  if (plusMatch) {
    return { prepTime: parseInt(plusMatch[1], 10) * 60, answerTime: parseInt(plusMatch[2], 10) * 60 }
  }
  // "15分钟包干" / "20分钟作答" → prep=0
  const baoGanMatch = /(\d+)\s*分钟\s*(?:包干|作答|答题)/.exec(trimmed)
  if (baoGanMatch) {
    return { prepTime: 0, answerTime: parseInt(baoGanMatch[1], 10) * 60 }
  }
  return null
}

export function normalizeTargetPayload(target = {}) {
  const payload = {}
  TARGET_FIELDS.forEach((field) => {
    const value = target[field]
    if (value !== undefined && value !== null && String(value).trim() !== '') {
      payload[field] = String(value).trim()
    }
  })
  payload.province = payload.province || 'national'
  payload.position = payload.position || ''
  payload.targetCode = payload.targetCode || String(target.id || target.code || '').trim()
  payload.targetName = payload.targetName || String(target.name || '').trim()

  // Auto-fill prepTime/answerTime from timingMode/interviewFormat if not explicitly set
  if (!payload.prepTime && !payload.answerTime) {
    const parsed = parseTimingFormat(payload.timingMode || payload.interviewFormat || '')
    if (parsed) {
      payload.prepTime = String(parsed.prepTime)
      payload.answerTime = String(parsed.answerTime)
    }
  }
  return payload
}

export function mergeTargetPayload(category = {}, region = {}, direction = {}) {
  return normalizeTargetPayload({
    ...category,
    ...region,
    ...direction,
    targetCode: direction.id || direction.code || region.id || category.id,
    targetName: direction.name || region.name || category.name || ''
  })
}

export function flattenTargetTree(tree = []) {
  const result = []
  tree.forEach((category) => {
    ;(category.children || []).forEach((region) => {
      const directions = region.directions || []
      if (!directions.length) {
        result.push(mergeTargetPayload(category, region, {}))
      }
      directions.forEach((direction) => {
        result.push(mergeTargetPayload(category, region, direction))
      })
    })
  })
  return result
}

export function findTargetByCode(tree = [], code = '') {
  const targetCode = String(code || '').trim()
  if (!targetCode) return null
  return flattenTargetTree(tree).find((item) => item.targetCode === targetCode) || null
}

export function firstTargetInTree(tree = []) {
  return flattenTargetTree(tree)[0] || null
}

export function getTargetMaintenanceHint(target = {}) {
  return String(target.adminHint || target.emptyHint || '').trim()
}
