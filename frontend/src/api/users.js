import client from './client'

export const list = () => client.get('/users')
export const get = (id) => client.get(`/users/${id}`)
export const create = (data) => client.post('/users', data)
export const update = (id, data) => client.put(`/users/${id}`, data)
export const remove = (id) => client.delete(`/users/${id}`)
export const myAdminCompanies = () => client.get('/users/my-companies')
export const getUserCompanies = (id) => client.get(`/users/${id}/companies`)
