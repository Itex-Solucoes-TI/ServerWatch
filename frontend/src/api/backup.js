import client from './client'

export const exportBackup = () => client.get('/backup')
export const importBackup = (data, replace = false) =>
  client.post('/backup', data, { params: { replace } })
