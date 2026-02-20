import client from './client'

export const list = () => client.get('/companies')
export const get = (id) => client.get(`/companies/${id}`)
export const create = (data) => client.post('/companies', data)
export const update = (id, data) => client.put(`/companies/${id}`, data)
