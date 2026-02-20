import client from './client'

export const list = () => client.get('/checks')
export const get = (id) => client.get(`/checks/${id}`)
export const create = (data) => client.post('/checks', data)
export const update = (id, data) => client.put(`/checks/${id}`, data)
export const remove = (id) => client.delete(`/checks/${id}`)
export const getResults = (id, limit = 50) => client.get(`/checks/${id}/results`, { params: { limit } })
export const runNow = (id) => client.post(`/checks/${id}/run`)
