import { describe, expect, it } from 'vitest'

import { reagentImportFileValidationMessage } from './reagentImportFile'

describe('ReagentImportModal file validation', () => {
  it('accepts only CSV and XLSX by extension', () => {
    expect(reagentImportFileValidationMessage(new File(['x'], '库存.csv'))).toBeNull()
    expect(reagentImportFileValidationMessage(new File(['x'], '库存.XLSX'))).toBeNull()
    expect(reagentImportFileValidationMessage(new File(['x'], '库存.xls'))).toContain('.csv 和 .xlsx')
    expect(reagentImportFileValidationMessage(new File(['x'], '库存.xlsm'))).toContain('.csv 和 .xlsx')
    expect(reagentImportFileValidationMessage(new File(['x'], '库存.txt'))).toContain('.csv 和 .xlsx')
  })
})
