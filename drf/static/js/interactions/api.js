/**
 * Axios 공통 설정
 * - CSRF 토큰 자동 첨부 (Django CsrfViewMiddleware 대응)
 * - 모든 interactions API 요청의 baseURL
 * 의존: header.js 의 전역 getCsrf()
 */

const api = axios.create({
  baseURL: "/api/interactions/",
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const csrfToken = getCsrf();
  if (csrfToken) config.headers["X-CSRFToken"] = csrfToken;
  return config;
});
