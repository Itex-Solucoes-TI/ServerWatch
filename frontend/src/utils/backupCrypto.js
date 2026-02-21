const MAGIC = 'SWENC1'
const PBKDF2_ITERATIONS = 120000
const KEY_LENGTH = 256
const IV_LENGTH = 12
const SALT_LENGTH = 16

function b64enc(b) {
  return btoa(String.fromCharCode(...new Uint8Array(b)))
}

function b64dec(s) {
  return Uint8Array.from(atob(s), (c) => c.charCodeAt(0))
}

async function deriveKey(password, salt) {
  const enc = new TextEncoder()
  const keyMaterial = await crypto.subtle.importKey(
    'raw',
    enc.encode(password),
    'PBKDF2',
    false,
    ['deriveBits']
  )
  const bits = await crypto.subtle.deriveBits(
    { name: 'PBKDF2', salt, iterations: PBKDF2_ITERATIONS, hash: 'SHA-256' },
    keyMaterial,
    KEY_LENGTH
  )
  return crypto.subtle.importKey('raw', bits, { name: 'AES-GCM' }, false, ['encrypt', 'decrypt'])
}

export async function encryptBackup(data, password) {
  const salt = crypto.getRandomValues(new Uint8Array(SALT_LENGTH))
  const iv = crypto.getRandomValues(new Uint8Array(IV_LENGTH))
  const key = await deriveKey(password, salt)
  const enc = new TextEncoder()
  const ciphertext = await crypto.subtle.encrypt(
    { name: 'AES-GCM', iv },
    key,
    enc.encode(JSON.stringify(data))
  )
  return JSON.stringify({
    _magic: MAGIC,
    salt: b64enc(salt),
    iv: b64enc(iv),
    data: b64enc(ciphertext),
  })
}

export async function decryptBackup(encryptedStr, password) {
  const parsed = JSON.parse(encryptedStr)
  if (parsed._magic !== MAGIC) throw new Error('Arquivo não é um backup criptografado')
  const salt = b64dec(parsed.salt)
  const iv = b64dec(parsed.iv)
  const ciphertext = b64dec(parsed.data)
  const key = await deriveKey(password, salt)
  const decrypted = await crypto.subtle.decrypt(
    { name: 'AES-GCM', iv },
    key,
    ciphertext
  )
  return JSON.parse(new TextDecoder().decode(decrypted))
}

export function isEncryptedBackup(str) {
  try {
    const p = JSON.parse(str)
    return p && p._magic === MAGIC
  } catch {
    return false
  }
}
