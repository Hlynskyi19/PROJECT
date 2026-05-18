import re  
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile

class CustomRegisterForm(UserCreationForm):
    
    email = forms.EmailField(required=True, label='Електронна пошта')

    class Meta:
        model = User
        fields = ['username', 'email']

    def __init__(self, *args, **kwargs):
        super(CustomRegisterForm, self).__init__(*args, **kwargs)
        
        
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control',
                'placeholder': ' '
            })
            field.help_text = ''

    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password1")

        
        if password:
            errors = []
            
            
            if len(password) < 8:
                errors.append("Мінімум 8 символів.")
                
            
            if not re.search(r'[A-ZА-ЯІЇЄҐ]', password):
                errors.append("Принаймні одна велика літера (A-Z).")
                
            
            if not re.search(r'\d', password):
                errors.append("Принаймні одна цифра (0-9).")

            
            if errors:
                for error in errors:
                    self.add_error('password1', error)

        return cleaned_data

    from .models import UserProfile 


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True, label='Електронна пошта')
    first_name = forms.CharField(required=False, label="Ім'я")
    last_name = forms.CharField(required=False, label="Прізвище")

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control', 'placeholder': ' '})


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['phone_number', 'birth_date']
        widgets = {
            'birth_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control', 'placeholder': ' '})