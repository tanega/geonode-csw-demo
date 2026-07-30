const API_BASE = import.meta.env.VITE_GEONODE_API_BASE
const CLIENT_ID = import.meta.env.VITE_OAUTH_CLIENT_ID

export class AuthError extends Error {}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  expires_in: number
  token_type: string
  scope: string
}

export interface UserInfo {
  sub: string
  email: string
  preferred_username: string
  groups: string[]
}

export interface SignupPayload {
  username: string
  email: string
  password1: string
  password2: string
}

// openid must never be requested here: it breaks refresh_token on this
// stack (see docs/iam-option-a-login.md).
const TOKEN_SCOPE = 'read write groups'

export async function login(username: string, password: string): Promise<TokenResponse> {
  const response = await fetch(`${API_BASE}/o/token/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'password',
      username,
      password,
      client_id: CLIENT_ID,
      scope: TOKEN_SCOPE,
    }),
  })

  if (!response.ok) {
    const data = await response.json().catch(() => null)
    throw new AuthError(data?.error_description ?? 'Login failed')
  }

  return response.json()
}

export async function fetchUserInfo(accessToken: string): Promise<UserInfo> {
  const response = await fetch(`${API_BASE}/api/o/v4/userinfo/`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })

  if (!response.ok) throw new AuthError('Failed to fetch user info')

  return response.json()
}

export async function signup(payload: SignupPayload): Promise<void> {
  const response = await fetch(`${API_BASE}/api/v2/signup/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const data = await response.json().catch(() => null)
    throw new AuthError(data?.errors?.join(', ') ?? 'Signup failed')
  }
}
