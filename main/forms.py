from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(max_length=255, required=True)
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')
        
    def __init__(self, *args, **kwargs):
        super(SignUpForm, self).__init__(*args, **kwargs)
        
        self.fields['username'].widget.attrs['help_text'] = '<span class="form-text text-muted"><small>Required. 150 characters or fewer, letters, digits and @/./+/-/_ only.</small></span>'
        
        self.fields['password1'].widget.attrs['help_text'] = '<ul class="form-text text-muted small"><li>Required. Your password cannot be too small. It must contain at least 8 characters.</li><li>Must contain at least one uppercase letter, one lowercase letter, and one number</li></ul>'

        self.fields['password2'].widget.attrs['help_text'] = '<span class="form-text text-muted"><small>Enter the same password as before for verification.</small></span>'