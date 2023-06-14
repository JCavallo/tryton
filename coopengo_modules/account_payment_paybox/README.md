# Account Payment Paybox Module

This module provides a new journal process method to proceed account payments
using the external and secured [paybox](http://www1.paybox.com/?lang=en) platform.
You'll need the tryton 'account_payment' module installed and of course, a valid paybox account
with your credentials and API references.
This new module adds:

- A new section into the tryton server configuration file. (For the API references)
- The possibility to process payments using the paybox method.
- A Payment URL on paybox payment groups to perform the transaction.
- A NodeJS endpoint server to receive Paybox's digitally signed callbacks
  which update as well the payments state into the tryton database.

## The tryton server configuration
First of all, you'll need to set this new section with your API references / credentials
as following: (The API informations below are given by paybox to a sandbox/test account)

```
[paybox]
payment_url = https://preprod-tpeweb.paybox.com/cgi/MYchoix_pagepaiement.cgi
PBX_SITE = 1999888
PBX_RANG = 43
PBX_IDENTIFIANT = 107975626
PBX_RETOUR=number:R;code:E;signature:K
PBX_REPONDRE_A = https://3907fcba.ngrok.io
secret=0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF
```
Once you have filled those variables with your data, the server must be restarted.

## Deploy the NodeJS callback server
All the sources are into the "callback" directory of the account_payment_paybox module

### With docker

build:
```
npm run docker
```

run: 
```
docker run -d
-e PAYBOX_PORT=
-e PAYBOX_TRYTON_URL=
-e PAYBOX_TRYTON_DB=
-e PAYBOX_TRYTON_USERNAME=
-e PAYBOX_TRYTON_PASSWORD=
coopengo/paybox
```

### As a node endpoint

```
cd callback
node .
```

*NB: You may need to run npm i  before run node into the callback directory*

## The Paybox Journal
To create and process payments, you'll need to configure a new payment journal using "Paybox" as process method.


## The paybox payment groups
Once you've created some paybox payments, you can process them and create payment groups.

All these payment groups have a unique URL which is valid for 15 minutes after it's generation. Passing this delay,
you'll need to fail the payment and generate another one.

You can click on the URL of the payment group form view to open up the browser straight on the paybox payment page.
Type your credit card informations and, depending on the transaction state, paybox will call back our NodeJS server
which will update the tryton payment state (If the certificate signature is valid otherwise, the request will be logged
and through away).

Nota: the payment group number is the paybox transaction reference, so you can go to the paybox backoffice with this number
to retrieve the logs of the payment transaction.
If an error occurs during the transaction, the code will be printed in the callback server logs. You can check from the [paybox documentation guide](http://www1.paybox.com/wp-content/uploads/2017/08/ManuelIntegrationVerifone_PayboxSystem_V8.0_EN.pdf) (Page 65) what does this code means.
