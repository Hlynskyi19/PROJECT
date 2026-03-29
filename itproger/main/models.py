from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

# 1. Типи відходів (Пластик, Скло, Папір тощо)
class WasteType(models.Model):
    name = models.CharField('Тип відходів', max_length=50)

    def __str__(self):
        return self.name

# 2. Пункти прийому
class RecyclingPoint(models.Model):
    name = models.CharField('Назва пункту', max_length=100)
    address = models.CharField('Адреса', max_length=200)
    latitude = models.FloatField('Широта')
    longitude = models.FloatField('Довгота')
    waste_types = models.ManyToManyField(WasteType, verbose_name='Що приймають')
    description = models.TextField('Опис та години роботи', blank=True)

    def __str__(self):
        return self.name

# 3. Профіль користувача (розширюємо стандартного User для зберігання балів)
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField('Баланс еко-балів', max_digits=10, decimal_places=2, default=0.00)

    is_partner = models.BooleanField(default=False, verbose_name="Це акаунт пункту прийому (Партнер)?")
    is_store = models.BooleanField(default=False, verbose_name='Магазин-партнер')

    phone_number = models.CharField('Номер телефону', max_length=20, blank=True, null=True)
    birth_date = models.DateField('Дата народження', blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.balance} балів"

# 4. Історія нарахування/списання балів
class Transaction(models.Model):
    TYPES = (
        ('EARN', 'Нарахування'),
        ('SPEND', 'Списання'),
    )
    transaction_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    amount = models.DecimalField('Кількість балів', max_digits=8, decimal_places=2)
    transaction_type = models.CharField('Тип', max_length=10, choices=TYPES)
    description = models.CharField('Опис (за що)', max_length=255)
    created_at = models.DateTimeField('Дата', auto_now_add=True)
    partner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='issued_transactions', verbose_name='Хто видав (Пункт прийому)')

    def __str__(self):
        return f"{self.get_transaction_type_display()} | {self.amount} | {self.user.user.username}"

class Review(models.Model):
    point = models.ForeignKey(RecyclingPoint, on_delete=models.CASCADE, related_name='reviews', verbose_name="Пункт прийому")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Користувач")
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Оцінка"
    )
    comment = models.TextField(verbose_name="Коментар")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата створення")

    def __str__(self):
        return f"Відгук від {self.user.username} на {self.point.name}"

class UserReward(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='my_rewards', verbose_name="Користувач")
    reward_name = models.CharField(max_length=255, verbose_name="Назва винагороди")
    promo_code = models.CharField(max_length=20, verbose_name="Унікальний код")
    purchased_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата покупки")
    offer = models.ForeignKey('StoreOffer', on_delete=models.SET_NULL, null=True, blank=True, related_name='purchased_codes', verbose_name='Яка пропозиція')
    is_used = models.BooleanField(default=False, verbose_name='Використано')

    def __str__(self):
        return f"{self.user.username} - {self.promo_code}"

class StoreOffer(models.Model):
    store = models.ForeignKey(User, on_delete=models.CASCADE, related_name='offers', verbose_name='Магазин')
    title = models.CharField(max_length=100, verbose_name='Назва винагороди')
    description = models.TextField(verbose_name='Опис', blank=True, null=True)
    cost = models.IntegerField(verbose_name='Вартість (в балах)')
    is_active = models.BooleanField(default=True, verbose_name='Активно')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.store.username})"