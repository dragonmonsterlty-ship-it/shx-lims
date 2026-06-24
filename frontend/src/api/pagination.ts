import type { PageResult } from '../types/common'

export const DEFAULT_PAGE_SIZE = 10

export function emptyPage<T>(page = 1, page_size = DEFAULT_PAGE_SIZE): PageResult<T> {
  return { items: [], total: 0, page, page_size }
}

/** 对内存数组做客户端分页，输出统一 PageResult。 */
export function paginate<T>(items: T[], page = 1, page_size = DEFAULT_PAGE_SIZE): PageResult<T> {
  const safePage = Math.max(1, page)
  const safeSize = Math.max(1, page_size)
  const start = (safePage - 1) * safeSize
  return {
    items: items.slice(start, start + safeSize),
    total: items.length,
    page: safePage,
    page_size: safeSize,
  }
}

/**
 * 归一化两种后端返回：纯数组 或 {items,total,page,page_size}。
 * 真实后端目前返回纯数组时也能被页面以统一结构消费。
 */
export function toPageResult<T>(
  raw: T[] | PageResult<T>,
  page = 1,
  page_size = DEFAULT_PAGE_SIZE,
): PageResult<T> {
  if (Array.isArray(raw)) {
    return { items: raw, total: raw.length, page, page_size: raw.length || page_size }
  }
  return raw
}
