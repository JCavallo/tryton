# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from unittest.mock import MagicMock, patch

from trytond.modules.authentication_saml import routes
from trytond.pool import Pool
from trytond.protocols.wrappers import HTTPStatus
from trytond.tests.test_tryton import (
    DB_NAME, ModuleTestCase, RouteTestCase)


class AuthenticationSamlTestCase(ModuleTestCase):
    "Test Authentication Saml module"
    module = 'authentication_saml'


class AuthenticationSamlRouteTestCase(RouteTestCase):
    "Test Authentication Saml routes"
    module = 'authentication_saml'
    identity = 'test'

    def setUp(self):
        super().setUp()
        client = MagicMock()
        client.parse_authn_request_response.return_value.get_identity\
            .return_value = {'uid': ['admin']}
        for patcher in [
                patch.object(routes, 'get_client', return_value=client),
                patch.dict(routes.LOGIN, {self.identity: 'uid'}),
                patch.object(routes, 'IDENTITIES', {self.identity}),
                ]:
            patcher.start()
            self.addCleanup(patcher.stop)

    def acs(self):
        return self.client().post(
            f'/{self.db_name}/authentication/saml/{self.identity}/acs',
            data={'SAMLResponse': 'response'})

    def test_acs_without_check(self):
        "Test ACS without check_saml_login"
        response = self.acs()
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_acs_check_saml_login(self):
        "Test ACS with check_saml_login"
        User = Pool(DB_NAME).get('res.user')
        for allowed, status in [
                (True, HTTPStatus.FOUND),
                (False, HTTPStatus.FORBIDDEN),
                ]:
            with self.subTest(allowed=allowed), \
                    patch.object(
                        User, 'check_saml_login', create=True,
                        return_value=allowed) as check:
                response = self.acs()
                self.assertEqual(response.status_code, status)
                check.assert_called_once_with(1, self.identity)


del ModuleTestCase, RouteTestCase
