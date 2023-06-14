# This file is part of Coog. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import logging
import binascii
import hmac
import hashlib
import datetime
from collections import OrderedDict

from trytond.i18n import gettext
from trytond.rpc import RPC
from trytond.config import config
from trytond.pool import PoolMeta, Pool
from trytond.transaction import Transaction
from trytond.pyson import Eval
from trytond.exceptions import UserError

from trytond.model import fields

from trytond.modules.account_payment.exceptions import (
    PaymentValidationError, ProcessError)


__all__ = [
    'Group',
    'Journal',
    'ProcessPayment',
    ]


class Payment(metaclass=PoolMeta):
    __name__ = 'account.payment'

    @classmethod
    def process_method_with_group(cls):
        return super().process_method_with_group() + ['paybox']


class Group(metaclass=PoolMeta):
    __name__ = 'account.payment.group'

    logger = logging.getLogger(__name__)

    payment_url = fields.Char('Payment Url', readonly=True,
            states={
                'invisible': Eval('journal_method') != 'paybox',
                }, depends=['journal_method'])
    journal_method = fields.Function(fields.Char('Journal Method'),
            'get_journal_method', searcher='search_journal_method')

    @classmethod
    def __setup__(cls):
        super(Group, cls).__setup__()
        cls.__rpc__.update({
            'reject_payment_group': RPC(readonly=False, instantiate=0),
            'succeed_payment_group': RPC(readonly=False, instantiate=0),
            })

    def get_journal_method(self, name):
        if self.journal:
            return self.journal.process_method

    @classmethod
    def search_journal_method(cls, name, clause):
        return [('journal.process_method',) + tuple(clause[1:])]

    def process_paybox(self):
        pass

    def processing_payment_amount(self):
        return sum([x.amount for x in self.get_payments(state='processing')])

    def generate_paybox_url(self):
        if self.kind != 'receivable':
            raise PaymentValidationError(
                gettext('account_payment_paybox.msg_only_receivable_allowed'))
        self.number = self.generate_paybox_transaction_id()
        if self.processing_payment_amount() > 0:
            self.payment_url = self.paybox_url_builder()
            return self.payment_url
        return None

    def generate_paybox_transaction_id(self, hash_method='md5'):
        identifier = str(self) + str(self.create_date)
        if hash_method:
            method = getattr(hashlib, hash_method)()
            if method:
                method.update(identifier.encode('utf-8'))
                return method.hexdigest()
        return identifier

    def generate_hmac(self, url, config):
        secret = config.get('secret')
        binary_key = binascii.unhexlify(secret)
        return hmac.new(binary_key, url.encode('utf-8'),
            hashlib.sha512).hexdigest().upper()

    def get_paybox_parameters(self, config):
        Company = Pool().get('company.company')
        company = Company(Transaction().context.get('company'))

        parameters = OrderedDict()
        for required_paybox_param in ('PBX_SITE', 'PBX_RANG', 'secret',
                'PBX_IDENTIFIANT', 'PBX_RETOUR', 'payment_url'):
            required_param = config.get(required_paybox_param)
            if required_param is None:
                raise UserError(gettext(
                    'account_payment_paybox.msg_missing_paybox_configuration',
                    required_paybox_param))
        parameters['PBX_SITE'] = config.get('PBX_SITE')
        parameters['PBX_RANG'] = config.get('PBX_RANG')
        parameters['PBX_IDENTIFIANT'] = config.get('PBX_IDENTIFIANT')
        parameters['PBX_TOTAL'] = int(self.processing_payment_amount() * 100)
        parameters['PBX_DEVISE'] = company.currency.numeric_code
        parameters['PBX_CMD'] = self.number
        parameters['PBX_PORTEUR'] = self.payments[0].party.email
        parameters['PBX_RETOUR'] = config.get('PBX_RETOUR')
        parameters['PBX_HASH'] = 'SHA512'
        parameters['PBX_TIME'] = datetime.datetime.now().isoformat()
        parameters['PBX_REPONDRE_A'] = config.get('PBX_REPONDRE_A')
        if config.get('PBX_TYPEPAIEMENT'):
            parameters['PBX_TYPEPAIEMENT'] = config.get('PBX_TYPEPAIEMENT')
        if config.get('PBX_TYPEPAIEMENT'):
            parameters['PBX_TYPECARTE'] = config.get('PBX_TYPECARTE')
        if config.get('PBX_EFFECTUE'):
            parameters['PBX_EFFECTUE'] = config.get('PBX_EFFECTUE')
        if config.get('PBX_REFUSE'):
            parameters['PBX_REFUSE'] = config.get('PBX_REFUSE')
        if config.get('PBX_ANNULE'):
            parameters['PBX_ANNULE'] = config.get('PBX_ANNULE')

        return parameters

    def encode_paybox_url_parameters(self, parameters):
        return parameters

    def paybox_url_builder(self):
        config = self.journal.get_paybox_config()
        main_url = config.get('payment_url')
        parameters = self.get_paybox_parameters(config)

        valid_values = [(key, value) for key, value in parameters.items()
            if value is not None]
        get_url_part = '&'.join(['%s=%s' % (var_name, value) for
                var_name, value in valid_values])
        pbx_hmac = ('PBX_HMAC=%s' % self.generate_hmac(get_url_part,
                config))

        encoded_params = self.encode_paybox_url_parameters(OrderedDict(valid_values))
        url_encoded_params = '&'.join(['%s=%s' % name_var for
                name_var in encoded_params.items()])
        final_url = '%s?%s&%s' % (main_url, url_encoded_params, pbx_hmac)
        return final_url

    def get_payments(self, state=None):
        Payment = Pool().get('account.payment')
        condition = [('group', '=', self.id)]
        if state:
            condition.append(('state', '=', state))
        return Payment.search(condition)

    @classmethod
    def update_payments(cls, groups, method_name, state=None):
        Payment = Pool().get('account.payment')
        method = getattr(Payment, method_name)
        method(sum([list(x.get_payments(state)) for x in groups], []))

    @classmethod
    def reject_payment_group(cls, groups, *args):
        Group = Pool().get('account.payment.group')
        Group.update_payments(groups, 'fail')

    @classmethod
    def succeed_payment_group(cls, groups, *args):
        Group = Pool().get('account.payment.group')
        Group.update_payments(groups, 'succeed')


class Journal(metaclass=PoolMeta):
    __name__ = 'account.payment.journal'

    @classmethod
    def __setup__(cls):
        super(Journal, cls).__setup__()
        sepa_method = ('paybox', 'Paybox')
        if sepa_method not in cls.process_method.selection:
            cls.process_method.selection.append(sepa_method)

    def get_paybox_config(self):
        return config['paybox']


class ProcessPayment(metaclass=PoolMeta):
    __name__ = 'account.payment.process'

    def do_process(self, action):
        pool = Pool()
        Payment = pool.get('account.payment')

        action, res = super(ProcessPayment, self).do_process(action)
        payments = Payment.browse(Transaction().context['active_ids'])
        is_paybox = any(p.journal.process_method == 'paybox' for p in payments)
        if res['res_id'] and is_paybox:
            group = Pool().get('account.payment.group')(res['res_id'][0])
            res['paybox_url'] = group.generate_paybox_url()
            if not res['paybox_url']:
                raise ProcessError(
                    gettext('account_payment_paybox.msg_error_url_generation'))
            group.save()
        return action, res
