import sys
import os
import django
import tempfile
import requests
import cloudinary
import cloudinary.uploader
import threading
from asgiref.sync import sync_to_async
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from django.core.files import File
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'singlesconnect.settings')
django.setup()

from django.conf import settings
from core.models import Profile, CheckoutSession, Connection, SuccessStory

admin_state = {}
story_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Admin Bot Active.\n\n"
        "Commands:\n"
        "/addstory - Add a new Success Story\n"
        "/members - View registered members"
    )

async def add_story_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    admin_state[user_id] = 'awaiting_story_photo'
    await update.message.reply_text("📸 Please send the couple's photo for the Success Story.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if admin_state.get(user_id) == 'awaiting_story_photo':
        try:
            file_id = update.message.photo[-1].file_id
            new_file = await context.bot.get_file(file_id)
            file_url = new_file.file_path
            
            temp_path = os.path.join(tempfile.gettempdir(), f"story_{user_id}.jpg")
            response = requests.get(file_url, stream=True)
            response.raise_for_status()
            
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            story_data[user_id] = {'photo_path': temp_path}
            admin_state[user_id] = 'awaiting_story_text'
            await update.message.reply_text("✅ Photo received! Now type the story details in this format:\n\nNames | Country | Testimonial\n\nExample:\nJohn & Mary | Kenya | We met on Singles Connect and are now engaged!")
        except Exception as e:
            print(f"Error downloading photo: {e}")
            await update.message.reply_text(f"❌ Error receiving photo: {str(e)}")
            del admin_state[user_id]

async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current_state = admin_state.get(user_id)
    
    if current_state == 'awaiting_story_text':
        parts = update.message.text.split("|")
        if len(parts) == 3:
            names = parts[0].strip()
            country = parts[1].strip()
            testimonial = parts[2].strip()
            
            photo_path = story_data[user_id].get('photo_path')
            
            def save_story():
                story = SuccessStory(couple_names=names, countries=country, testimonial=testimonial)
                if photo_path and os.path.exists(photo_path):
                    try:
                        result = cloudinary.uploader.upload(photo_path)
                        story.photo = result['secure_url']
                    except Exception as upload_error:
                        print(f"Cloudinary upload failed: {upload_error}")
                    os.remove(photo_path)
                story.save()
            
            try:
                await sync_to_async(save_story)()
                del admin_state[user_id]
                del story_data[user_id]
                await update.message.reply_text(f"✅ Success Story for {names} has been published to the website!")
            except Exception as e:
                print(f"Error saving story: {e}")
                await update.message.reply_text(f"❌ Error saving to database: {str(e)}")
        else:
            await update.message.reply_text("❌ Invalid format. Please use: Names | Country | Testimonial")
        return

    if isinstance(current_state, int):
        checkout = await sync_to_async(CheckoutSession.objects.filter(id=current_state).first)()
        if not checkout:
            await update.message.reply_text("Error: Checkout not found.")
            del admin_state[user_id]
            return

        checkout.admin_instructions = update.message.text
        checkout.status = 'pending_payment'
        await sync_to_async(checkout.save)()
        
        del admin_state[user_id]
        await update.message.reply_text(f"✅ Payment details successfully sent to {checkout.member.profile.full_name}'s checkout page.")
        return

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.rsplit("_", 1) 
    action = data[0]
    checkout_id = int(data[1])
    
    checkout = await sync_to_async(CheckoutSession.objects.filter(id=checkout_id).first)()
    if not checkout:
        await query.edit_message_text("Checkout not found.")
        return

    if action == "approve":
        checkout.status = 'approved'
        await sync_to_async(checkout.save)()
        await sync_to_async(Connection.objects.get_or_create)(sender=checkout.member, receiver=checkout.receiver, defaults={'status': 'accepted'})
        await query.edit_message_text(f"✅ APPROVED: {checkout.member.profile.full_name} is now a paid member.")
    elif action == "reject":
        checkout.status = 'rejected'
        await sync_to_async(checkout.save)()
        await query.edit_message_text(f"❌ REJECTED: Payment from {checkout.member.profile.full_name} was declined.")
    elif action == "send_details":
        admin_state[query.from_user.id] = checkout_id
        await query.edit_message_text(f"Please reply with the payment details for {checkout.reference}.\nJust type the message exactly as you want the member to see it.")

async def members_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    def get_members_data():
        members = []
        for p in Profile.objects.all():
            members.append({
                'full_name': p.full_name,
                'age': p.age,
                'city': p.city,
                'country': p.country,
                'phone': p.phone,
                'user_id': p.user.id
            })
        return members

    profiles_data = await sync_to_async(get_members_data)()
    
    if not profiles_data:
        await update.message.reply_text("No members registered yet.")
        return
        
    total_members = len(profiles_data)
    message = f"👥 *REGISTERED MEMBERS ({total_members})*\n\n"
    
    for member in profiles_data[:30]:
        phone = member['phone'] if member['phone'] else 'No phone'
        message += (
            f"👤 *{member['full_name']}*, {member['age']}\n"
            f"📍 {member['city']}, {member['country']}\n"
            f"📞 {phone}\n"
            f"🆔 SC-{member['user_id']}\n\n"
        )
        
    if total_members > 30:
        message += f"...and {total_members - 30} more members."
        
    await update.message.reply_text(message, parse_mode="Markdown")

def start_bot():
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addstory", add_story_command))
    application.add_handler(CommandHandler("members", members_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_text))
    print("Telegram Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    # 1. Start the bot in a background thread
    bot_thread = threading.Thread(target=start_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # 2. Start a TINY web server to keep Render awake (instead of full Django)
    class HealthCheckHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is running!")

    port = int(os.environ.get('PORT', 10000))
    print(f"Starting health check server on port {port}...")
    
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()