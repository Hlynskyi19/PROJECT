from django.db import transaction
from .models import UserProfile, Transaction
from decimal import Decimal

def add_eco_points(user_profile, amount, description="Нарахування за вторсировину", partner=None):
    """
    Безпечне нарахування балів з використанням транзакцій БД.
    Якщо хоча б один етап (збереження балансу або створення запису) 
    завершиться з помилкою, жодних змін у базі не відбудеться.
    """
    if amount <= 0:
        raise ValueError("Сума нарахування має бути більшою за нуль.")

    # transaction.atomic() гарантує, що весь блок виконається як одна дія
    with transaction.atomic():
        # 1. Оновлюємо баланс користувача
        user_profile.balance += Decimal(str(amount))
        user_profile.save()

        # 2. Створюємо запис в історії транзакцій
        new_transaction = Transaction.objects.create(
            user=user_profile,
            partner=partner,       # <--- ОСЬ ВІН, НАШ ПАРТНЕР!
            amount=amount,
            transaction_type='EARN',
            description=description
        )
        
    return new_transaction

def spend_eco_points(user_profile, amount, description="Витрата на купон"):
    """
    Безпечне списання балів з перевіркою балансу та блокуванням від подвійного списання (Race Condition).
    """
    amount_decimal = Decimal(str(amount))
    
    if amount_decimal <= 0:
        raise ValueError("Сума списання має бути більшою за нуль.")

    with transaction.atomic():
        # Блокуємо профіль у БД для цього запиту, щоб інші запити чекали
        # Це рятує від "подвійного списання", якщо користувач швидко клікає кнопку
        locked_profile = UserProfile.objects.select_for_update().get(id=user_profile.id)
        
        # Перевіряємо, чи вистачає балів
        if locked_profile.balance < amount_decimal:
            raise ValueError("Недостатньо еко-балів на балансі для цієї операції.")
        
        # 1. Віднімаємо бали
        locked_profile.balance -= amount_decimal
        locked_profile.save()

        # 2. Записуємо в історію транзакцій
        new_transaction = Transaction.objects.create(
            user=locked_profile,
            amount=amount_decimal,
            transaction_type='SPEND',
            description=description
        )
        
    return new_transaction