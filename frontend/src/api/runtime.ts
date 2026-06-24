export type ApiMode = 'real' | 'mock'

export function resolveApiMode(value?: string): ApiMode {
  return value?.toLowerCase() === 'mock' ? 'mock' : 'real'
}

export const API_MODE = resolveApiMode(import.meta.env.VITE_API_MODE as string | undefined)
export const USE_MOCK = API_MODE === 'mock'
