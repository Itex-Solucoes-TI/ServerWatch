import client from './client'

export const list = () => client.get('/routers')
export const get = (id) => client.get(`/routers/${id}`)
export const create = (data) => client.post('/routers', data)
export const update = (id, data) => client.put(`/routers/${id}`, data)
export const remove = (id) => client.delete(`/routers/${id}`)
export const listInterfaces = (id) => client.get(`/routers/${id}/interfaces`)
export const addInterface = (id, data) => client.post(`/routers/${id}/interfaces`, data)
export const updateInterface = (routerId, interfaceId, data) => client.put(`/routers/${routerId}/interfaces/${interfaceId}`, data)
export const removeInterface = (routerId, interfaceId) => client.delete(`/routers/${routerId}/interfaces/${interfaceId}`)
