# vim:fileencoding=utf8:et:ts=4:sts=4:sw=4:ft=python

from mockldap import MockLdap

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.test import TestCase

from okupy.common.test_helpers import ldap_users, set_request
from okupy.tests import vars

import base64

import paramiko


class AuthSSLUnitTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mockldap = MockLdap(vars.DIRECTORY)

    @classmethod
    def tearDownClass(cls):
        del cls.mockldap

    def setUp(self):
        self.mockldap.start()
        self.ldapobj = self.mockldap[settings.AUTH_LDAP_SERVER_URI]

    def tearDown(self):
        self.mockldap.stop()
        del self.ldapobj

    def test_valid_certificate_authenticates_alice(self):
        request = set_request(uri='/login')
        request.META['SSL_CLIENT_VERIFY'] = 'SUCCESS'
        request.META['SSL_CLIENT_RAW_CERT'] = vars.TEST_CERTIFICATE

        u = authenticate(request=request)
        self.assertEqual(u.username, vars.LOGIN_ALICE['username'])

    def test_second_email_authenticates_alice(self):
        request = set_request(uri='/login')
        request.META['SSL_CLIENT_VERIFY'] = 'SUCCESS'
        request.META['SSL_CLIENT_RAW_CERT'] = (
            vars.TEST_CERTIFICATE_WITH_TWO_EMAIL_ADDRESSES)

        u = authenticate(request=request)
        self.assertEqual(u.username, vars.LOGIN_ALICE['username'])

    def test_no_certificate_returns_none(self):
        request = set_request(uri='/login')
        request.META['SSL_CLIENT_VERIFY'] = 'NONE'

        u = authenticate(request=request)
        self.assertIs(u, None)

    def test_failed_verification_returns_none(self):
        request = set_request(uri='/login')
        request.META['SSL_CLIENT_VERIFY'] = 'FAILURE'
        request.META['SSL_CLIENT_RAW_CERT'] = vars.TEST_CERTIFICATE

        u = authenticate(request=request)
        self.assertIs(u, None)

    def test_unmatched_email_returns_none(self):
        request = set_request(uri='/login')
        request.META['SSL_CLIENT_VERIFY'] = 'SUCCESS'
        request.META['SSL_CLIENT_RAW_CERT'] = vars.TEST_CERTIFICATE_WRONG_EMAIL

        u = authenticate(request=request)
        self.assertIs(u, None)


class AuthSSHUnitTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mockldap = MockLdap(vars.DIRECTORY)

    def setUp(self):
        self.mockldap.start()
        self.ldapobj = self.mockldap[settings.AUTH_LDAP_SERVER_URI]

    def tearDown(self):
        self.mockldap.stop()

    @staticmethod
    def get_ssh_key(person, number=0):
        keystr = person['sshPublicKey'][number]
        return base64.b64decode(keystr.split()[1])

    def test_valid_rsa_ssh_key_authenticates_alice(self):
        dn, alice = ldap_users('alice')
        key = paramiko.RSAKey(data=self.get_ssh_key(alice))
        u = authenticate(ssh_key=key)
        self.assertEqual(u.username, alice['uid'][0])

    def test_valid_dss_ssh_key_authenticates_bob(self):
        dn, bob = ldap_users('bob')
        key = paramiko.DSSKey(data=self.get_ssh_key(bob, 1))
        u = authenticate(ssh_key=key)
        self.assertEqual(u.username, bob['uid'][0])

    def test_valid_rsa_key_with_comment_authenticates_bob(self):
        dn, bob = ldap_users('bob')
        key = paramiko.RSAKey(data=self.get_ssh_key(bob))
        u = authenticate(ssh_key=key)
        self.assertEqual(u.username, bob['uid'][0])

    def test_unknown_ssh_key_returns_none(self):
        key = paramiko.RSAKey(
            data=base64.b64decode(vars.TEST_SSH_KEY_FOR_NO_USER))
        u = authenticate(ssh_key=key)
        self.assertIs(u, None)


class AuthLDAPUnitTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mockldap = MockLdap(vars.DIRECTORY)

    @classmethod
    def tearDownClass(cls):
        del cls.mockldap

    def setUp(self):
        self.mockldap.start()
        self.ldapobj = self.mockldap[settings.AUTH_LDAP_SERVER_URI]
        self.request = set_request(uri='/login')

    def tearDown(self):
        self.mockldap.stop()
        del self.ldapobj

    def test_successful_login(self):
        user = authenticate(request=self.request,
                            username='alice', password='ldaptest')
        self.assertTrue(user.username, 'alice')

    def test_successful_login_lowercase(self):
        user = authenticate(request=self.request,
                            username='Alice', password='ldaptest')
        self.assertTrue(user.username, 'alice')

    def test_successful_login_trailing_whitespace(self):
        user = authenticate(request=self.request,
                            username='alice ', password='ldaptest')
        self.assertTrue(user.username, 'alice')

    def test_successful_login_leading_whitespace(self):
        user = authenticate(request=self.request,
                            username=' alice', password='ldaptest')
        self.assertTrue(user.username, 'alice')

    def test_failed_login_wrong_password(self):
        user = authenticate(request=self.request,
                            username='alice', password='ldaptest1')
        self.assertIs(user, None)

    def test_failed_login_wrong_username(self):
        user = authenticate(request=self.request,
                            username='wrong', password='ldaptest')
        self.assertIs(user, None)

    def test_add_user_in_db(self):
        authenticate(request=self.request,
                     username='alice', password='ldaptest')
        self.assertEqual(User.objects.count(), 1)

    def test_successful_login_existing_user(self):
        User.objects.create(username='alice')
        user = authenticate(request=self.request,
                            username='alice', password='ldaptest')
        self.assertTrue(user is not None)
        self.assertEqual(User.objects.count(), 1)

    def test_successful_login_existing_user_insensitive(self):
        User.objects.create(username='alice')
        user = authenticate(request=self.request,
                            username='Alice', password='ldaptest')
        self.assertTrue(user.username, 'alice')

    def test_successful_login_insensitive(self):
        user = authenticate(request=self.request,
                            username='Alice', password='ldaptest')
        self.assertTrue(user.username, 'alice')
