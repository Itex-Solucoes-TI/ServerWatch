import client from './client'

export const getGraph = () => client.get('/topology')
export const createLink = (data) => client.post('/topology/links', data)
export const deleteLink = (id) => client.delete(`/topology/links/${id}`)
export const savePositions = (positions) => client.put('/topology/positions', positions)

export const getGenericDevice = (id) => client.get(`/topology/devices/${id}`)
export const createGenericDevice = (data) => client.post('/topology/devices', data)
export const updateGenericDevice = (id, data) => client.put(`/topology/devices/${id}`, data)
export const deleteGenericDevice = (id) => client.delete(`/topology/devices/${id}`)
