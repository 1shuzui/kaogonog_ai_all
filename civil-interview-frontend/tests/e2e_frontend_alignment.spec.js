/**
 * 这个前端测试文件守住 `e2e_frontend_alignment.spec` 的回归行为；它让提交表单、页面联动这类细节不会悄悄退化。
 *
 * @param 无；文件级模块依赖导出函数、组合式 API 或调用方传入上下文。
 * @return 导出可复用的端侧能力，具体返回值由各公共函数保持兼容。
 * @raises 不主动吞掉业务异常；请求失败、权限不足和运行时错误交由调用方或全局拦截器处理。
 */
import { test, expect } from '@playwright/test'

function uniqueUser(prefix) {
  return `${prefix}_${Date.now()}_${Math.floor(Math.random() * 1000)}`
}

async function createUserWithToken(api, prefix) {
  const username = uniqueUser(prefix)
  const password = 'Test123456'

  await api.post('http://127.0.0.1:8050/register', {
    data: { username, password }
  })
  const tokenResp = await api.post('http://127.0.0.1:8050/token', {
    form: { username, password }
  })
  const tokenJson = await tokenResp.json()
  return { username, token: tokenJson.access_token }
}

test.describe('PC frontend paid access check', () => {
  test('trial user is blocked by route guard, but local paid unlock still cannot call premium APIs', async ({ page, request }) => {
    test.setTimeout(90_000)
    const session = await createUserWithToken(request, 'pcdeep')
    await page.addInitScript(({ token, username }) => {
      localStorage.setItem('token', token)
      localStorage.setItem('username', username)
      localStorage.setItem('civil_selected_province', 'beijing')
      localStorage.setItem('civil_selected_province_confirmed', '1')
      localStorage.setItem(`civil_selected_province:${username}`, 'beijing')
      localStorage.setItem(`civil_selected_province_confirmed:${username}`, '1')
      localStorage.removeItem('civil_billing_state')
    }, session)

    await page.goto('http://127.0.0.1:3003/targeted')
    await expect(page).toHaveURL('http://127.0.0.1:3003/')

    await page.evaluate(() => {
      localStorage.setItem('civil_billing_state', JSON.stringify({
        planType: 'monthly',
        remainingSeconds: 0,
        monthlyExpireAt: Date.now() + 30 * 24 * 60 * 60 * 1000,
        activatedAt: Date.now(),
        orderHistory: [],
        paywallVisible: false,
        paywallSource: '',
        activeSessionStartedAt: 0,
        activeSessionKind: '',
        lastPaywallSource: '',
        lastIntendedPath: ''
      }))
    })

    await page.goto('http://127.0.0.1:3003/targeted')
    await expect(page).toHaveURL('http://127.0.0.1:3003/targeted')

    const backendDenied = await request.post('http://127.0.0.1:8050/targeted/generate', {
      headers: { Authorization: `Bearer ${session.token}` },
      data: { province: 'beijing', position: 'tax', count: 3 }
    })
    expect(backendDenied.status()).toBe(403)
  })
})

test.describe('Mini H5 frontend paid access check', () => {
  test('trial user can enter paid pages but backend rejects paid APIs', async ({ page, request }) => {
    test.setTimeout(90_000)
    const session = await createUserWithToken(request, 'minideep')
    await page.addInitScript(({ token, username }) => {
      localStorage.setItem('token', token)
      localStorage.setItem('username', username)
      localStorage.setItem('civil_mini_billing_state', JSON.stringify({ planType: 'trial', activatedAt: 0 }))
    }, session)

    await page.goto('http://127.0.0.1:3004/#/pages/targeted/index')
    await expect(page.getByText('定向备面').first()).toBeVisible()
    await page.getByText('国考').first().click()
    await page.getByText('税务系统').first().click()

    const targetedRespPromise = page.waitForResponse((resp) => (
      resp.url().includes('/targeted/generate') && resp.request().method() === 'POST'
    ))
    await page.getByText('生成题目').last().click()
    const targetedResp = await targetedRespPromise
    expect(targetedResp.status()).toBe(403)

    await page.goto('http://127.0.0.1:3004/#/pages/training/dimension?key=analysis')
    await expect(page.getByText('训练进度')).toBeVisible()
    const trainingRespPromise = page.waitForResponse((resp) => (
      resp.url().includes('/training/generate') && resp.request().method() === 'POST'
    ))
    await page.getByText('生成训练题').last().click()
    const trainingResp = await trainingRespPromise
    expect(trainingResp.status()).toBe(403)

    await page.goto('http://127.0.0.1:3004/#/pages/exam/prepare')
    const prepareRespPromise = page.waitForResponse((resp) => (
      resp.url().includes('/questions/random') && resp.request().method() === 'GET'
    ))
    await page.getByText('进入考场').last().click()
    const prepareResp = await prepareRespPromise
    expect(prepareResp.status()).toBe(403)
  })
})
