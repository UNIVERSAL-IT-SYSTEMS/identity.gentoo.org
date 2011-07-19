from django import forms
from django.forms import ModelForm

class PasswordForm(forms.Form):
    old_password = forms.CharField(max_length = 30, widget = forms.PasswordInput(), label = 'Old password:')
    password1 = forms.CharField(max_length = 30, widget = forms.PasswordInput(), label = 'New Password:')
    password2 = forms.CharField(max_length = 30, widget = forms.PasswordInput(), label = 'Verify Password:')

def profileExclude(privil):
    '''
    Helper function to generate a tuple with attributes that should
    be excluded from the edit form
    '''
    exclude = ['user', 'mail', 'secondary_password', 'base_dn']
    if not privil:
        exclude.append('objectClass')
        for key in settings.LDAP_ACL_GROUPS.keys():
            exclude.append(key)
    return tuple(exclude)

'''
Below are the forms generated by the above models
'''

class UserProfileForm(ModelForm):
    '''
    UserProfile form for unprivileged users
    Some fields are hidden
    '''
    class Meta:
        model = UserProfile
        exclude = profileExclude(False)

class UserProfileForm(ModelForm):
    '''
    UserProfile form for privileged users
    All fields are available
    '''
    class Meta:
        model = UserProfile
        exclude = profileExclude(True)

class GentooProfileForm(ModelForm):
    '''
    GentooProfile form for unprivileged users
    Many fields are hidden
    '''
    class Meta:
        model = GentooProfile
        exclude = profileExclude(False)

class GentooProfilePrivilForm(ModelForm):
    '''
    GentooProfile form for privileged users
    All the fields are available
    '''
    class Meta:
        model = GentooProfile
        exclude = profileExclude(True)
