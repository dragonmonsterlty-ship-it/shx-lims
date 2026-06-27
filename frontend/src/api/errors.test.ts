import { AxiosError, AxiosHeaders } from 'axios'
import { describe, expect, it } from 'vitest'

import { normalizeApiError } from './errors'

describe('normalizeApiError', () => {
  it('uses a clear backend connection message for network failures', () => {
    const error = new AxiosError('Network Error', 'ERR_NETWORK')

    expect(normalizeApiError(error)).toEqual(
      expect.objectContaining({
        code: -1,
        isNetwork: true,
        message: '无法连接后端 API，请检查服务地址或服务状态',
      }),
    )
  })

  it('keeps backend status, message and validation details', () => {
    const error = new AxiosError(
      'Request failed',
      'ERR_BAD_REQUEST',
      undefined,
      undefined,
      {
        status: 422,
        statusText: 'Unprocessable Entity',
        headers: {},
        config: { headers: new AxiosHeaders() },
        data: {
          code: 422,
          message: 'Validation error',
          data: { errors: [{ loc: ['body', 'name'], msg: 'Field required' }] },
        },
      },
    )

    expect(normalizeApiError(error)).toEqual(
      expect.objectContaining({
        code: 422,
        status: 422,
        message: 'Validation error',
        fieldErrors: { name: 'Field required' },
      }),
    )
  })

  it('keeps the unified 403 error envelope without inventing field errors', () => {
    const error = new AxiosError(
      'Request failed',
      'ERR_BAD_REQUEST',
      undefined,
      undefined,
      {
        status: 403,
        statusText: 'Forbidden',
        headers: {},
        config: { headers: new AxiosHeaders() },
        data: {
          code: 403,
          message: 'Administrator permission required',
          data: null,
        },
      },
    )

    expect(normalizeApiError(error)).toEqual(
      expect.objectContaining({
        code: 403,
        status: 403,
        message: 'Administrator permission required',
        fieldErrors: undefined,
      }),
    )
  })
})
