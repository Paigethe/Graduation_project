import type { PageResp } from './types'
import { api } from './client'
import type { AxiosResponse } from 'axios'

export async function fetchAll<T>(url: string, maxPages = 10): Promise<T[]> {
  const out: T[] = []
  let pageUrl: string | null = url
  let pages = 0

  while (pageUrl && pages < maxPages) {
    const resp: AxiosResponse<PageResp<T>> = await api.get<PageResp<T>>(pageUrl)
    out.push(...(resp.data.results ?? []))
    pageUrl = resp.data.next
    pages += 1
  }
  return out
}
