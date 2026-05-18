from django.shortcuts import render, redirect, get_object_or_404
import json
from django.contrib.auth.decorators import login_required
from .models import RecyclingPoint, UserProfile, Review, Transaction, UserReward, StoreOffer
from django.contrib import messages
from .services import spend_eco_points, add_eco_points
import uuid
from django.contrib.auth.models import User
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from .forms import CustomRegisterForm, UserUpdateForm, ProfileUpdateForm

def index(request):
    
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
    
    
    context = {
        'points_json': json.dumps(points_data),
    }

    
    if request.user.is_authenticated:
        
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        context['balance'] = profile.balance

    return render(request, 'main/index.html', context)

def about(request):
    return render(request, 'main/about.html')


def rules(request):
    return render(request, 'main/rules.html')

def register(request):
    
    if request.method == 'POST':
        form = CustomRegisterForm(request.POST)
        if form.is_valid():
            user = form.save() 
            
            
            UserProfile.objects.create(user=user)
            
            
            login(request, user)
            return redirect('home') 
    else:
        
        form = CustomRegisterForm()
        
    return render(request, 'main/register.html', {'form': form})

def point_detail(request, point_id):
    
    point = get_object_or_404(RecyclingPoint, id=point_id)
    
    
    if request.method == 'POST' and request.user.is_authenticated:
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        
        
        if rating and comment:
            Review.objects.create(
                point=point,
                user=request.user,
                rating=rating,
                comment=comment
            )
            return redirect('point_detail', point_id=point.id)
            
    reviews = point.reviews.all().order_by('-created_at')
    
    return render(request, 'main/point_detail.html', {'point': point, 'reviews': reviews})

@login_required
def profile(request):
    user_profile = get_object_or_404(UserProfile, user=request.user)

    if user_profile.is_partner:
        transactions = Transaction.objects.filter(partner=request.user).order_by('-created_at')
    else:
        
        transactions = Transaction.objects.filter(user=user_profile).order_by('-created_at')
        
    
    my_rewards = UserReward.objects.filter(user=request.user).order_by('-purchased_at')

    
    return render(request, 'main/profile.html', {
        'profile': user_profile,
        'transactions': transactions,
        'my_rewards': my_rewards,
    })

@login_required
def rewards(request):
    profile = request.user.userprofile
    
    
    if request.method == 'POST':
        
        offer_id = request.POST.get('offer_id')
        
        try:
            
            offer = get_object_or_404(StoreOffer, id=offer_id)
            
            
            spend_eco_points(profile, offer.cost, f"Придбано: {offer.title}")
            
            
            new_code = uuid.uuid4().hex[:8].upper()
            
            
            UserReward.objects.create(
                user=request.user,
                offer=offer,  
                reward_name=offer.title,
                promo_code=new_code
            )
            
            messages.success(request, f"Ви успішно придбали '{offer.title}'. Ваш код збережено в кабінеті!")
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, "Сталася помилка при обміні балів.")
            
    
    active_offers = StoreOffer.objects.filter(is_active=True).order_by('-created_at')
    
    return render(request, 'main/rewards.html', {
        'balance': profile.balance,
        'offers': active_offers  
    })

@login_required
def partner_panel(request):
    profile = request.user.userprofile
    
    
    if not profile.is_partner:
        messages.error(request, "У вас немає доступу до панелі підприємства.")
        return redirect('home')
        
    if request.method == 'POST':
        target_username = request.POST.get('username')
        points_to_add = int(request.POST.get('points'))
        description = request.POST.get('description', 'Здача вторсировини')
        
        try:
            
            target_user = User.objects.get(username=target_username)
            target_profile = target_user.userprofile
            
            
            add_eco_points(
                target_profile, 
                points_to_add, 
                f"Пункт прийому ({request.user.username}): {description}",
                partner=request.user  
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
        
        if 'update_profile' in request.POST:
            u_form = UserUpdateForm(request.POST, instance=request.user)
            p_form = ProfileUpdateForm(request.POST, instance=request.user.userprofile)
            
            if u_form.is_valid() and p_form.is_valid():
                u_form.save()
                p_form.save()
                messages.success(request, 'Ваші особисті дані успішно оновлено!')
                return redirect('settings') 
                
        
        elif 'change_password' in request.POST:
            pass_form = PasswordChangeForm(request.user, request.POST)
            if pass_form.is_valid():
                user = pass_form.save()
                
                update_session_auth_hash(request, user) 
                messages.success(request, 'Ваш пароль успішно змінено!')
                return redirect('settings')
            else:
                messages.error(request, 'Помилка зміни пароля. Перевірте правильність введення.')

    
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.userprofile)
        pass_form = PasswordChangeForm(request.user)

    
    context = {
        'u_form': u_form,
        'p_form': p_form,
        'pass_form': pass_form
    }
    return render(request, 'main/settings.html', context)

@login_required
def store_panel(request):
    profile = request.user.userprofile
    
    
    if not profile.is_store:
        messages.error(request, "У вас немає доступу до панелі партнера-магазину.")
        return redirect('home')
        
    
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
        
    
    my_offers = StoreOffer.objects.filter(store=request.user).order_by('-created_at')
    
    
    purchased_codes = UserReward.objects.filter(offer__store=request.user).order_by('-purchased_at')
    
    return render(request, 'main/store_panel.html', {
        'my_offers': my_offers,
        'purchased_codes': purchased_codes
    })

@login_required
def delete_offer(request, offer_id):
    
    if request.method == 'POST':
        
        offer = get_object_or_404(StoreOffer, id=offer_id, store=request.user)
        title = offer.title
        offer.delete()
        messages.success(request, f"Пропозицію '{title}' успішно видалено.")
        
    return redirect('store_panel')