from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import Car, Service, ServiceStation, User


class RegistrationForm(forms.ModelForm):
    """Форма реєстрації нового користувача (клієнта або СТО)."""

    password = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['full_name', 'phone', 'email', 'role']

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()

    def clean_password2(self):
        password = self.cleaned_data.get('password')
        password2 = self.cleaned_data['password2']
        if password and password != password2:
            raise forms.ValidationError('Паролі не збігаються.')
        return password2

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        if password and not self.has_error('password2'):
            user = User(
                email=cleaned_data.get('email', ''),
                full_name=cleaned_data.get('full_name', ''),
                phone=cleaned_data.get('phone', ''),
                role=cleaned_data.get('role', ''),
            )
            try:
                validate_password(password, user)
            except ValidationError as error:
                self.add_error('password', error)
        return cleaned_data


class ProfileForm(forms.ModelForm):
    """Форма редагування контактних даних профілю."""

    class Meta:
        model = User
        fields = ['full_name', 'phone']


class CarForm(forms.ModelForm):
    """Форма додавання або редагування автомобіля клієнта."""

    class Meta:
        model = Car
        fields = ['vin_code', 'brand', 'model', 'year']

    def clean_vin_code(self):
        return self.cleaned_data['vin_code'].strip().upper()


class StationForm(forms.ModelForm):
    """Форма налаштування станції технічного обслуговування."""

    class Meta:
        model = ServiceStation
        fields = ['name', 'city', 'address', 'phone', 'latitude', 'longitude']

    def clean(self):
        cleaned_data = super().clean()
        latitude, longitude = cleaned_data.get('latitude'), cleaned_data.get('longitude')
        if (latitude is None) != (longitude is None):
            raise forms.ValidationError('Вкажіть обидві координати або залиште обидва поля порожніми.')
        return cleaned_data


class ServiceForm(forms.ModelForm):
    """Форма додавання послуги та її вартості."""

    class Meta:
        model = Service
        fields = ['service_name', 'price', 'description']
