import client from './client'

export const listContainers = (serverId) => client.get(`/docker/servers/${serverId}/containers`)
export const syncServer = (serverId) => client.post(`/docker/servers/${serverId}/sync`)
export const startContainer = (serverId, containerId) => client.post(`/docker/servers/${serverId}/containers/${containerId}/start`)
export const stopContainer = (serverId, containerId) => client.post(`/docker/servers/${serverId}/containers/${containerId}/stop`)
export const restartContainer = (serverId, containerId) => client.post(`/docker/servers/${serverId}/containers/${containerId}/restart`)
export const removeContainer = (serverId, containerId, force = false) =>
  client.delete(`/docker/servers/${serverId}/containers/${containerId}`, { params: { force } })
