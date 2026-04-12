import { mockDelay } from './index'

export async function mockLogin(username, password) {
  await mockDelay(500)
  if (username === 'admin' && password === '123456') {
    return {
      access_token: 'mock_jwt_token_' + Date.now(),
      token_type: 'bearer'
    }
  }
  throw { response: { status: 401, data: { detail: '用户名或密码错误' } } }
}

export async function mockRegister(form) {
  await mockDelay(500)
  if (!form.username || !form.password) {
    throw { response: { status: 400, data: { detail: '请填写完整信息' } } }
  }
  return { success: true, message: '注册成功' }
}
