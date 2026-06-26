const MAX_FILE_SIZE = 20 * 1024 * 1024
const BLOCKED_EXTENSIONS = new Set(['exe', 'bat', 'cmd', 'ps1', 'sh', 'js', 'mjs', 'cjs', 'html', 'htm'])

export function clientFileValidationMessage(file: Pick<File, 'name' | 'size'>): string | null {
  if (file.size > MAX_FILE_SIZE) return '单个文件不超过 20 MB'
  const extension = file.name.split('.').pop()?.toLowerCase()
  if (!extension) return '文件必须包含扩展名'
  if (BLOCKED_EXTENSIONS.has(extension)) return `不允许上传 .${extension} 类型文件`
  return null
}
