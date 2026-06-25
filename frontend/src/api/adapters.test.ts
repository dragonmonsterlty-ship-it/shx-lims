import { describe, expect, it } from 'vitest'

import {
  adaptDailyReport,
  adaptExperiment,
  adaptInventoryTransaction,
  adaptProject,
  adaptReagentLot,
  adaptSample,
  adaptTestResult,
  adaptTestTask,
  adaptUser,
  normalizeRole,
  toBackendExperimentCreate,
  toBackendExperimentUpdate,
  toBackendDailyReportCreate,
  toBackendDailyReportUpdate,
  toBackendReagentCreate,
  toBackendReagentLotCreate,
  toBackendReagentLotUpdate,
  toBackendReagentUpdate,
} from './adapters'

const user = {
  id: 7,
  name: 'Demo Manager',
  username: 'manager',
  role: 'project_manager',
}

describe('backend adapters', () => {
  it('normalizes backend role aliases into the frontend role enum', () => {
    expect(normalizeRole('pm')).toBe('project_manager')
    expect(normalizeRole('PROJECT_MANAGER')).toBe('project_manager')
    expect(normalizeRole('principal_investigator')).toBe('project_manager')
    expect(normalizeRole('admin')).toBe('admin')
    expect(normalizeRole('director')).toBe('director')
    expect(normalizeRole('researcher')).toBe('operator')
    expect(normalizeRole('unknown_role')).toBe('operator')
    expect(normalizeRole(undefined)).toBe('operator')
  })

  it('adaptUser maps a backend pm role to project_manager', () => {
    expect(adaptUser({ id: 1, username: 'm', role: 'pm' }).role).toBe('project_manager')
    expect(adaptUser({ id: 2, username: 'r', role: 'researcher' }).role).toBe('operator')
  })

  it('maps experiment create payload to the backend experiment-records contract', () => {
    const payload = toBackendExperimentCreate({
      project_id: 3,
      experiment_no: 'EXP-7',
      title: 'Assay run',
      lead_user_id: 9,
      participant_ids: [4, 5],
      status: 'draft',
      plan_start_date: '2026-06-24',
      plan_end_date: '2026-06-30',
      objective: 'check',
      steps: ['step1', 'step2'],
      result_summary: 'ok',
    })
    expect(payload).toEqual({
      project_id: 3,
      code: 'EXP-7',
      title: 'Assay run',
      record_type: 'other',
      status: 'draft',
      owner_id: 9,
      experiment_date: '2026-06-24',
      objective: 'check',
      procedure: 'step1\nstep2',
      result_summary: 'ok',
      conclusion: null,
      next_step: null,
      risk_note: null,
      participant_ids: [4, 5],
      reagent_usages: [],
    })
  })

  it('auto-generates a code when experiment_no is empty and honors explicit record_type', () => {
    const payload = toBackendExperimentCreate({
      project_id: 1,
      title: 't',
      lead_user_id: 2,
      record_type: 'synthesis',
    })
    expect(payload.code).toMatch(/^EXP-\d+$/)
    expect(payload.record_type).toBe('synthesis')
    expect(payload.experiment_date).toBeNull()
  })

  it('maps experiment update payload to only the provided fields', () => {
    expect(
      toBackendExperimentUpdate({ experiment_no: 'EXP-9', lead_user_id: 6, steps: 'do it' }),
    ).toEqual({ code: 'EXP-9', owner_id: 6, procedure: 'do it' })
    expect(toBackendExperimentUpdate({ title: 'x' })).toEqual({ title: 'x' })
  })

  it('maps reagent create payload (material_code→catalog_no, specification→grade)', () => {
    const payload = toBackendReagentCreate({
      name: '甲醇',
      material_code: 'MEOH-01',
      cas_no: '67-56-1',
      specification: 'HPLC',
      unit: 'mL',
    })
    expect(payload).toEqual({
      name: '甲醇',
      cas_no: '67-56-1',
      catalog_no: 'MEOH-01',
      grade: 'HPLC',
      default_unit: 'mL',
      manufacturer: null,
      min_stock: null,
      is_active: true,
    })
    // 前端独有字段（category/safety_level/storage_condition）不写入后端
    expect('category' in payload).toBe(false)
    expect('safety_level' in payload).toBe(false)
  })

  it('maps reagent update payload to only the provided fields', () => {
    expect(toBackendReagentUpdate({ material_code: 'X-1', specification: 'AR' })).toEqual({
      catalog_no: 'X-1',
      grade: 'AR',
    })
  })

  it('maps reagent lot create (batch_no→lot_no, status normalize)', () => {
    expect(
      toBackendReagentLotCreate({ reagent_id: 5, batch_no: 'LOT-1', quantity: 10, status: 'frozen' }),
    ).toEqual(
      expect.objectContaining({
        reagent_id: 5,
        lot_no: 'LOT-1',
        quantity: 10,
        status: 'quarantined',
        controlled_flag: false,
      }),
    )
    expect(toBackendReagentLotCreate({ reagent_id: 5, batch_no: 'LOT-2' }).status).toBe('in_stock')
  })

  it('reagent lot update never writes quantity (stock changes go via transactions)', () => {
    const out = toBackendReagentLotUpdate({ quantity: 99, location: 'Shelf-A' })
    expect(out).toEqual({ location: 'Shelf-A' })
    expect('quantity' in out).toBe(false)
  })

  it('preserves multiple daily report items on read', () => {
    const r = adaptDailyReport({
      id: 1,
      user,
      report_date: '2026-06-24',
      status: 'draft',
      summary: 's',
      item_count: 2,
      project_count: 1,
      experiment_record_count: 1,
      items: [
        { id: 1, daily_report_id: 1, work_type: 'analysis', content: 'a', sort_order: 0 },
        { id: 2, daily_report_id: 1, work_type: 'other', content: 'b', sort_order: 1 },
      ],
      attachments: [],
    })
    expect(r.items?.length).toBe(2)
    expect(r.work_content).toBe('s')
  })

  it('converts a flat daily report input to a single backend item', () => {
    const payload = toBackendDailyReportCreate({
      project_id: 3,
      related_experiment_id: 11,
      report_date: '2026-06-24',
      work_content: 'did work',
      issues_risks: 'risk',
      next_plan: 'tomorrow',
    })
    expect(payload.summary).toBe('did work')
    const items = payload.items as Record<string, unknown>[]
    expect(items).toHaveLength(1)
    expect(items[0]).toEqual({
      project_id: 3,
      experiment_record_id: 11,
      work_type: 'other',
      content: 'did work',
      progress_note: null,
      hours_spent: null,
      problem_note: 'risk',
      next_step: 'tomorrow',
      sort_order: 0,
    })
  })

  it('writes multiple daily report items with defaults and sort order', () => {
    const payload = toBackendDailyReportCreate({
      project_id: 1,
      report_date: '2026-06-24',
      work_content: 'summary',
      items: [
        { content: 'first', hours_spent: 2, project_id: 5, experiment_record_id: 9, problem_note: 'p', next_step: 'n' },
        { content: 'second', work_type: 'analysis' },
      ],
    })
    const items = payload.items as Record<string, unknown>[]
    expect(items).toHaveLength(2)
    expect(items[0]).toMatchObject({ content: 'first', work_type: 'other', hours_spent: 2, project_id: 5, experiment_record_id: 9, problem_note: 'p', next_step: 'n', sort_order: 0 })
    expect(items[1]).toMatchObject({ content: 'second', work_type: 'analysis', sort_order: 1 })
  })

  it('daily report update only sends provided fields (no unknown keys)', () => {
    expect(toBackendDailyReportUpdate({ next_plan: 'np' })).toEqual({ next_plan: 'np' })
    const withItems = toBackendDailyReportUpdate({ items: [{ content: 'x' }] })
    expect(Object.keys(withItems)).toEqual(['items', 'summary', 'issues', 'next_plan'])
    expect((withItems.items as Record<string, unknown>[])[0]).toMatchObject({ content: 'x', work_type: 'other' })
  })


  it('maps project list aliases into the existing project view model', () => {
    expect(
      adaptProject({
        id: 3,
        code: 'P-003',
        name: 'Assay',
        type: 'analysis',
        status: 'active',
        owner: user,
        priority: 'high',
        start_date: '2026-06-01',
        expected_end_date: '2026-08-01',
        member_count: 4,
        progress: 35,
      }),
    ).toEqual(
      expect.objectContaining({
        id: 3,
        project_code: 'P-003',
        project_type: 'analysis',
        lead_user_id: 7,
        end_date: '2026-08-01',
        priority: 'high',
        is_deleted: false,
      }),
    )
  })

  it('maps an experiment detail and its reagent usages', () => {
    const result = adaptExperiment({
      id: 11,
      code: 'EXP-011',
      title: 'HPLC assay',
      project_id: 3,
      project_code: 'P-003',
      project_name: 'Assay',
      record_type: 'analysis',
      status: 'submitted',
      creator: user,
      owner: null,
      experiment_date: '2026-06-23',
      procedure: 'Run method',
      reagent_usages: [
        {
          id: 21,
          experiment_record_id: 11,
          reagent_id: 5,
          lot_id: 9,
          reagent_name_snapshot: 'Methanol',
          lot_code_snapshot: 'LOT-9',
          quantity: '1.2500',
          unit: 'mL',
          purpose: 'mobile phase',
        },
      ],
      attachments: [],
      attachment_count: 0,
      reagent_usage_count: 1,
    })

    expect(result).toEqual(
      expect.objectContaining({
        experiment_no: 'EXP-011',
        lead_user_id: 7,
        participant_ids: [],
        plan_start_date: '2026-06-23',
        steps: 'Run method',
        status: 'submitted',
      }),
    )
    expect(result.material_usages?.[0]).toEqual(
      expect.objectContaining({
        batch_id: 9,
        material_name: 'Methanol',
        batch_no: 'LOT-9',
        actual_qty: 1.25,
      }),
    )
  })

  it('maps a daily report detail using its first item for the current UI', () => {
    const result = adaptDailyReport({
      id: 31,
      user,
      user_id: 7,
      report_date: '2026-06-23',
      status: 'reviewed',
      summary: 'Daily summary',
      issues: 'No blocker',
      next_plan: 'Continue',
      item_count: 1,
      project_count: 1,
      experiment_record_count: 1,
      items: [
        {
          id: 1,
          daily_report_id: 31,
          project_id: 3,
          experiment_record_id: 11,
          work_type: 'analysis',
          content: 'Completed assay',
          sort_order: 0,
        },
      ],
      attachments: [],
    })

    expect(result).toEqual(
      expect.objectContaining({
        user_id: 7,
        project_id: 3,
        related_experiment_id: 11,
        work_content: 'Daily summary',
        issues_risks: 'No blocker',
        status: 'confirmed',
      }),
    )
  })

  it('maps reagent lot numbers and inventory transaction signs', () => {
    const lot = adaptReagentLot(
      {
        id: 9,
        reagent_id: 5,
        lot_no: 'LOT-9',
        quantity: '12.5000',
        unit: 'mL',
        status: 'in_stock',
        controlled_flag: false,
      },
      {
        id: 5,
        name: 'Methanol',
        catalog_no: 'MEOH-01',
        manufacturer: 'Demo Vendor',
        default_unit: 'mL',
        is_active: true,
      },
    )
    const txn = adaptInventoryTransaction({
      id: 40,
      reagent_lot_id: 9,
      txn_type: 'out',
      quantity: '2.5000',
      balance_after: '10.0000',
      operator_id: 8,
      txn_at: '2026-06-23T12:00:00Z',
    })

    expect(lot.batch).toEqual(
      expect.objectContaining({
        material_id: 5,
        batch_no: 'LOT-9',
        quantity: 12.5,
        status: 'normal',
      }),
    )
    expect(lot.material).toEqual(
      expect.objectContaining({
        material_code: 'MEOH-01',
        name: 'Methanol',
      }),
    )
    expect(txn).toEqual(
      expect.objectContaining({
        batch_id: 9,
        transaction_type: 'outbound',
        qty_delta: -2.5,
      }),
    )
  })

  it('marks an in-stock lot as low when quantity is below reagent min_stock', () => {
    const result = adaptReagentLot(
      {
        id: 10,
        reagent_id: 5,
        lot_no: 'LOW-LOT',
        quantity: '2.0000',
        unit: 'mL',
        status: 'in_stock',
        controlled_flag: false,
      },
      {
        id: 5,
        name: 'Methanol',
        default_unit: 'mL',
        min_stock: '10.0000',
        is_active: true,
      },
    )

    expect(result.row.status).toBe('low')
  })

  it('maps the T1.5 sample contract without mock-only field drift', () => {
    expect(
      adaptSample({
        id: 51,
        project_id: 3,
        sample_no: 'S-051',
        sample_code: 'S-051',
        name: 'Assay sample',
        type: 'compound',
        sample_type: 'compound',
        amount: '10.5000',
        unit: 'mg',
        status: 'registered',
        priority: 'normal',
        is_deleted: false,
        created_at: '2026-06-25T00:00:00Z',
      }),
    ).toEqual(
      expect.objectContaining({
        id: 51,
        sample_no: 'S-051',
        sample_code: 'S-051',
        type: 'compound',
        amount: 10.5,
      }),
    )
  })

  it('maps nested T1.5 task and result summaries', () => {
    const task = adaptTestTask({
      id: 61,
      sample_id: 51,
      method_id: 7,
      test_method_id: 7,
      assigned_to: 9,
      status: 'in_progress',
      priority: 'high',
      sample: { id: 51, project_id: 3, sample_no: 'S-051', name: 'Assay sample', status: 'in_testing' },
      method: { id: 7, code: 'HPLC', name: 'Assay', category: 'assay', version: '1.0' },
      result_id: 71,
      result_status: 'submitted',
      created_at: '2026-06-25T00:00:00Z',
    })
    const result = adaptTestResult({
      id: 71,
      task_id: 61,
      sample_test_id: 61,
      result_data: { assay: 99.4 },
      conclusion: 'Pass',
      status: 'submitted',
      submitted_by: 9,
      task: {
        id: 61,
        sample_id: 51,
        method_id: 7,
        test_method_id: 7,
        assigned_to: 9,
        status: 'in_progress',
        priority: 'high',
        sample: { id: 51, project_id: 3, sample_no: 'S-051', name: 'Assay sample', status: 'pending_review' },
        method: { id: 7, code: 'HPLC', name: 'Assay' },
        result_id: 71,
        result_status: 'submitted',
        created_at: '2026-06-25T00:00:00Z',
      },
      created_at: '2026-06-25T00:00:00Z',
    })

    expect(task.method_name).toBe('Assay')
    expect(task.review_status).toBe('submitted')
    expect(result.sample_code).toBe('S-051')
    expect(result.review_status).toBe('submitted')
  })
})
