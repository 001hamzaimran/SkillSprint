import ky from 'ky'

let csrfToken = ''

export function setCsrfToken(token: string) {
  csrfToken = token
}

export function getCsrfToken(): string {
  return csrfToken
}

const api = ky.create({
  prefixUrl: '/api',
  credentials: 'include',
  hooks: {
    beforeRequest: [
      (request) => {
        const method = request.method.toUpperCase()
        if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method) && csrfToken) {
          request.headers.set('X-CSRF-Token', csrfToken)
        }
      },
    ],
    afterResponse: [
      async (_request, _options, response) => {
        const path = new URL(_request.url).pathname
        if (response.status === 401 && !path.startsWith('/api/auth/')) {
          setCsrfToken('')
          const base = window.location.pathname === '/app' || window.location.pathname.startsWith('/app/') ? '/app' : ''
          window.location.assign(`${base}/login`)
        }
      },
    ],
  },
  timeout: 30000,
})

export default api
