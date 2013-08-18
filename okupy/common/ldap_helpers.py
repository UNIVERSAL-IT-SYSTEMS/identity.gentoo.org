# vim:fileencoding=utf8:et:ts=4:sts=4:sw=4:ft=python

from base64 import b64encode
from Crypto import Random
from passlib.hash import ldap_md5_crypt

from .crypto import cipher
from ..accounts.models import LDAPUser


def get_bound_ldapuser(request, password=None):
    """
    Get LDAPUser with connection bound to the current user.
    Uses either provided password or the secondary password saved
    in session.
    """
    username = request.user.username
    if not password:
        try:
            password = b64encode(cipher.decrypt(
                request.session['secondary_password'], 48))
        except KeyError:
            raise OkupyError('Secondary password not available (no strong auth?)')

    bound_cls = LDAPUser.bind_as(
        alias='ldap_%s' % username,
        username=username,
        password=password,
    )
    return bound_cls.objects.get(username=username)


def set_secondary_password(request, password):
    """ Generate a secondary passsword and encrypt it in the session """
    user = get_bound_ldapuser(request, password)

    secondary_password = Random.get_random_bytes(48)
    request.session['secondary_password'] = cipher.encrypt(secondary_password)
    # Clean up possible leftover secondary passwords from the LDAP account
    if len(user.password) > 1:
        for hash in user.password:
            try:
                if not ldap_md5_crypt.verify(password, hash):
                    user.password.remove(hash)
            except ValueError:
                # don't remove unknown hashes
                pass
    # Add a new generated encrypted password to LDAP
    user.password.append(ldap_md5_crypt.encrypt(b64encode(secondary_password)))
    user.save()


def remove_secondary_password(request):
    """ Remove secondary password on logout """
    try:
        password = b64encode(cipher.decrypt(
            request.session['secondary_password'], 48))
    except KeyError:
        return
    user = get_bound_ldapuser(request, password)

    if len(user.password) > 1:
        for hash in user.password:
            try:
                if ldap_md5_crypt.verify(password, hash):
                    user.password.remove(hash)
            except ValueError:
                # ignore unknown hashes
                pass
    user.save()
