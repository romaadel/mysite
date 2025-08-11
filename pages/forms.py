from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms

class RegisterForm(UserCreationForm):
    email = forms.EmailField(label='Email')
    confirm_email = forms.EmailField(label='Confirm Email')
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput(attrs={'class':'form-control'}))
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput(attrs={'class':'form-control'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'confirm_email', 'password1', 'password2']
        labels = {
            'username': 'Username',
        }

    def __init__(self, *args, **kwargs):
        super(RegisterForm, self).__init__(*args, **kwargs)
        # باقي الحقول (بما فيها اللي فوق) هيتضاف لهم الكلاس
        for field_name, field in self.fields.items():
            if field_name not in ['password1', 'password2']:
                field.widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        confirm_email = cleaned_data.get("confirm_email")

        if email and confirm_email and email != confirm_email:
            raise forms.ValidationError("Emails do not match.")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('البريد الإلكتروني مستخدم بالفعل.')
        return cleaned_data




























class CheckoutForm(forms.Form):
    full_name = forms.CharField(max_length=200)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows':3}))
    phone = forms.CharField(max_length=50, required=False)
    note = forms.CharField(widget=forms.Textarea(attrs={'rows':2}), required=False)

