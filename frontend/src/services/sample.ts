import { unwrap } from '../api/client'
import { mockServer } from '../api/mock'
import type {
  Id,
  PageResult,
  Sample,
  SampleListQuery,
  SampleTestRow,
  TestMethod,
  User,
} from '../types'

export async function listSamples(
  query: SampleListQuery,
  currentUser: User,
): Promise<PageResult<Sample>> {
  return unwrap(await mockServer.samples.list(query, currentUser))
}

export async function getSample(id: Id): Promise<Sample> {
  return unwrap(await mockServer.samples.get(id))
}

export async function listSampleTests(sampleId: Id): Promise<SampleTestRow[]> {
  return unwrap(await mockServer.samples.tests(sampleId))
}

export async function listTestMethods(): Promise<TestMethod[]> {
  return unwrap(await mockServer.testMethods.list())
}

export const sampleService = { listSamples, getSample, listSampleTests, listTestMethods }
