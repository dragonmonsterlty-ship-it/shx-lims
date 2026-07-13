const ACCEPTED_EXTENSIONS = ['.csv', '.xlsx']

export function reagentImportFileValidationMessage(file: File): string | null {
  const name = file.name.toLowerCase()
  return ACCEPTED_EXTENSIONS.some((extension) => name.endsWith(extension))
    ? null
    : '仅支持 .csv 和 .xlsx 文件'
}
