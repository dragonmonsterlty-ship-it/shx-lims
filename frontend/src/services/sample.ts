import {
  adaptSample,
  adaptTestTask,
  type BackendSample,
  type BackendTestTask,
} from '../api/adapters'
import { endpoints } from '../api/endpoints'
import { request } from '../api/http'
import type {
  Id,
  PageResult,
  Sample,
  SampleInput,
  SampleListQuery,
  SampleStatus,
  TestMethod,
  TestTask,
  TaskStatus,
  User,
} from '../types'

interface BackendTestMethod {
  id: Id
  code: string
  name: string
  category?: string | null
  version?: string | null
  description?: string | null
  is_active: boolean
  created_by?: Id | null
  created_at?: string
  updated_by?: Id | null
  updated_at?: string | null
}

const adaptMethod = (raw: BackendTestMethod): TestMethod => ({
  ...raw,
  method: raw.category ?? null,
})

export async function listSamples(
  query: SampleListQuery,
  currentUser: User,
): Promise<PageResult<Sample>> {
  void currentUser
  const result = await request<PageResult<BackendSample>>({
    method: 'GET',
    url: endpoints.samples.root,
    params: query,
  })
  return { ...result, items: result.items.map(adaptSample) }
}

export async function getSample(id: Id): Promise<Sample> {
  return adaptSample(await request<BackendSample>({ method: 'GET', url: endpoints.samples.detail(id) }))
}

export async function createSample(input: SampleInput): Promise<Sample> {
  return adaptSample(
    await request<BackendSample>({ method: 'POST', url: endpoints.samples.root, data: input }),
  )
}

export async function updateSample(id: Id, input: Partial<SampleInput>): Promise<Sample> {
  const payload: Record<string, unknown> = { ...input }
  delete payload.project_id
  delete payload.sample_no
  return adaptSample(
    await request<BackendSample>({ method: 'PATCH', url: endpoints.samples.detail(id), data: payload }),
  )
}

export async function changeSampleStatus(id: Id, status: SampleStatus): Promise<Sample> {
  return adaptSample(
    await request<BackendSample>({
      method: 'POST',
      url: endpoints.samples.status(id),
      data: { status },
    }),
  )
}

export async function listSampleTests(sampleId: Id): Promise<TestTask[]> {
  const result = await request<PageResult<BackendTestTask>>({
    method: 'GET',
    url: endpoints.testTasks.root,
    params: { sample_id: sampleId, page_size: 100 },
  })
  return result.items.map(adaptTestTask)
}

export async function listTestMethods(): Promise<TestMethod[]> {
  const result = await request<PageResult<BackendTestMethod>>({
    method: 'GET',
    url: endpoints.testMethods.root,
    params: { page_size: 100 },
  })
  return result.items.map(adaptMethod)
}

export async function createTestTask(input: {
  sample_id: Id
  method_id: Id
  assigned_to: Id
  priority?: string
  due_date?: string | null
}): Promise<TestTask> {
  return adaptTestTask(
    await request<BackendTestTask>({ method: 'POST', url: endpoints.testTasks.root, data: input }),
  )
}

export async function updateTaskAssignee(id: Id, assignedTo: Id): Promise<TestTask> {
  return adaptTestTask(
    await request<BackendTestTask>({
      method: 'PATCH',
      url: endpoints.testTasks.assignee(id),
      data: { assigned_to: assignedTo },
    }),
  )
}

export async function changeTaskStatus(id: Id, status: TaskStatus): Promise<TestTask> {
  return adaptTestTask(
    await request<BackendTestTask>({
      method: 'POST',
      url: endpoints.testTasks.status(id),
      data: { status },
    }),
  )
}

export const sampleService = {
  listSamples,
  getSample,
  createSample,
  updateSample,
  changeSampleStatus,
  listSampleTests,
  listTestMethods,
  createTestTask,
  updateTaskAssignee,
  changeTaskStatus,
}
