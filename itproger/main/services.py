from django.db import transaction
from .models import UserProfile, Transaction
from decimal import Decimal

def add_eco_points(user_profile, amount, description="Нарахування за вторсировину", partner=None):
    if amount <= 0:
        raise ValueError("Сума нарахування має бути більшою за нуль.")

    with transaction.atomic():
        user_profile.balance += Decimal(str(amount))
        user_profile.save()

        new_transaction = Transaction.objects.create(
            user=user_profile,
            partner=partner,
            amount=amount,
            transaction_type='EARN',
            description=description
        )
        
    return new_transaction

def spend_eco_points(user_profile, amount, description="Витрата на купон"):
    amount_decimal = Decimal(str(amount))
    
    if amount_decimal <= 0:
        raise ValueError("Сума списання має бути більшою за нуль.")

    with transaction.atomic():
        
        
        locked_profile = UserProfile.objects.select_for_update().get(id=user_profile.id)
        
        
        if locked_profile.balance < amount_decimal:
            raise ValueError("Недостатньо еко-балів на балансі для цієї операції.")
        
        
        locked_profile.balance -= amount_decimal
        locked_profile.save()

        
        new_transaction = Transaction.objects.create(
            user=locked_profile,
            amount=amount_decimal,
            transaction_type='SPEND',
            description=description
        )
        
    return new_transaction