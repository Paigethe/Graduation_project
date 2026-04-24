import axios from 'axios'

export const api = axios.create({
  baseURL: '',
  timeout: 15000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('bs001_access_token')
  if (token) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

function filenameFromDisposition(disposition?: string | null): string | null {
  if (!disposition) return null
  const utf8Match = disposition.match(/filename\\*=UTF-8''([^;]+)/i)
  if (utf8Match?.[1]) return decodeURIComponent(utf8Match[1])
  const basicMatch = disposition.match(/filename=\"?([^\";]+)\"?/i)
  if (basicMatch?.[1]) return basicMatch[1]
  return null
}

export async function downloadWithAuth(url: string, fallbackName?: string) {
  const response = await api.get(url, { responseType: 'blob' })
  const disposition = response.headers['content-disposition']
  const filename = filenameFromDisposition(disposition) || fallbackName || 'download'

  const blobUrl = window.URL.createObjectURL(response.data)
  const link = document.createElement('a')
  link.href = blobUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(blobUrl)
}
