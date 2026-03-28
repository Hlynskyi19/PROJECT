import re  # Обов'язково додаємо імпорт для пошуку літер і цифр
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile

class CustomRegisterForm(UserCreationForm):
    # Додаємо поле email
    email = forms.EmailField(required=True, label='Електронна пошта')

    class Meta:
        model = User
        fields = ['username', 'email']

    def __init__(self, *args, **kwargs):
        super(CustomRegisterForm, self).__init__(*args, **kwargs)
        
        # Додаємо стилі Bootstrap і прибираємо стандартні підказки
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control',
                'placeholder': ' '
            })
            field.help_text = ''

    # Наша власна перевірка пароля (замість стандартної Django)
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password1")

        # Якщо пароль введено, перевіряємо його за нашими трьома правилами
        if password:
            errors = []
            
            # 1. Перевірка на 8 символів
            if len(password) < 8:
                errors.append("Мінімум 8 символів.")
                
            # 2. Перевірка на велику літеру (шукаємо англійські або українські)
            if not re.search(r'[A-ZА-ЯІЇЄҐ]', password):
                errors.append("Принаймні одна велика літера (A-Z).")
                
            # 3. Перевірка на цифру
            if not re.search(r'\d', password):
                errors.append("Принаймні одна цифра (0-9).")

            # Якщо є помилки, прив'язуємо їх до поля password1, щоб вони вивелися під ним
            if errors:
                for error in errors:
                    self.add_error('password1', error)

        return cleaned_data

    from .models import UserProfile # Обов'язково імпортуй свою модель профілю зверху файлу!

# Форма для стандартних даних (Ім'я, Прізвище, Email)
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

# Форма для додаткових даних (Телефон, Дата народження)
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