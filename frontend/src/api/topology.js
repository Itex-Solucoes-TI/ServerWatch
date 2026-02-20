import client from './client'

export const getGraph = () => client.get('/topology')
export const createLink = (data) => client.post('/topology/links', data)
export const deleteLink = (id) => client.delete(`/topology/links/${id}`)
export const savePositions = (positions) => client.put('/topology/positions', positions)
