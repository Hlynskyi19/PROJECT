from django.shortcuts import render
import json
from django.contrib.auth.decorators import login_required
from .models import RecyclingPoint, UserProfile, Review, Transaction, UserReward, StoreOffer
from django.contrib import messages
from .services import spend_eco_points
import uuid
from django.contrib.auth.models import User
from .services import spend_eco_points, add_eco_points
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from .forms import CustomRegisterForm, UserUpdateForm, ProfileUpdateForm

def index(request):
    # 1. Отримуємо всі пункти прийому з БД
    points = RecyclingPoint.objects.all()
    points_data = []
    
    for point in points:
        points_data.append({
            'id': point.id,
            'name': point.name,
            'lat': point.latitude,
            'lon': point.longitude,
            'address': point.address
        })
    
    # 2. Готуємо базовий контекст для шаблону
    context = {
        'points_json': json.dumps(points_data),
    }

    # 3. Якщо користувач увійшов у систему, дістаємо його баланс
    if request.user.is_authenticated:
        # get_or_create гарантує, що якщо профілю ще немає, він створиться без помилки
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        context['balance'] = profile.balance

    return render(request, 'main/index.html', context)

def about(request):
    return render(request, 'main/about.html')

from django.contrib.auth import login
from django.shortcuts import redirect

def register(request):
    # Якщо користувач відправив форму з даними
    if request.method == 'POST':
        form = CustomRegisterForm(request.POST)
        if form.is_valid():
            user = form.save() # Зберігаємо стандартного користувача
            
            # ВАЖЛИВО: Одразу створюємо йому гаманець для еко-балів
            UserProfile.objects.create(user=user)
            
            # Автоматично логінимо після успішної реєстрації
            login(request, user)
            return redirect('home') # Перекидаємо на головну сторінку
    else:
        # Якщо користувач просто зайшов на сторінку, показуємо порожню форму
        form = CustomRegisterForm()
        
    return render(request, 'main/register.html', {'form': form})

from django.shortcuts import render, redirect, get_object_or_404
from .models import RecyclingPoint, UserProfile, Review # Додали імпорт Review

def point_detail(request, point_id):
    # Шукаємо пункт за ID, якщо не знайдено — видасть помилку 404
    point = get_object_or_404(RecyclingPoint, id=point_id)
    
    # Якщо користувач відправив форму відгуку
    if request.method == 'POST' and request.user.is_authenticated:
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        
        # Створюємо новий відгук у базі
        if rating and comment:
            Review.objects.create(
                point=point,
                user=request.user,
                rating=rating,
                comment=comment
            )
            return redirect('point_detail', point_id=point.id)
            
    # Дістаємо всі відгуки для цього пункту (нові зверху)
    reviews = point.reviews.all().order_by('-created_at')
    
    return render(request, 'main/point_detail.html', {'point': point, 'reviews': reviews})

@login_required
def profile(request):
    user_profile = get_object_or_404(UserProfile, user=request.user)

    if user_profile.is_partner:
        # Для пункту прийому все правильно (партнер прив'язаний до User)
        transactions = Transaction.objects.filter(partner=request.user).order_by('-created_at')
    else:
        # ВИПРАВЛЕНО ТУТ: Шукаємо по user_profile, а не по request.user!
        transactions = Transaction.objects.filter(user=user_profile).order_by('-created_at')
        
    # Дістаємо всі куплені промокоди користувача
    my_rewards = UserReward.objects.filter(user=request.user).order_by('-purchased_at')

    # 3. Передаємо все у шаблон
    return render(request, 'main/profile.html', {
        'profile': user_profile,
        'transactions': transactions,
        'my_rewards': my_rewards,
    })

@login_required
def rewards(request):
    profile = request.user.userprofile
    
    # Якщо користувач натиснув кнопку "Обміняти"
    if request.method == 'POST':
        # Отримуємо ID пропозиції, яку хоче купити користувач
        offer_id = request.POST.get('offer_id')
        
        try:
            # Знаходимо саму пропозицію в базі
            offer = get_object_or_404(StoreOffer, id=offer_id)
            
            # Списуємо бали (вартість беремо з бази даних!)
            spend_eco_points(profile, offer.cost, f"Придбано: {offer.title}")
            
            # Генеруємо унікальний промокод (8 випадкових символів)
            new_code = uuid.uuid4().hex[:8].upper()
            
            # Зберігаємо покупку і ПРИВ'ЯЗУЄМО її до конкретної пропозиції (offer=offer)
            UserReward.objects.create(
                user=request.user,
                offer=offer,  # <--- Цей рядок передасть промокод у панель магазину
                reward_name=offer.title,
                promo_code=new_code
            )
            
            messages.success(request, f"Ви успішно придбали '{offer.title}'. Ваш код збережено в кабінеті!")
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, "Сталася помилка при обміні балів.")
            
    # Дістаємо всі АКТИВНІ пропозиції від усіх магазинів
    active_offers = StoreOffer.objects.filter(is_active=True).order_by('-created_at')
    
    return render(request, 'main/rewards.html', {
        'balance': profile.balance,
        'offers': active_offers  # Передаємо їх у шаблон
    })

@login_required
def partner_panel(request):
    profile = request.user.userprofile
    
    # Перевіряємо, чи має цей користувач права підприємства
    if not profile.is_partner:
        messages.error(request, "У вас немає доступу до панелі підприємства.")
        return redirect('home')
        
    if request.method == 'POST':
        target_username = request.POST.get('username')
        points_to_add = int(request.POST.get('points'))
        description = request.POST.get('description', 'Здача вторсировини')
        
        try:
            # Шукаємо клієнта за логіном
            target_user = User.objects.get(username=target_username)
            target_profile = target_user.userprofile
            
            # Нараховуємо бали (ОСЬ ТУТ МИ ДОДАЛИ ПАРТНЕРА)
            add_eco_points(
                target_profile, 
                points_to_add, 
                f"Пункт прийому ({request.user.username}): {description}",
                partner=request.user  # <--- Цей рядок прив'язує транзакцію до пункту прийому
            )
            
            messages.success(request, f"Успішно! Користувачу {target_username} нараховано {points_to_add} балів.")
        except User.DoesNotExist:
            messages.error(request, f"Помилка: Користувача з логіном '{target_username}' не знайдено!")
        except Exception as e:
            messages.error(request, f"Сталася помилка: {str(e)}")
            
        return redirect('partner_panel')
        
    return render(request, 'main/partner_panel.html')

@login_required
def settings_view(request):
    if request.method == 'POST':
        # Якщо натиснули кнопку "Зберегти особисті дані"
        if 'update_profile' in request.POST:
            u_form = UserUpdateForm(request.POST, instance=request.user)
            p_form = ProfileUpdateForm(request.POST, instance=request.user.userprofile)
            
            if u_form.is_valid() and p_form.is_valid():
                u_form.save()
                p_form.save()
                messages.success(request, 'Ваші особисті дані успішно оновлено!')
                return redirect('settings') # Робимо редірект, щоб уникнути повторної відправки
                
        # Якщо натиснули кнопку "Оновити пароль"
        elif 'change_password' in request.POST:
            pass_form = PasswordChangeForm(request.user, request.POST)
            if pass_form.is_valid():
                user = pass_form.save()
                # Це ВАЖЛИВО: не дає системі викинути тебе з акаунта після зміни пароля
                update_session_auth_hash(request, user) 
                messages.success(request, 'Ваш пароль успішно змінено!')
                return redirect('settings')
            else:
                messages.error(request, 'Помилка зміни пароля. Перевірте правильність введення.')

    # Якщо це звичайний перехід на сторінку (GET запит)
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.userprofile)
        pass_form = PasswordChangeForm(request.user)

    # Додаємо всі форми в контекст, щоб їх бачив HTML
    context = {
        'u_form': u_form,
        'p_form': p_form,
        'pass_form': pass_form
    }
    return render(request, 'main/settings.html', context)

@login_required
def store_panel(request):
    profile = request.user.userprofile
    
    # Перевіряємо, чи має користувач права магазину
    if not profile.is_store:
        messages.error(request, "У вас немає доступу до панелі партнера-магазину.")
        return redirect('home')
        
    # Якщо магазин додає нову пропозицію (товар)
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        cost = request.POST.get('cost')
        
        if title and cost:
            StoreOffer.objects.create(
                store=request.user,
                title=title,
                description=description,
                cost=int(cost)
            )
            messages.success(request, f"Пропозицію '{title}' успішно додано до магазину!")
        else:
            messages.error(request, "Будь ласка, заповніть назву та вартість.")
            
        return redirect('store_panel')
        
    # Отримуємо всі пропозиції цього магазину
    my_offers = StoreOffer.objects.filter(store=request.user).order_by('-created_at')
    
    # Отримуємо всі куплені ПРОМОКОДИ на товари САМЕ ЦЬОГО магазину
    purchased_codes = UserReward.objects.filter(offer__store=request.user).order_by('-purchased_at')
    
    return render(request, 'main/store_panel.html', {
        'my_offers': my_offers,
        'purchased_codes': purchased_codes
    })

@login_required
def delete_offer(request, offer_id):
    # Видаляти можна тільки методом POST (це стандарт безпеки, щоб уникнути випадкових видалень через посилання)
    if request.method == 'POST':
        # Шукаємо пропозицію. ВАЖЛИВО: store=request.user гарантує, що чужий магазин не видалить цю пропозицію!
        offer = get_object_or_404(StoreOffer, id=offer_id, store=request.user)
        title = offer.title
        offer.delete()
        messages.success(request, f"Пропозицію '{title}' успішно видалено.")
        
    return redirect('store_panel')