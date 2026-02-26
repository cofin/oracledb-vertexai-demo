const CSRF_COOKIE_NAME = "XSRF-TOKEN"
const CSRF_HEADER_NAME = "X-XSRF-TOKEN"

function getCookie(name: string): string | null {
  if (typeof document === "undefined") {
    return null
  }
  const prefix = `${name}=`
  const cookie = document.cookie.split("; ").find((entry) => entry.startsWith(prefix))
  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : null
}

export async function apiFetch(input: RequestInfo | URL, init: RequestInit = {}) {
  const headers = new Headers(init.headers)
  const csrfToken = getCookie(CSRF_COOKIE_NAME)
  if (csrfToken && !headers.has(CSRF_HEADER_NAME)) {
    headers.set(CSRF_HEADER_NAME, csrfToken)
  }

  return fetch(input, {
    ...init,
    credentials: "same-origin",
    headers,
  })
}
