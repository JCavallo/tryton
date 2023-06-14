const crypto = require('crypto')

const Koa = require('koa')
const logger = require('koa-logger')

const request = require('superagent')
const Session = require('tryton-session')
const model = require('tryton-model')
const qs = require('querystring')

const debug = require('debug')('paybox')
const config = require('./config')

let pubkey

const init = async () => {
  const res = await request.get(config.PEM_URL).buffer()
  debug('init:pem')
  pubkey = Buffer.from(res.text)
}

const verify = async (ctx, next) => {
  debug('verify')
  const query = Object.assign({}, ctx.query)
  ctx.assert(query.signature, 'missing signature')
  const signature = Buffer.from(qs.unescape(query.signature), 'base64')
  delete query.signature
  const buffer = qs.unescape(qs.stringify(query))
  const verifier = crypto.createVerify(config.HASH_METHOD)
  verifier.update(buffer)
  if (verifier.verify(pubkey, signature)) {
    debug('verify:ok')
  } else {
    debug('verify:ko (%j)', ctx.query)
    ctx.throw(403, 'signature check failed')
  }
  await next()
}

const auth = async (ctx, next) => {
  debug('auth:login')
  ctx.tryton = new Session(config.TRYTON_URL, config.TRYTON_DB)
  await ctx.tryton.start(config.TRYTON_USERNAME, {password: config.TRYTON_PASSWORD})
  await next()
  debug('auth:logout')
  var tryton = ctx.tryton
  delete ctx.tryton
  await tryton.stop()
}

const treat = async (ctx) => {
  const {code, number} = ctx.query
  debug('treat:search (%s)', number)
  const payments = await model.Group.search(ctx.tryton,
    'account.payment.group', {
      domain: ['number', '=', number]
    })
  const nb = payments.size()
  debug('treat:found (%s)', nb)
  if (nb !== 1) {
    ctx.throw(500, 'payment search failed')
  }
  const payment = payments.first()
  if (code === '00000') {
    debug('treat:ok')
    const method = 'model.account.payment.group.succeed_payment_group'
    await ctx.tryton.rpc(method, [
      [payment.id]
    ])
  } else {
    debug('treat:ko')
    const method = 'model.account.payment.group.reject_payment_group'
    await ctx.tryton.rpc(method, [
      [payment.id], code
    ])
  }
  ctx.body = 'OK'
}

const main = async () => {
  await model.init(Session)
  await init()

  var app = new Koa()
  app.on('error', function (err) {
    console.error(err)
  })

  app.use(logger())
  app.use(verify)
  app.use(auth)
  app.use(treat)

  app.listen(config.PORT)
  return 'web server started on port ' + config.PORT
}

main().then(console.log, (err) => {
  console.error(err)
  process.exit(1)
})
