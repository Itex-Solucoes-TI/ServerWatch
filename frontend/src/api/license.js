import client from './client'

export const status = () => client.get('/license/status')

export const activate = (token) =>
  client.post('/license/activate', { token })

export const remove = () => client.delete('/license/')
