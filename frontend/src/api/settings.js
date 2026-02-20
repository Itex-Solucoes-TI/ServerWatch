import client from './client'

export const get = () => client.get('/settings')
export const update = (data) => client.put('/settings', data)
