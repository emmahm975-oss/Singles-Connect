import random
import string
import requests
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse
from django.contrib.admin.views.decorators import staff_member_required
from .models import Profile, Connection, CheckoutSession, Message, SuccessStory, BlockedUser
from .utils import get_local_amount

def generate_ref():
    return 'SC' + ''.join(random.choices(string.digits, k=4))

def home(request):
    stories = SuccessStory.objects.all().order_by('-created_at')[:3]
    return render(request, 'core/home.html', {'success_stories': stories})

def register(request):
    if request.method == 'POST':
        try:
            username = request.POST['username']
            email = request.POST['email']
            password = request.POST['password']
            full_name = request.POST['full_name']
            phone = request.POST.get('phone', '')
            age = request.POST['age']
            gender = request.POST['gender']
            country = request.POST['country']
            city = request.POST['city']
            
            pref_gender = request.POST.get('pref_gender', 'F')
            pref_min_age = request.POST.get('pref_min_age', 18)
            pref_max_age = request.POST.get('pref_max_age', 40)
            pref_country = request.POST.get('pref_country', '')

            if User.objects.filter(username=username).exists():
                return render(request, 'core/register.html', {'error': 'Username is already taken.'})

            user = User.objects.create_user(username=username, email=email, password=password)
            Profile.objects.create(
                user=user, full_name=full_name, phone=phone, age=age, 
                gender=gender, country=country, city=city,
                pref_gender=pref_gender, pref_min_age=pref_min_age, 
                pref_max_age=pref_max_age, pref_country=pref_country
            )
            login(request, user)
            return redirect('dashboard')
            
        except Exception as e:
            return render(request, 'core/register.html', {'error': str(e)})

    return render(request, 'core/register.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'core/login.html', {'error': 'Invalid username or password.'})
            
    return render(request, 'core/login.html')

def logout_view(request):
    logout(request)
    return redirect('home')

@login_required
def dashboard(request):
    # Safely get or create a profile for the superuser
    try:
        user_profile = request.user.profile
    except Profile.DoesNotExist:
        user_profile = Profile.objects.create(
            user=request.user,
            full_name=request.user.username.title(),
            age=30,
            gender='M',
            country='Kenya',
            city='Nairobi'
        )
    
    matches = Profile.objects.exclude(user=request.user)
    matches = matches.filter(gender=user_profile.pref_gender)
    # ... (keep the rest of the dashboard code exactly as it is) ...
    
@login_required
def discover(request):
    profiles = Profile.objects.exclude(user=request.user)
    return render(request, 'core/discover.html', {'profiles': profiles})

@login_required
def profile_edit(request):
    if request.method == 'POST':
        profile = request.user.profile
        if 'profile_photo' in request.FILES:
            import cloudinary.uploader
            upload_result = cloudinary.uploader.upload(request.FILES['profile_photo'])
            profile.profile_photo = upload_result['secure_url']
            
        profile.occupation = request.POST.get('occupation', '')
        profile.bio = request.POST.get('bio', '')
        profile.save()
        return redirect('dashboard')
        
    return render(request, 'core/profile_edit.html')
    
@login_required
def send_connection(request, user_id):
    receiver = User.objects.get(id=user_id)
    member = request.user
    
    checkout = CheckoutSession.objects.filter(
        member=member, receiver=receiver, 
        status__in=['pending_admin', 'pending_payment', 'pending_verification']
    ).first()
    
    if not checkout:
        currency, symbol, amount = get_local_amount(member.profile.country)
        
        checkout = CheckoutSession.objects.create(
            member=member, receiver=receiver, reference=generate_ref(),
            country=member.profile.country, currency=currency, amount=amount
        )
        
        bot_token = settings.TELEGRAM_BOT_TOKEN
        chat_id = settings.TELEGRAM_ADMIN_CHAT_ID
        
        message = (
            f"🚨 *NEW CHECKOUT REQUEST*\n\n"
            f"*Member:* {member.profile.full_name}\n"
            f"*Reg ID:* SC-{member.id}\n"
            f"*Country:* {checkout.country}\n"
            f"*Currency:* {currency}\n"
            f"*Amount:* {symbol} {amount}\n"
            f"*Reference:* {checkout.reference}\n\n"
            f"*Action Required:* Please send payment details for this checkout."
        )
        
        reply_markup = {
            "inline_keyboard": [
                [{"text": "💳 Send Payment Details", "callback_data": f"send_details_{checkout.id}"}]
            ]
        }
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "reply_markup": reply_markup
        }
        requests.post(url, json=payload)
    
    return redirect('checkout_page', checkout_id=checkout.id)

@login_required
def checkout_page(request, checkout_id):
    checkout = get_object_or_404(CheckoutSession, id=checkout_id, member=request.user)
    
    connection = None
    if checkout.status == 'approved':
        connection, created = Connection.objects.get_or_create(
            sender=checkout.member, 
            receiver=checkout.receiver, 
            defaults={'status': 'accepted'}
        )
        
    return render(request, 'core/checkout.html', {
        'checkout': checkout, 
        'matched_profile': checkout.receiver.profile,
        'connection': connection
    })

@login_required
def submit_evidence(request, checkout_id):
    checkout = get_object_or_404(CheckoutSession, id=checkout_id, member=request.user)
    
    if request.method == 'POST':
        checkout.evidence_text = request.POST.get('evidence_text', '')
        
        if 'evidence_screenshot' in request.FILES:
            checkout.evidence_screenshot = request.FILES['evidence_screenshot']
            
        checkout.status = 'pending_verification'
        checkout.save()
        
        bot_token = settings.TELEGRAM_BOT_TOKEN
        chat_id = settings.TELEGRAM_ADMIN_CHAT_ID
        
        message = (
            f"📄 *NEW PAYMENT SUBMISSION*\n\n"
            f"*Member:* {checkout.member.profile.full_name}\n"
            f"*Reference:* {checkout.reference}\n"
            f"*Amount:* {checkout.amount} {checkout.currency}\n\n"
            f"*Pasted Message:*\n{checkout.evidence_text}\n\n"
            f"Please check the website or Telegram to Approve/Reject."
        )
        
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "✅ Approve Payment", "callback_data": f"approve_{checkout.id}"},
                    {"text": "❌ Reject Payment", "callback_data": f"reject_{checkout.id}"}
                ]
            ]
        }
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "reply_markup": reply_markup
        }
        requests.post(url, json=payload)
        
        messages.success(request, "Payment evidence submitted! Waiting for admin verification.")
        return redirect('checkout_page', checkout_id=checkout.id)
        
    return render(request, 'core/checkout.html', {'checkout': checkout})

@login_required
def accept_connection(request, connection_id):
    connection = Connection.objects.get(id=connection_id)
    if connection.receiver == request.user:
        connection.status = 'accepted'
        connection.save()
        messages.success(request, f"You are now connected with {connection.sender.profile.full_name}!")
    return redirect('dashboard')

@login_required
def chat_view(request, connection_id):
    connection = get_object_or_404(Connection, id=connection_id)
    
    if request.user != connection.sender and request.user != connection.receiver:
        return redirect('dashboard')
        
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            Message.objects.create(connection=connection, sender=request.user, content=content)
            return redirect('chat_view', connection_id=connection.id)

    messages_list = connection.messages.all().order_by('timestamp')
    other_user = connection.receiver if request.user == connection.sender else connection.sender

    return render(request, 'core/chat.html', {
        'connection': connection,
        'messages': messages_list,
        'other_user': other_user
    })

@login_required
def retry_checkout(request, checkout_id):
    checkout = get_object_or_404(CheckoutSession, id=checkout_id, member=request.user)
    if checkout.status == 'rejected':
        checkout.status = 'pending_payment'
        checkout.save()
    return redirect('checkout_page', checkout_id=checkout.id)

@login_required
def delete_checkout(request, checkout_id):
    checkout = get_object_or_404(CheckoutSession, id=checkout_id, member=request.user)
    if checkout.status != 'approved':
        checkout.delete()
        messages.success(request, "Payment record deleted.")
    else:
        messages.error(request, "You cannot delete an approved payment record.")
    return redirect('dashboard')

def success_stories(request):
    stories = SuccessStory.objects.all().order_by('-created_at')
    return render(request, 'core/success_stories.html', {'stories': stories})

@login_required
def block_user(request, user_id):
    user_to_block = User.objects.get(id=user_id)
    BlockedUser.objects.get_or_create(blocker=request.user, blocked=user_to_block)
    messages.success(request, f"You have successfully blocked {user_to_block.profile.full_name}.")
    return redirect('dashboard')

def password_reset_request(request):
    if request.method == "POST":
        email = request.POST.get('email')
        users = User.objects.filter(email=email)
        
        if users.exists():
            for user in users:
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                
                reset_url = request.build_absolute_uri(
                    reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
                )
                
                configuration = sib_api_v3_sdk.Configuration()
                configuration.api_key['api-key'] = settings.BREVO_API_KEY
                
                api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
                
                subject = "Password Reset - Singles Connect"
                html_content = f"<p>Click the link below to reset your password:</p><p><a href='{reset_url}'>{reset_url}</a></p><p>If you didn't request this, ignore this email.</p>"
                
                sender = {"name": "Singles Connect", "email": settings.DEFAULT_FROM_EMAIL}
                to = [{"email": email}]
                
                send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                    to=to,
                    sender=sender,
                    subject=subject,
                    html_content=html_content
                )
                
                try:
                    api_instance.send_transac_email(send_smtp_email)
                    messages.success(request, "Password reset link sent! Check your email.")
                except ApiException as e:
                    return render(request, 'core/password_reset.html', {'error': f"API failed: {str(e)}"})
            
            return redirect('login')
        else:
            messages.success(request, "If that email exists, a reset link has been sent.")
            return redirect('login')
            
    return render(request, 'core/password_reset.html')

# ---------------------------------------------------------
# ADMIN DASHBOARD VIEWS
# ---------------------------------------------------------
@staff_member_required
def admin_dashboard(request):
    pending_admin = CheckoutSession.objects.filter(status='pending_admin').order_by('-created_at')
    pending_verification = CheckoutSession.objects.filter(status='pending_verification').order_by('-created_at')
    approved_payments = CheckoutSession.objects.filter(status='approved').order_by('-created_at')
    members = Profile.objects.all().order_by('-created_at')
    stories = SuccessStory.objects.all().order_by('-created_at')

    return render(request, 'core/admin_dashboard.html', {
        'pending_admin': pending_admin,
        'pending_verification': pending_verification,
        'approved_payments': approved_payments,
        'members': members,
        'stories': stories,
    })

@staff_member_required
def admin_send_details(request, checkout_id):
    if request.method == 'POST':
        checkout = get_object_or_404(CheckoutSession, id=checkout_id)
        checkout.admin_instructions = request.POST.get('instructions')
        checkout.status = 'pending_payment'
        checkout.save()
        messages.success(request, f"Details sent to {checkout.member.profile.full_name}!")
    return redirect('admin_dashboard')

@staff_member_required
def admin_approve_payment(request, checkout_id):
    checkout = get_object_or_404(CheckoutSession, id=checkout_id)
    checkout.status = 'approved'
    checkout.save()
    Connection.objects.get_or_create(sender=checkout.member, receiver=checkout.receiver, defaults={'status': 'accepted'})
    messages.success(request, f"Payment approved for {checkout.member.profile.full_name}!")
    return redirect('admin_dashboard')

@staff_member_required
def admin_reject_payment(request, checkout_id):
    checkout = get_object_or_404(CheckoutSession, id=checkout_id)
    checkout.status = 'rejected'
    checkout.save()
    messages.success(request, f"Payment rejected for {checkout.member.profile.full_name}.")
    return redirect('admin_dashboard')

@staff_member_required
def admin_add_story(request):
    if request.method == 'POST':
        names = request.POST.get('names')
        country = request.POST.get('country')
        testimonial = request.POST.get('testimonial')
        
        photo_url = ''
        if 'photo' in request.FILES:
            import cloudinary.uploader
            upload_result = cloudinary.uploader.upload(request.FILES['photo'])
            photo_url = upload_result['secure_url']
            
        SuccessStory.objects.create(
            couple_names=names,
            countries=country,
            testimonial=testimonial,
            photo=photo_url
        )
        messages.success(request, "Success Story added successfully!")
        return redirect('admin_dashboard')
        
    return redirect('admin_dashboard')