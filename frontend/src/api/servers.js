import client from './client'

export const list = () => client.get('/servers')
export const get = (id) => client.get(`/servers/${id}`)
export const create = (data) => client.post('/servers', data)
export const update = (id, data) => client.put(`/servers/${id}`, data)
export const remove = (id) => client.delete(`/servers/${id}`)
export const listInterfaces = (id) => client.get(`/servers/${id}/interfaces`)
export const addInterface = (id, data) => client.post(`/servers/${id}/interfaces`, data)
export const updateInterface = (serverId, interfaceId, data) => client.put(`/servers/${serverId}/interfaces/${interfaceId}`, data)
export const removeInterface = (serverId, interfaceId) => client.delete(`/servers/${serverId}/interfaces/${interfaceId}`)
