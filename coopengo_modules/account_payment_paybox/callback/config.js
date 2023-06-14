const PREFIX = 'PAYBOX_'

const keys = Object.keys(process.env).filter((k) => k.startsWith(PREFIX))
const vals = keys.map((k) => process.env[k])

const settings = {}
keys.forEach((k, i) => { settings[k.substring(PREFIX.length)] = vals[i] })

const defaults = {
  PORT: 3000,
  TRYTON_URL: 'http://localhost:8000',
  TRYTON_DB: 'coog',
  TRYTON_USERNAME: 'admin',
  TRYTON_PASSWORD: 'admin',
  HASH_METHOD: 'RSA-SHA1',
  PEM_URL: 'http://www1.paybox.com/wp-content/uploads/2014/03/pubkey.pem'
}

module.exports = Object.assign(defaults, settings)
