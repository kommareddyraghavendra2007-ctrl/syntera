import axios from 'axios'

// All API calls go through the backend — no LLM/Qdrant keys in frontend
const client = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
  timeout: 120_000,
})

client.interceptors.response.use(
  (res) => res,
  (err) => {
    const message =
      err.response?.data?.detail ??
      err.response?.data?.message ??
      err.message ??
      'An unexpected error occurred'
    return Promise.reject(new Error(message))
  },
)

export default client
