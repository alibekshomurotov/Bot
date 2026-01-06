# Telegram Ride Sharing Bot - To'liq ishlaydigan versiya
# Yo'lovchidan 5,000 so'm to'lov evaziga haydovchilar ro'yxati

import logging
import json
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ⚠️ BU YERNI O'ZGARTIRING!
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "-1003236563110"
ADMIN_ID = 8014950410

PAYMENT_AMOUNT = 5000

DATA_FILE = "ride_sharing_bot_data.json"
PAYMENTS_FILE = "payments_data.json"

user_data = {}
user_states = {}
driver_applications = {}
passenger_applications = {}
payments_data = {}
application_counter = 1

# ==================== MA'LUMOTLARNI YUKLASH/SAQLASH ====================
def load_data():
    global user_data, driver_applications, passenger_applications, payments_data, application_counter
    
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                user_data = data.get("user_data", {})
                driver_applications = data.get("driver_applications", {})
                passenger_applications = data.get("passenger_applications", {})
                application_counter = data.get("application_counter", 1)
                print("✅ Asosiy ma'lumotlar yuklandi")
        
        if os.path.exists(PAYMENTS_FILE):
            with open(PAYMENTS_FILE, "r", encoding="utf-8") as f:
                payments_data = json.load(f)
                print("✅ To'lov ma'lumotlari yuklandi")
    except Exception as e:
        print(f"❌ Ma'lumotlarni yuklashda xato: {e}")

def save_data():
    try:
        main_data = {
            "user_data": user_data,
            "driver_applications": driver_applications,
            "passenger_applications": passenger_applications,
            "application_counter": application_counter
        }
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(main_data, f, ensure_ascii=False, indent=4)
        
        with open(PAYMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(payments_data, f, ensure_ascii=False, indent=4)
        
        print("✅ Ma'lumotlar saqlandi")
    except Exception as e:
        print(f"❌ Ma'lumotlarni saqlashda xato: {e}")

load_data()

# ==================== KEYBOARD FUNKSIYALARI ====================
def car_type_keyboard():
    keyboard = [
        [InlineKeyboardButton("Spark ⚡️", callback_data='car_type_Spark'),
         InlineKeyboardButton("Cobalt", callback_data='car_type_Cobalt')],
        [InlineKeyboardButton("Gentra", callback_data='car_type_Gentra'),
         InlineKeyboardButton("Lacetti", callback_data='car_type_Lacetti')],
        [InlineKeyboardButton("Nexia", callback_data='car_type_Nexia'),
         InlineKeyboardButton("Malibu", callback_data='car_type_Malibu')],
        [InlineKeyboardButton("Boshqa", callback_data='car_type_Boshqa')]
    ]
    return InlineKeyboardMarkup(keyboard)

def car_preference_keyboard():
    keyboard = [
        [InlineKeyboardButton("Iqtisodiy 💸", callback_data='car_pref_Iqtisodiy'),
         InlineKeyboardButton("Komfort 🛋️", callback_data='car_pref_Komfort')],
        [InlineKeyboardButton("Spark", callback_data='car_pref_Spark'),
         InlineKeyboardButton("Cobalt", callback_data='car_pref_Cobalt')],
        [InlineKeyboardButton("Gentra", callback_data='car_pref_Gentra'),
         InlineKeyboardButton("Farqi yo'q", callback_data='car_pref_Farqi yoq')]
    ]
    return InlineKeyboardMarkup(keyboard)

def time_keyboard():
    keyboard = [
        [InlineKeyboardButton("Hozir 🕐", callback_data='time_Hozir'),
         InlineKeyboardButton("30 daqiqadan keyin", callback_data='time_30 daqiqadan keyin')],
        [InlineKeyboardButton("1 soatdan keyin", callback_data='time_1 soatdan keyin'),
         InlineKeyboardButton("Bugun kechqurun", callback_data='time_Bugun kechqurun')],
        [InlineKeyboardButton("Ertaga ertalab", callback_data='time_Ertaga ertalab')],
        [InlineKeyboardButton("Boshqa vaqt", callback_data='time_Boshqa')]
    ]
    return InlineKeyboardMarkup(keyboard)

def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🚗 Haydovchi bo'lish", callback_data='role_driver')],
        [InlineKeyboardButton("🚶 Yo'lovchi bo'lish", callback_data='role_passenger')],
        [InlineKeyboardButton("💰 Haydovchilar ro'yxati (5,000 so'm)", callback_data='show_drivers')],
        [InlineKeyboardButton("📞 Admin", url=f"tg://user?id={ADMIN_ID}")]
    ]
    return InlineKeyboardMarkup(keyboard)

def payment_methods_keyboard():
    keyboard = [
        [InlineKeyboardButton("💳 Bank karta", callback_data='pay_card')],
        [InlineKeyboardButton("📱 Click", callback_data='pay_click')],
        [InlineKeyboardButton("💵 Payme", callback_data='pay_payme')],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data='cancel_payment')]
    ]
    return InlineKeyboardMarkup(keyboard)

def confirm_payment_keyboard():
    keyboard = [
        [InlineKeyboardButton("✅ To'lov qildim", callback_data='confirm_payment')],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data='cancel_payment')]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== TO'LOV TIZIMI FUNKSIYALARI ====================
def has_paid_recently(user_id):
    user_id_str = str(user_id)
    
    if user_id_str in payments_data:
        for payment in payments_data[user_id_str]:
            if payment.get('status') == 'verified':
                try:
                    payment_date = datetime.fromisoformat(payment['date'])
                    time_diff = datetime.now() - payment_date
                    if time_diff.total_seconds() < 24 * 3600:
                        return True
                except:
                    continue
    return False

def add_payment_record(user_id, method, screenshot_id=None):
    user_id_str = str(user_id)
    
    if user_id_str not in payments_data:
        payments_data[user_id_str] = []
    
    payment_record = {
        'id': f"pay_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        'date': datetime.now().isoformat(),
        'amount': PAYMENT_AMOUNT,
        'method': method,
        'status': 'pending',
        'screenshot': screenshot_id
    }
    
    payments_data[user_id_str].append(payment_record)
    save_data()
    return payment_record['id']

async def send_drivers_list_to_user(context, user_id):
    active_drivers = []
    for app_id, driver in driver_applications.items():
        active_drivers.append(driver)
    
    if not active_drivers:
        await context.bot.send_message(
            user_id,
            "🚗 *Haydovchilar ro'yxati*\n\nHozircha faol haydovchilar yo'q. Biroz vaqt o'tgach qayta urinib ko'ring.\n\n✅ To'lovingiz qabul qilindi va saqlandi.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    message = "🚗 *TOP HAYDOVCHILAR*\n\n"
    message += "💰 *To'lov qilganingiz uchun rahmat! (5,000 so'm)*\n\n"
    
    for i, driver in enumerate(active_drivers[:10], 1):
        message += f"{i}. *{driver.get('first_name', 'Noma\'lum')}*\n"
        message += f"   🚘 {driver.get('car_type', 'Mashina yo\'q')}\n"
        message += f"   💰 {driver.get('price', 'Narx yo\'q')}\n"
        message += f"   📞 {driver.get('phone', 'Telefon yo\'q')}\n\n"
    
    message += "📞 *Haydovchi bilan bog'laning va safar haqida kelishing*\n\n"
    message += "⏱️ *24 soat davomida yangi haydovchilar qo'shilganda sizga xabar yuboriladi*"
    
    await context.bot.send_message(user_id, message, parse_mode=ParseMode.MARKDOWN)

async def notify_admin_about_payment(context, user_id, payment_id, screenshot_id=None):
    try:
        user = await context.bot.get_chat(user_id)
        message = f"🔄 *Yangi to'lov tasdiqlanmoqda!*\n\n👤 *Foydalanuvchi:* {user.first_name}\n🆔 *ID:* {user_id}\n💰 *Summa:* {PAYMENT_AMOUNT:,} so'm\n📅 *Vaqt:* {datetime.now().strftime('%H:%M %d.%m.%Y')}\n🔢 *To'lov ID:* {payment_id}\n\n*Tasdiqlang yoki rad eting:*"
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Tasdiqlash", callback_data=f'verify_{payment_id}'),
                InlineKeyboardButton("❌ Rad etish", callback_data=f'reject_{payment_id}')
            ]
        ]
        
        if screenshot_id:
            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=screenshot_id,
                caption=message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
    except Exception as e:
        print(f"Adminga xabar yuborishda xato: {e}")

# ==================== START VA ASOSIY FUNKSIYALAR ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id == ADMIN_ID:
        await update.message.reply_text(
            f"👑 *Assalomu alaykum, Admin!*\n\nAdmin panelga xush kelibsiz. Quyidagi komandalar mavjud:\n/stats - Statistika\n/payments - To'lovlar ro'yxati\n/broadcast - Xabar yuborish\n/users - Foydalanuvchilar",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    welcome_text = f"👋 *Assalomu alaykum, {user.first_name}!*\n\n🚖 *Ride Sharing Bot* ga xush kelibsiz!\n\n📌 *Bot qanday ishlaydi:*\n1. Haydovchi yoki yo'lovchi sifatida ro'yxatdan o'ting\n2. Yo'lovchi bo'lsangiz, haydovchilar ro'yxatini ko'rish uchun 5,000 so'm to'lang\n3. Haydovchi bilan bog'lanib, safar haqida kelishing\n\n💰 *Xizmat narxi:* 5,000 so'm (yo'lovchidan)\n⏱️ *24 soat davomida cheksiz haydovchilarni ko'rishingiz mumkin*\n\nQuyidagi tugmalardan birini tanlang:"
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

# ==================== TO'LOV TIZIMI HANDLERLARI ====================
async def show_drivers_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if str(user_id) not in user_data:
        await query.edit_message_text(
            "<b>⚠️ Avval ro'yxatdan o'ting!</b>\n\n"
            "Haydovchilar ro'yxatini ko'rish uchun avval botdan foydalanish uchun ro'yxatdan o'ting. "
            "Quyidagi tugmalardan birini tanlang:",
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.HTML
        )
        return
    
    if has_paid_recently(user_id):
        await send_drivers_list_to_user(context, user_id)
        return
    
    payment_text = (
        f"<b>💰 Haydovchilar ro'yxati - {PAYMENT_AMOUNT:,} so'm</b>\n\n"
        f"To'lov usulini tanlang:\n\n"
        f"💳 <b>Bank karta:</b> 8600 1234 5678 9012 (JOHN DOE)\n"
        f"📱 <b>Click:</b> +998901234567\n"
        f"💵 <b>Payme:</b> @payme_username\n\n"
        f"💡 <b>Eslatma:</b> To'lov qilganingizdan so'ng screenshot yuboring"
    )
    
    await query.edit_message_text(
        payment_text,
        reply_markup=payment_methods_keyboard(),
        parse_mode=ParseMode.HTML
    )

async def payment_method_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """To'lov usullari callback handleri"""
    query = update.callback_query
    await query.answer()
    
    # Payme tugmasi bosilganda
    if query.data == 'pay_payme':
        context.user_data['payment_method'] = "Payme"
        
        await query.edit_message_text(
            f"💵 <b>Payme orqali to'lash</b>\n\n"
            f"Telefon: +998901234567\n"
            f"Username: @payme_bot\n\n"
            f"💰 <b>To'lov summasi:</b> {PAYMENT_AMOUNT:,} so'm\n\n"
            f"💡 <b>Ko'rsatma:</b>\n"
            f"1. Yuqoridagi raqamga {PAYMENT_AMOUNT:,} so'm o'tkazing\n"
            f"2. To'lovni tasdiqlovchi screenshot oling\n"
            f"3. '✅ To'lov qildim' tugmasini bosing\n"
            f"4. Screenshotni yuboring\n\n"
            f"Admin 5-10 daqiqa ichida tekshirib, ro'yxatni yuboradi.",
            reply_markup=confirm_payment_keyboard(),
            parse_mode=ParseMode.HTML
        )
    
    # Bank karta tugmasi bosilganda
    elif query.data == 'pay_card':
        context.user_data['payment_method'] = "Bank karta"
        
        await query.edit_message_text(
            f"💳 <b>Bank karta orqali to'lash</b>\n\n"
            f"Karta raqami: 8600 1234 5678 9012\n"
            f"Ism: JOHN DOE\n\n"
            f"💰 <b>To'lov summasi:</b> {PAYMENT_AMOUNT:,} so'm\n\n"
            f"💡 <b>Ko'rsatma:</b>\n"
            f"1. Yuqoridagi raqamga {PAYMENT_AMOUNT:,} so'm o'tkazing\n"
            f"2. To'lovni tasdiqlovchi screenshot oling\n"
            f"3. '✅ To'lov qildim' tugmasini bosing\n"
            f"4. Screenshotni yuboring\n\n"
            f"Admin 5-10 daqiqada tekshirib, ro'yxatni yuboradi.",
            reply_markup=confirm_payment_keyboard(),
            parse_mode=ParseMode.HTML
        )
    
    # Click tugmasi bosilganda
    elif query.data == 'pay_click':
        context.user_data['payment_method'] = "Click"
        
        await query.edit_message_text(
            f"📱 <b>Click orqali to'lash</b>\n\n"
            f"Telefon: +998901234567\n"
            f"Ism: John\n\n"
            f"💰 <b>To'lov summasi:</b> {PAYMENT_AMOUNT:,} so'm\n\n"
            f"💡 <b>Ko'rsatma:</b>\n"
            f"1. Yuqoridagi raqamga {PAYMENT_AMOUNT:,} so'm o'tkazing\n"
            f"2. To'lovni tasdiqlovchi screenshot oling\n"
            f"3. '✅ To'lov qildim' tugmasini bosing\n"
            f"4. Screenshotni yuboring\n\n"
            f"Admin 5-10 daqiqada tekshirib, ro'yxatni yuboradi.",
            reply_markup=confirm_payment_keyboard(),
            parse_mode=ParseMode.HTML
        )
    
    # Bekor qilish tugmasi
    elif query.data == 'cancel_payment':
        await query.edit_message_text(
            "❌ <b>To'lov bekor qilindi.</b>\n\n"
            "Bosh menyuga qaytish uchun /start ni bosing.",
            parse_mode=ParseMode.HTML
        )
    
    # To'lov qildim tugmasi
    elif query.data == 'confirm_payment':
        method = context.user_data.get('payment_method', 'Noma\'lum')
        
        await query.edit_message_text(
            "✅ <b>To'lov qilganingizni bildirdingiz!</b>\n\n"
            "Endi to'lov screenshotini (skrinshot) yuboring.\n"
            "Admin tekshirgach, sizga haydovchilar ro'yxati yuboriladi.\n\n"
            "📸 <b>Iltimos, rasm yuboring:</b>",
            parse_mode=ParseMode.HTML
        )
        context.user_data['awaiting_screenshot'] = True

async def show_payment_instructions(query, method, details, context):
    """To'lov ko'rsatmalarini ko'rsatish"""
    user_id = query.from_user.id
    context.user_data['payment_method'] = method
    
    await query.edit_message_text(
        f"💳 *{method} orqali to'lash*\n\n"
        f"{details}\n\n"
        f"💰 *To'lov summasi:* {PAYMENT_AMOUNT:,} so'm\n\n"
        f"💡 *Ko'rsatma:*\n"
        f"1. Yuqoridagi raqamga {PAYMENT_AMOUNT:,} so'm o'tkazing\n"
        f"2. To'lovni tasdiqlovchi screenshot oling\n"
        f"3. '✅ To'lov qildim' tugmasini bosing\n"
        f"4. Screenshotni yuboring\n\n"
        f"Admin 5-10 daqiqada tekshirib, ro'yxatni yuboradi.",
        reply_markup=confirm_payment_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if context.user_data.get('awaiting_screenshot'):
        if update.message.photo:
            screenshot_id = update.message.photo[-1].file_id
            
            payment_id = add_payment_record(
                user_id, 
                context.user_data.get('payment_method', 'Noma\'lum'),
                screenshot_id
            )
            
            await notify_admin_about_payment(context, user_id, payment_id, screenshot_id)
            
            await update.message.reply_text(
                "✅ *Screenshot qabul qilindi!*\n\nAdmin to'lovni tekshiryapti. Tasdiqlanganidan so'ng sizga haydovchilar ro'yxati yuboriladi.\n\n⏳ *Kuting...*",
                parse_mode=ParseMode.MARKDOWN
            )
            
            context.user_data['awaiting_screenshot'] = False
            context.user_data['payment_method'] = None
            
        else:
            await update.message.reply_text(
                "⚠️ *Iltimos, screenshotni rasm shaklida yuboring!*\n\nTelefoningizdan to'lov qilganingizni ko'rsatadigan rasmni yuboring.",
                parse_mode=ParseMode.MARKDOWN
            )

async def admin_payment_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        await query.answer("Siz admin emassiz!", show_alert=True)
        return
    
    action, payment_id = query.data.split('_', 1)
    
    for user_id_str, payments in payments_data.items():
        for payment in payments:
            if payment['id'] == payment_id:
                if action == 'verify':
                    payment['status'] = 'verified'
                    payment['verified_by'] = query.from_user.id
                    payment['verified_at'] = datetime.now().isoformat()
                    
                    await send_drivers_list_to_user(context, int(user_id_str))
                    
                    await context.bot.send_message(
                        chat_id=int(user_id_str),
                        text="✅ *To'lovingiz tasdiqlandi!*\n\nHaydovchilar ro'yxati sizga yuborildi. 24 soat davomida yangi haydovchilar qo'shilganda xabar olasiz.\n\nRahmat! 🚗",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                    await query.edit_message_text(
                        f"✅ *To'lov tasdiqlandi!*\n\nFoydalanuvchiga haydovchilar ro'yxati yuborildi.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                elif action == 'reject':
                    payment['status'] = 'rejected'
                    
                    await context.bot.send_message(
                        chat_id=int(user_id_str),
                        text="❌ *To'lov rad etildi!*\n\nSizning to'lovingiz tasdiqlanmadi. Sabab:\n• Screenshot noaniq\n• To'lov summasi noto'g'ri\n• Boshqa xatolik\n\nQayta urinib ko'ring yoki admin bilan bog'laning.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                    await query.edit_message_text(
                        f"❌ *To'lov rad etildi!*\n\nFoydalanuvchiga rad etilganligi haqida xabar yuborildi.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                
                save_data()
                return
    
    await query.answer("To'lov topilmadi!", show_alert=True)

# ==================== SIZNING KODINGIZ ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == 'role_driver':
        user_states[user_id] = 'registering_driver_name'
        await query.edit_message_text('Iltimos, ismingizni kiriting:')

    elif query.data == 'role_passenger':
        user_states[user_id] = 'registering_passenger_name'
        await query.edit_message_text('Iltimos, ismingizni kiriting:')

    elif query.data.startswith('car_type_'):
        car_type = query.data[9:]
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]['car_type'] = car_type
        user_states[user_id] = 'registering_driver_price'
        await query.edit_message_text('Bir safar narxini kiriting (masalan: 150000 soʻm):')

    elif query.data.startswith('car_pref_'):
        pref = query.data[9:]
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]['car_preference'] = pref
        user_states[user_id] = 'registering_passenger_time'
        await query.edit_message_text('Qachon joʻnamoqchisiz?', reply_markup=time_keyboard())

    elif query.data.startswith('time_'):
        time_text = query.data[5:]
        if time_text == 'Boshqa':
            user_states[user_id] = 'registering_passenger_time_manual'
            await query.edit_message_text('Vaqtni oʻzingiz yozing (masalan: 15:30, ertaga soat 10:00):')
        else:
            user_data[user_id]['departure_time'] = time_text
            await complete_passenger_application(update, context)

    elif query.data == 'show_drivers':
        await show_drivers_callback(update, context)
    
    elif query.data in ['pay_card', 'pay_click', 'pay_payme', 'cancel_payment', 'confirm_payment']:
        await payment_method_callback(update, context)
    
    elif query.data.startswith('verify_') or query.data.startswith('reject_'):
        await admin_payment_action(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message

    if context.user_data.get('awaiting_screenshot'):
        await handle_screenshot(update, context)
        return
    
    if user_id not in user_states:
        if message.text and message.text.startswith('/myapp'):
            await my_application(update, context)
        return

    state = user_states[user_id]
    if user_id not in user_data:
        user_data[user_id] = {}

    if state in ['registering_driver_name', 'registering_passenger_name']:
        user_data[user_id]['first_name'] = message.text.strip()
        next_state = 'registering_driver_phone' if 'driver' in state else 'registering_passenger_phone'
        user_states[user_id] = next_state
        keyboard = [[KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await message.reply_text('Telefon raqamingizni yuboring:', reply_markup=reply_markup)

    elif state in ['registering_driver_phone', 'registering_passenger_phone']:
        if message.contact:
            phone = message.contact.phone_number
            if not phone.startswith('+'):
                phone = '+' + phone
            user_data[user_id]['phone'] = phone
        else:
            user_data[user_id]['phone'] = message.text.strip()

        if 'driver' in state:
            user_states[user_id] = 'registering_driver_car_type'
            await message.reply_text('Mashina turini tanlang:', reply_markup=car_type_keyboard())
        else:
            user_states[user_id] = 'registering_passenger_departure'
            await message.reply_text('📍 Qayerdan joʻnamoqchisiz?\n\nMasalan: "Toshkent, Chilanzor" yoki "Samarqand shahar" deb yozing.')

    elif state == 'registering_passenger_departure':
        if message.location:
            user_data[user_id]['departure_location'] = {
                'latitude': message.location.latitude,
                'longitude': message.location.longitude
            }
        elif message.text:
            user_data[user_id]['departure'] = message.text.strip()
        user_states[user_id] = 'registering_passenger_destination'
        keyboard = [[KeyboardButton("📍 Borish joyini yuborish", request_location=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await message.reply_text('📍 Borish joyingizni yuboring:', reply_markup=reply_markup)

    elif state == 'registering_passenger_destination':
        if message.location:
            user_data[user_id]['destination_location'] = {
                'latitude': message.location.latitude,
                'longitude': message.location.longitude
            }
        elif message.text:
            user_data[user_id]['destination'] = message.text.strip()
        user_states[user_id] = 'registering_passenger_car_preference'
        await message.reply_text('Qanday mashina afzal koʻrasiz?', reply_markup=car_preference_keyboard())

    elif state == 'registering_driver_price':
        user_data[user_id]['price'] = message.text.strip()
        user_states[user_id] = 'registering_driver_photo'
        await message.reply_text('🚗 Mashinangiz rasmini yuboring:')

    elif state == 'registering_driver_photo':
        if message.photo:
            user_data[user_id]['car_photo'] = message.photo[-1].file_id
            await complete_driver_application(update, context)
        else:
            await message.reply_text('Iltimos, faqat rasm yuboring!')

    elif state == 'registering_passenger_time_manual':
        user_data[user_id]['departure_time'] = message.text.strip()
        await complete_passenger_application(update, context)

async def complete_driver_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id]['role'] = 'driver'
    global application_counter
    app_id = f"D{application_counter:04d}"
    application_counter += 1

    driver_applications[app_id] = {
        'user_id': user_id,
        'first_name': user_data[user_id]['first_name'],
        'phone': user_data[user_id]['phone'],
        'car_type': user_data[user_id]['car_type'],
        'price': user_data[user_id]['price'],
        'car_photo': user_data[user_id].get('car_photo'),
        'date': datetime.now().isoformat()
    }

    application_text = f"🚗 YANGI HAYDOVCHI ARIZASI #{app_id}\n\nIsm: {user_data[user_id]['first_name']}\nTelefon: {user_data[user_id]['phone']}\nMashina: {user_data[user_id]['car_type']}\nNarx: {user_data[user_id]['price']}\nUser ID: {user_id}"

    try:
        if user_data[user_id].get('car_photo'):
            await context.bot.send_photo(
                chat_id=CHANNEL_ID, 
                photo=user_data[user_id]['car_photo'], 
                caption=application_text
            )
        else:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=application_text)

        del user_states[user_id]
        save_data()

        await update.message.reply_text(
            f"✅ Rahmat, {user_data[user_id]['first_name']}!\nArizangiz qabul qilindi (ID: {app_id})\nTez orada yo'lovchilar bilan bog'lanamiz!\n\n💰 Yo'lovchilar sizni ko'rish uchun 5,000 so'm to'laydi",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await update.message.reply_text("Xato yuz berdi.")
        print(e)

async def complete_passenger_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Rolni faqat agar hali rol belgilamagan bo‘lsa o‘rnatamiz
    # Agar allaqachon driver bo‘lsa — o‘zgartirmaymiz!
    if user_id not in user_data or 'role' not in user_data[user_id]:
        user_data[user_id]['role'] = 'passenger'
    # Agar driver bo‘lsa — hech nima qilmaymiz, role o‘zgarmaydi
    
    global application_counter
    app_id = f"P{application_counter:04d}"
    application_counter += 1
    
    # ... qolgan kod o‘zgarmaydi

    passenger_applications[app_id] = {
        'user_id': user_id,
        'first_name': user_data[user_id]['first_name'],
        'phone': user_data[user_id]['phone'],
        'departure': user_data[user_id].get('departure'),
        'destination': user_data[user_id].get('destination'),
        'car_preference': user_data[user_id]['car_preference'],
        'departure_time': user_data[user_id]['departure_time'],
        'date': datetime.now().isoformat()
    }

    departure_text = user_data[user_id].get('departure') or "Lokatsiya yuborilgan"
    destination_text = user_data[user_id].get('destination') or "Lokatsiya yuborilgan"

    application_text = f"🚶 YANGI YOʻLOVCHI ARIZASI #{app_id}\n\nIsm: {user_data[user_id]['first_name']}\nTelefon: {user_data[user_id]['phone']}\nJoʻnash: {departure_text}\nBorish: {destination_text}\nMashina: {user_data[user_id]['car_preference']}\nVaqt: {user_data[user_id]['departure_time']}\nUser ID: {user_id}"

    try:
        if user_data[user_id].get('departure_location'):
            await context.bot.send_location(
                chat_id=CHANNEL_ID,
                latitude=user_data[user_id]['departure_location']['latitude'],
                longitude=user_data[user_id]['departure_location']['longitude']
            )
            await context.bot.send_message(chat_id=CHANNEL_ID, text="📍 Joʻnash joyi")

        if user_data[user_id].get('destination_location'):
            await context.bot.send_location(
                chat_id=CHANNEL_ID,
                latitude=user_data[user_id]['destination_location']['latitude'],
                longitude=user_data[user_id]['destination_location']['longitude']
            )
            await context.bot.send_message(chat_id=CHANNEL_ID, text="📍 Borish joyi")

        await context.bot.send_message(chat_id=CHANNEL_ID, text=application_text)

        del user_states[user_id]
        save_data()

        await update.message.reply_text(
            f"✅ Rahmat, {user_data[user_id]['first_name']}!\nYangi arizangiz qabul qilindi (ID: {app_id})\n\n🚗 *Haydovchilar ro'yxatini ko'rish uchun 5,000 so'm to'lang*\n24 soat davomida cheksiz haydovchilarni ko'rishingiz mumkin!\n\nTo'lov qilish uchun:",
            reply_markup=payment_methods_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        await update.message.reply_text("Xato yuz berdi.")
        print(e)

async def my_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    for app_id, app in driver_applications.items():
        if app.get('user_id') == user_id:
            await update.message.reply_text(
                f"🚗 *Sizning haydovchi arizangiz* ({app_id})\n\n👤 Ism: {app['first_name']}\n📞 Telefon: {app['phone']}\n🚘 Mashina: {app['car_type']}\n💰 Narx: {app['price']}\n📅 Sana: {app['date'][:10]}",
                parse_mode=ParseMode.MARKDOWN
            )
            return
    
    passenger_apps = []
    for app_id, app in passenger_applications.items():
        if app.get('user_id') == user_id:
            passenger_apps.append((app_id, app))
    
    if passenger_apps:
        app_id, app = passenger_apps[-1]
        departure = app.get('departure') or "Lokatsiya"
        destination = app.get('destination') or "Lokatsiya"
        
        await update.message.reply_text(
            f"🚶 *Sizning yoʻlovchi arizangiz* ({app_id})\n\n👤 Ism: {app['first_name']}\n📞 Telefon: {app['phone']}\n📍 Joʻnash: {departure}\n🎯 Borish: {destination}\n🕐 Vaqt: {app['departure_time']}\n🚗 Mashina: {app['car_preference']}\n📅 Sana: {app['date'][:10]}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        if has_paid_recently(user_id):
            await update.message.reply_text(
                "✅ *Siz to'lov qilgansiz!*\n24 soat davomida haydovchilar ro'yxatini ko'rishingiz mumkin.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                f"💰 *Haydovchilar ro'yxatini ko'rish uchun to'lov qiling!*\nSumma: {PAYMENT_AMOUNT:,} so'm\n24 soat davomida cheksiz access",
                reply_markup=payment_methods_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
    else:
        await update.message.reply_text(
            "📭 Siz hali ariza topshirmagansiz.\nAriza topshirish uchun /start ni bosing.",
            parse_mode=ParseMode.MARKDOWN
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚕 *Ride Sharing Bot - Yordam*\n\n/start - Botni ishga tushirish\n/myapp - Ariza holatini ko'rish\n/help - Yordam\n\n💰 *Xizmat narxi:* 5,000 so'm (yo'lovchidan)\n⏱️ *Access muddati:* 24 soat\n👥 *Haydovchilar:* Bepul ro'yxatdan o'tadi\n\n📞 *Admin:* @username (murojaat uchun)",
        parse_mode=ParseMode.MARKDOWN
    )

# ==================== ADMIN KOMANDALARI ====================
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    total_users = len(user_data)
    total_drivers = len(driver_applications)
    total_passengers = len(passenger_applications)
    
    total_payments = 0
    verified_payments = 0
    total_income = 0
    
    for user_payments in payments_data.values():
        for payment in user_payments:
            total_payments += 1
            if payment.get('status') == 'verified':
                verified_payments += 1
                total_income += PAYMENT_AMOUNT
    
    stats_text = f"📊 *BOT STATISTIKASI*\n\n👥 *Umumiy foydalanuvchilar:* {total_users}\n🚗 *Haydovchilar:* {total_drivers}\n🚶 *Yo'lovchilar:* {total_passengers}\n\n💰 *TO'LOVLAR:*\n• Umumiy to'lovlar: {total_payments}\n• Tasdiqlangan: {verified_payments}\n• Daromad: {total_income:,} so'm\n\n📅 *Bugun:* {datetime.now().strftime('%d.%m.%Y')}"
    
    await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)

async def admin_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    if not payments_data:
        await update.message.reply_text("📭 To'lovlar mavjud emas")
        return
    
    text = "💰 *TO'LOVLAR RO'YXATI*\n\n"
    
    count = 0
    for user_id_str, payments in payments_data.items():
        for payment in payments[-5:]:
            count += 1
            status_emoji = "✅" if payment['status'] == 'verified' else "⏳" if payment['status'] == 'pending' else "❌"
            text += f"{count}. {status_emoji} {payment['id']}\n"
            text += f"   👤 User ID: {user_id_str}\n"
            text += f"   💰 {payment['amount']:,} so'm\n"
            text += f"   💳 {payment['method']}\n"
            text += f"   📅 {payment['date'][:16]}\n"
            text += f"   📊 {payment['status']}\n"
            text += "   ―" * 10 + "\n"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    if len(context.args) == 0:
        await update.message.reply_text(
            "📢 *Xabar yuborish*\n\nFoydalanish: /broadcast <xabar>\nMasalan: /broadcast Yangi yangilik!",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    message = ' '.join(context.args)
    success = 0
    failed = 0
    
    for user_id in user_data.keys():
        try:
            await context.bot.send_message(
                chat_id=int(user_id),
                text=f"📢 *Admin xabari:*\n\n{message}",
                parse_mode=ParseMode.MARKDOWN
            )
            success += 1
        except:
            failed += 1
    
    await update.message.reply_text(
        f"✅ *Xabar yuborildi!*\n\n✅ Muvaffaqiyatli: {success}\n❌ Muvaffaqiyatsiz: {failed}",
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    if not user_data:
        await update.message.reply_text("📭 Foydalanuvchilar mavjud emas")
        return
    
    text = f"👥 *FOYDALANUVCHILAR: {len(user_data)} ta*\n\n"
    
    for i, (user_id_str, data) in enumerate(list(user_data.items())[:10], 1):
        role = "🚗 Haydovchi" if data.get('role') == 'driver' else "🚶 Yo'lovchi"
        text += f"{i}. {data.get('first_name', 'Noma\'lum')}\n"
        text += f"   🆔 {user_id_str}\n"
        text += f"   {role}\n"
        text += f"   📞 {data.get('phone', 'Yo\'q')}\n"
        text += "   ―" * 8 + "\n"
    
    if len(user_data) > 10:
        text += f"\n... va yana {len(user_data) - 10} ta foydalanuvchi"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# ==================== ASOSIY FUNKSIYA ====================
def main():
    print("🤖 Ride Sharing Bot ishga tushmoqda...")
    print(f"💰 To'lov summasi: {PAYMENT_AMOUNT:,} so'm")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print("=" * 50)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlerlar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myapp", my_application))
    app.add_handler(CommandHandler("help", help_command))
    
    # Admin commandlar
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("payments", admin_payments))
    app.add_handler(CommandHandler("broadcast", admin_broadcast))
    app.add_handler(CommandHandler("users", admin_users))
    
    # Barcha callbacklar uchun bitta handler - ENG MUHIM QISMI!
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Message handlerlar
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_message))
    app.add_handler(MessageHandler(filters.LOCATION, handle_message))
    app.add_handler(MessageHandler(filters.CONTACT, handle_message))
    
    print("✅ Bot ishga tushdi! Ctrl+C to'xtatish")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':

    main()
