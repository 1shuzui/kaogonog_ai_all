const frontendBase = process.env.CIVIL_FRONTEND_BASE || 'http://127.0.0.1:3001'
const proxyBase = `${frontendBase}/api`
const username = `smoke_${Date.now()}`
const password = 'Smoke123456'

async function request(path, options = {}) {
  const response = await fetch(`${proxyBase}${path}`, options)
  const raw = await response.text()
  let data
  try {
    data = raw ? JSON.parse(raw) : {}
  } catch {
    data = raw
  }

  if (!response.ok) {
    throw new Error(`${options.method || 'GET'} ${path} failed (${response.status}): ${typeof data === 'string' ? data : JSON.stringify(data)}`)
  }
  return data
}

async function main() {
  await request('/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  })

  const form = new URLSearchParams()
  form.set('username', username)
  form.set('password', password)
  const tokenResult = await request('/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: form
  })

  const authHeaders = {
    Authorization: `Bearer ${tokenResult.access_token}`
  }

  const userInfo = await request('/user/info', { headers: authHeaders })
  const questionList = await request('/questions?province=hunan&current=1&pageSize=5', {
    headers: authHeaders
  })
  const targeted = await request('/targeted/generate', {
    method: 'POST',
    headers: {
      ...authHeaders,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ province: 'hunan', position: 'prison', count: 3 })
  })

  const questionId =
    targeted?.questions?.[0]?.id ||
    questionList?.list?.[0]?.id

  if (!questionId) {
    throw new Error('No question available for smoke scoring')
  }

  const scoring = await request('/scoring/evaluate', {
    method: 'POST',
    headers: {
      ...authHeaders,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      questionId,
      transcript: '首先，我会安抚群众情绪，说明政策依据。其次，提供可行方案和补充材料指引。最后，复盘流程短板，优化一次性告知和回访机制。',
      examId: null
    })
  })

  console.log(JSON.stringify({
    username,
    userProvince: userInfo?.province || '',
    listedQuestions: questionList?.list?.length || 0,
    targetedSources: (targeted?.questions || []).map((item) => ({
      id: item.id,
      generationSource: item.generationSource,
      questionSourceLabel: item.questionSourceLabel,
      province: item.province
    })),
    scoringMode: scoring?.scoringMode || 'llm',
    totalScore: scoring?.totalScore || 0
  }, null, 2))
}

main().catch((error) => {
  console.error(error.stack || String(error))
  process.exit(1)
})
