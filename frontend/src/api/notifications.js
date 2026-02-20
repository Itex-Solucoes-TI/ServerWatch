import client from './client'

export const listChannels = () => client.get('/notifications/channels')
export const createChannel = (data) => client.post('/notifications/channels', data)
export const updateChannel = (id, data) => client.put(`/notifications/channels/${id}`, data)
export const deleteChannel = (id) => client.delete(`/notifications/channels/${id}`)
export const listRules = () => client.get('/notifications/rules')
export const createRule = (data) => client.post('/notifications/rules', data)
export const updateRule = (id, data) => client.put(`/notifications/rules/${id}`, data)
export const deleteRule = (id) => client.delete(`/notifications/rules/${id}`)
