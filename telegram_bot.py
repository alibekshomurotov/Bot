import logging
import json
import os
import threading
import asyncio
from datetime import datetime
from flask import Flask  
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ApplicationBuilder
from telegram.error import TelegramError, NetworkError, TimedOut

# Logging sozlamalari
logger = logging.getLogger(__name__)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ==================== ERROR HANDLER ====================
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xatolarni boshqarish"""
    try:
        error = context.error
        logger.error(f"❌ Bot xatosi: {error}")
        
        if isinstance(error, TimedOut):
            logger.warning("⚠️ Request timeout. Internet connection muammosi.")
        elif isinstance(error, NetworkError):
            logger.warning("⚠️ Network error. Internet ulanmagan.")
        elif isinstance(error, TelegramError):
            logger.error(f"❌ Telegram API xatosi: {error}")
        else:
            logger.error(f"❌ Noma'lum xato: {error}")
            
    except Exception as e:
        logger.error(f"❌ Error handler ichida xato: {e}")

# Flask app yaratish
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return """
    <!DOCTYPE html>
<html>
<head>
    <title>🚖 Ride Sharing Bot</title>
    <style>
        body { 
            font-family: 'Arial', sans-serif; 
            text-align: center; 
            padding: 50px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .container {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            max-width: 600px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        h1 { 
            color: white; 
            font-size: 36px;
            margin-bottom: 20px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .status { 
            color: #4ade80; 
            font-size: 28px;
            font-weight: bold;
            margin: 20px 0;
        }
        .info {
            background: rgba(255, 255, 255, 0.15);
            padding: 20px;
            border-radius: 15px;
            margin: 20px 0;
            text-align: left;
        }
        .bot-link {
            display: inline-block;
            background: white;
            color: #667eea;
            padding: 12px 30px;
            border-radius: 50px;
            text-decoration: none;
            font-weight: bold;
            font-size: 18px;
            margin: 20px 0;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        .bot-link:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.3);
        }
        .features {
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
            margin: 30px 0;
        }
        .feature {
            background: rgba(255, 255, 255, 0.1);
            padding: 15px;
            border-radius: 10px;
            margin: 10px;
            flex: 1;
            min-width: 150px;
        }
        .feature h3 {
            margin: 0 0 10px 0;
            color: #ffd166;
        }
        .stats {
            font-size: 14px;
            opacity: 0.8;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid rgba(255,255,255,0.2);
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚖 Ride Sharing Bot</h1>
        <p class="status">✅ Bot is running!</p>
        
        <div class="info">
            <h3>📋 Bot Features:</h3>
            <p>• 🚗 Find drivers & passengers</p>
            <p>• 💰 Secure payment system</p>
            <p>• 📍 Location-based matching</p>
            <p>• ⏱️ Real-time notifications</p>
        </div>
        
        <a href="https://t.me/@ZamonaviyMebelBot" class="bot-link" target="_blank">
            🤖 Start Bot in Telegram
        </a>
        
        <div class="features">
            <div class="feature">
                <h3>💰 Payment</h3>
                <p>5,000 UZS per ride list</p>
            </div>
            <div class="feature">
                <h3>⏱️ 24/7</h3>
                <p>Always available</p>
            </div>
            <div class="feature">
                <h3>👥 Users</h3>
                <p>Growing community</p>
            </div>
        </div>
        
        <div class="stats">
            <p>Server Time: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
            <p>🚀 Powered by Python Telegram Bot</p>
        </div>
    </div>
</body>
</html>
    """

@flask_app.route('/health')
def health():
    return {"status": "ok", "service": "telegram-ride-bot", "timestamp": datetime.now().isoformat()}

def run_flask_server():
    """Flask serverni ishga tushiradi"""
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"🌐 Flask server port {port} da ishga tushmoqda...")
    flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# Bot token va sozlamalar
BOT_TOKEN = "8289853358:AAEJsNKO3_v_IPbXjTx5VrYeddn5a426aFg"
CHANNEL_ID = "-1003236563110"
ADMIN_ID = 8014950410  # Bu int bo'lishi kerak

PAYMENT_AMOUNT = 5000

DATA_FILE = "ride_sharing_bot_data.json"
PAYMENTS_FILE = "payments_data.json"

# Global ma'lumotlar
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
                # JSON da kalitlar string, lekin biz int kerak
                user_data = {int(k): v for k, v in user_data.items()}
                driver_applications = data.get("driver_applications", {})
                passenger_applications = data.get("passenger_applications", {})
                application_counter = data.get("application_counter", 1)
                logger.info("✅ Asosiy ma'lumotlar yuklandi")
        
        if os.path.exists(PAYMENTS_FILE):
            with open(PAYMENTS_FILE, "r", encoding="utf-8") as f:
                payments_data = json.load(f)
                logger.info("✅ To'lov ma'lumotlari yuklandi")
    except Exception as e:
        logger.error(f"❌ Ma'lumotlarni yuklashda xato: {e}")
        # Fayl bo'lmasa yangisini yaratish
        save_data()

def save_data():
    try:
        # user_data kalitlarini string ga o'tkazish
        user_data_str = {str(k): v for k, v in user_data.items()}
        
        main_data = {
            "user_data": user_data_str,
            "driver_applications": driver_applications,
            "passenger_applications": passenger_applications,
            "application_counter": application_counter
        }
        
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(main_data, f, ensure_ascii=False, indent=4)
        
        with open(PAYMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(payments_data, f, ensure_ascii=False, indent=4)
        
        logger.info("✅ Ma'lumotlar saqlandi")
    except Exception as e:
        logger.error(f"❌ Ma'lumotlarni saqlashda xato: {e}")

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
    """24 soat ichida to'lov qilganmi tekshirish"""
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
    """To'lov yozuvini qo'shish"""
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
    """Haydovchilar ro'yxatini foydalanuvchiga yuborish"""
    active_drivers = []
    for app_id, driver in driver_applications.items():
        # Faqat tasdiqlangan haydovchilarni qo'shish
        if driver.get('status') == 'verified':
            active_drivers.append(driver)
    
    if not active_drivers:
        await context.bot.send_message(
            chat_id=user_id,
            text="🚗 *Haydovchilar ro'yxati*\n\nHozircha faol haydovchilar yo'q. Biroz vaqt o'tgach qayta urinib ko'ring.\n\n✅ To'lovingiz qabul qilindi va saqlandi.",
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
    
    await context.bot.send_message(
        chat_id=user_id,
        text=message, 
        parse_mode=ParseMode.MARKDOWN
    )

async def notify_admin_about_payment(context, user_id, payment_id, screenshot_id=None):
    """Admin ga to'lov haqida xabar berish"""
    try:
        user = await context.bot.get_chat(user_id)
        message = (
            f"💳 *TO'LOV TEKSHRIVI*\n\n"
            f"📋 **Foydalanuvchi ma'lumotlari:**\n"
            f"• Ism: {user.first_name}\n"
            f"• ID: {user_id}\n"
            f"• Summa: {PAYMENT_AMOUNT:,} so'm\n"
            f"• Vaqt: {datetime.now().strftime('%H:%M %d.%m.%Y')}\n"
            f"• To'lov ID: {payment_id}\n\n"
            f"🔍 *Screenshotni tekshiring:*\n"
            f"1. To'lov summasi to'g'rimi?\n"
            f"2. Screenshot aniq va ko'rinadimi?\n"
            f"3. To'lov vaqti to'g'rimi?\n\n"
            f"*Tasdiqlang yoki rad eting:*"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("✅ To'lovni tasdiqlash", callback_data=f'verify_{payment_id}'),
                InlineKeyboardButton("❌ To'lovni rad etish", callback_data=f'reject_{payment_id}')
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
        logger.info(f"📤 Adminga TO'LOV tekshiruvi uchun xabar yuborildi: {payment_id}")
    except Exception as e:
        logger.error(f"Adminga xabar yuborishda xato: {e}")

# ==================== HAYDOVCHI ARIZASINI YAKUNLASH ====================
async def complete_driver_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Haydovchi arizasini admin tasdiqlashi uchun yuborish"""
    try:
        user_id = update.effective_user.id
        
        # Foydalanuvchi ma'lumotlarini tekshirish
        if user_id not in user_data:
            await update.message.reply_text(
                "❌ Xatolik! Iltimos, qaytadan /start boshlang.", 
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Kerakli maydonlarni tekshirish
        required_fields = ['first_name', 'phone', 'car_type', 'price', 'car_photo']
        missing_fields = []
        
        for field in required_fields:
            if field not in user_data[user_id]:
                missing_fields.append(field)
        
        if missing_fields:
            await update.message.reply_text(
                f"❌ Quyidagi maydonlar to'ldirilmagan: {', '.join(missing_fields)}\nIltimos, qaytadan /start boshlang.", 
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Rolni o'rnatish
        user_data[user_id]['role'] = 'driver'
        
        # Ariza ID sini yaratish
        global application_counter
        app_id = f"D{application_counter:04d}"
        application_counter += 1
        
        # Ma'lumotlarni vaqtinchalik saqlash (admin tasdiqlashini kutish)
        driver_applications[app_id] = {
            'user_id': user_id,  # int saqlanadi
            'first_name': user_data[user_id]['first_name'],
            'phone': user_data[user_id]['phone'],
            'car_type': user_data[user_id]['car_type'],
            'price': user_data[user_id]['price'],
            'car_photo': user_data[user_id]['car_photo'],
            'date': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        # Admin uchun tasdiqlash keyboardi
        keyboard = [
            [InlineKeyboardButton("✅ Mashinani tasdiqlash", callback_data=f'admin_verify_driver_{app_id}'),
             InlineKeyboardButton("❌ Mashinani rad etish", callback_data=f'admin_reject_driver_{app_id}')]
        ]
        
        # Adminga xabar yuborish
        try:
            caption = (
                f"🚗 *MASHINA TEKSHRIVI*\n\n"
                f"📋 **Haydovchi ma'lumotlari:**\n"
                f"• ID: {app_id}\n"
                f"• Ism: {user_data[user_id]['first_name']}\n"
                f"• Telefon: {user_data[user_id]['phone']}\n"
                f"• Mashina: {user_data[user_id]['car_type']}\n"
                f"• Narx: {user_data[user_id]['price']}\n"
                f"• Vaqt: {datetime.now().strftime('%H:%M %d.%m.%Y')}\n\n"
                f"🔍 *Mashina rasmiga qarang va tekshiring:*\n"
                f"1. Rasm mashinaga tegishlimi?\n"
                f"2. Rasm aniq va ko'rinadimi?\n"
                f"3. Barcha ma'lumotlar to'grimi?\n\n"
                f"*Tasdiqlang yoki rad eting:*"
            )
            
            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=user_data[user_id]['car_photo'],
                caption=caption,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"📤 Adminga MASHINA TEKSHIRUVI uchun xabar yuborildi: {app_id}")
            
        except Exception as e:
            logger.error(f"⚠️ Adminga rasm yuborishda xato: {e}")
            text_message = (
                f"🚗 *MASHINA TEKSHRIVI*\n\n"
                f"📋 **Haydovchi ma'lumotlari:**\n"
                f"• ID: {app_id}\n"
                f"• Ism: {user_data[user_id]['first_name']}\n"
                f"• Telefon: {user_data[user_id]['phone']}\n"
                f"• Mashina: {user_data[user_id]['car_type']}\n"
                f"• Narx: {user_data[user_id]['price']}\n\n"
                f"⚠️ *RASM YUBORISHDA XATOLIK*\n\n"
                f"*Tasdiqlang yoki rad eting:*"
            )
            
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=text_message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        
        # Foydalanuvchiga xabar
        await update.message.reply_text(
            f"✅ *Rahmat, {user_data[user_id]['first_name']}!*\n\n"
            f"Haydovchi arizangiz qabul qilindi (ID: {app_id})\n\n"
            f"⏳ *Mashina rasm tekshiruvida...*\n"
            f"Admin mashina rasmni tekshiryapti. Natija sizga yuboriladi.\n\n"
            f"✅ **Tasdiqlansa** - siz haydovchilar ro'yxatiga qo'shilasiz\n"
            f"❌ **Rad etilsa** - sizga sababi bilan xabar beriladi\n\n"
            f"⏱️ *Kuting, tez orada javob olasiz...*",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # User_states dan o'chirish
        if user_id in user_states:
            del user_states[user_id]
        
        # Ma'lumotlarni saqlash
        save_data()
        
        logger.info(f"✅ Haydovchi arizasi #{app_id} admin tekshiruviga yuborildi")
        
    except Exception as e:
        logger.error(f"❌ complete_driver_application da xato: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(
            "❌ Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring yoki admin bilan bog'laning.",
            parse_mode=ParseMode.MARKDOWN
        )

# ==================== ADMIN HAYDOVCHI TASDIQLASH HANDLERI ====================
# ==================== ADMIN HAYDOVCHI TASDIQLASH HANDLERI ====================
# ==================== ADMIN HAYDOVCHI TASDIQLASH HANDLERI ====================
async def admin_driver_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin haydovchi arizasini tasdiqlash yoki rad etish"""
    query = update.callback_query
    
    try:
        await query.answer()
    except:
        pass
    
    if query.from_user.id != ADMIN_ID:
        try:
            await query.answer("Siz admin emassiz!", show_alert=True)
        except:
            pass
        return
    
    callback_data = query.data
    logger.info(f"🚗 Admin action: {callback_data}")
    
    try:
        if 'admin_' not in callback_data:
            logger.error(f"❌ Noto'g'ri callback format: {callback_data}")
            return
        
        # ✅ TO'G'RI AJRATISH
        # callback_data: "admin_verify_driver_D0001" yoki "admin_reject_driver_D0001"
        # parts = ['admin', 'verify', 'driver', 'D0001']
        parts = callback_data.split('_')
        
        # Tekshirish
        if len(parts) != 4:
            logger.error(f"❌ Noto'g'ri callback format: {parts}")
            await query.answer("Noto'g'ri format!", show_alert=True)
            return
        
        action = parts[1]  # 'verify' yoki 'reject' (parts[1] bo'lishi kerak!)
        driver_type = parts[2]  # 'driver'
        app_id = parts[3]  # 'D0001'
        
        logger.info(f"🔧 Action: {action}, Driver Type: {driver_type}, App ID: {app_id}")
        
        if action not in ['verify', 'reject']:
            logger.error(f"❌ Noto'g'ri action: {action}")
            await query.answer("Noto'g'ri action!", show_alert=True)
            return
        
        # Ariza topish
        if app_id not in driver_applications:
            logger.error(f"❌ Ariza topilmadi: {app_id}")
            await query.answer(f"Ariza topilmadi! ID: {app_id}", show_alert=True)
            return
        
        driver_app = driver_applications[app_id]
        logger.info(f"🔍 Driver app ma'lumotlari: {driver_app}")
        
        # USER_ID ni olish
        user_id = driver_app.get('user_id')
        logger.info(f"🔍 Original user_id: {user_id}, type: {type(user_id)}")
        
        if user_id is None:
            logger.error(f"❌ user_id None!")
            await query.answer("Xatolik: user_id topilmadi", show_alert=True)
            return
        
        # Agar string bo'lsa, int ga o'tkazish
        if isinstance(user_id, str):
            try:
                user_id = int(user_id)
                logger.info(f"🔄 user_id stringdan int ga o'tkazildi: {user_id}")
            except ValueError as e:
                logger.error(f"❌ user_id ni int ga o'tkazib bo'lmadi: {user_id}")
                await query.answer("Xatolik: user_id noto'g'ri", show_alert=True)
                return
        
        logger.info(f"👤 Final user_id: {user_id}, type: {type(user_id)}")
        
        # ================ TASDIQLASH ================
        if action == 'verify':
            driver_app['status'] = 'verified'
            driver_app['verified_by'] = query.from_user.id
            driver_app['verified_at'] = datetime.now().isoformat()
            
            logger.info(f"✅ Haydovchi tasdiqlandi: {app_id}")
            
            # 1. FOYDALANUVCHIGA XABAR
            try:
                user_message = (
                    f"✅ *Tabriklaymiz, {driver_app['first_name']}!*\n\n"
                    f"Sizning haydovchi arizangiz tasdiqlandi (ID: {app_id})\n\n"
                    f"🚗 Endi siz haydovchilar ro'yxatidasiz\n"
                    f"👥 Yo'lovchilar siz bilan bog'lanishi mumkin\n"
                    f"💰 Siz belgilagan narx: {driver_app['price']}\n\n"
                    f"✅ *Muvaffaqiyatli safarlar!*"
                )
                
                logger.info(f"📤 Foydalanuvchiga xabar yuborilmoqda: user_id={user_id}")
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=user_message,
                    parse_mode=ParseMode.MARKDOWN
                )
                
                logger.info(f"✅ Foydalanuvchiga xabar yuborildi: {user_id}")
                
            except Exception as e:
                logger.error(f"❌ Foydalanuvchiga xabar yuborishda xato: {e}")
                await query.answer(f"Xatolik: {str(e)[:50]}", show_alert=True)
            
            # 2. KANALGA XABAR
            try:
                channel_text = (
                    f"🚗 YANGI HAYDOVCHI QO'SHILDI #{app_id}\n\n"
                    f"👤 Ism: {driver_app['first_name']}\n"
                    f"📞 Telefon: {driver_app['phone']}\n"
                    f"🚘 Mashina: {driver_app['car_type']}\n"
                    f"💰 Narx: {driver_app['price']}\n"
                    f"🕐 Qo'shilgan: {datetime.now().strftime('%H:%M %d.%m.%Y')}"
                )
                
                await context.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=channel_text
                )
                logger.info(f"📤 Kanalga xabar yuborildi")
                
            except Exception as e:
                logger.error(f"⚠️ Kanalga xabar yuborishda xato: {e}")
            
            # 3. ADMIN XABARINI YANGILASH
            try:
                await query.edit_message_text(
                    f"✅ *HAYDOVCHI TASDIQLANDI!* #{app_id}\n\n"
                    f"👤 {driver_app['first_name']}\n"
                    f"📞 {driver_app['phone']}\n"
                    f"🚘 {driver_app['car_type']}\n"
                    f"💰 {driver_app['price']}\n\n"
                    f"✅ Kanalga qo'shildi.\n"
                    f"✅ Foydalanuvchiga xabar yuborildi.",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Admin xabarini yangilashda xato: {e}")
                
        # ================ RAD ETISH ================
        elif action == 'reject':
            driver_app['status'] = 'rejected'
            driver_app['rejected_by'] = query.from_user.id
            driver_app['rejected_at'] = datetime.now().isoformat()
            
            logger.info(f"❌ Haydovchi rad etildi: {app_id}")
            
            # 1. FOYDALANUVCHIGA RAD ETISH XABARI
            try:
                reject_message = (
                    f"❌ *Arizangiz rad etildi* (ID: {app_id})\n\n"
                    f"Sabablar:\n"
                    f"• Mashina rasmida muammo\n"
                    f"• Noto'g'ri ma'lumotlar\n"
                    f"• Rasm mashinaga tegishli emas\n\n"
                    f"ℹ️ Qaytadan urinib ko'rishingiz mumkin. /start"
                )
                
                logger.info(f"📤 Rad etish xabari yuborilmoqda: user_id={user_id}")
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=reject_message,
                    parse_mode=ParseMode.MARKDOWN
                )
                
                logger.info(f"📩 Rad etish xabari yuborildi: {user_id}")
                
            except Exception as e:
                logger.error(f"❌ Rad etish xabari yuborishda xato: {e}")
                await query.answer(f"Xatolik: {str(e)[:50]}", show_alert=True)
            
            # 2. ADMIN XABARINI YANGILASH
            try:
                await query.edit_message_text(
                    f"❌ *HAYDOVCHI RAD ETILDI!* #{app_id}\n\n"
                    f"👤 {driver_app['first_name']}\n"
                    f"📞 {driver_app['phone']}\n"
                    f"🚘 {driver_app['car_type']}\n\n"
                    f"❌ Foydalanuvchiga rad etilganligi haqida xabar yuborildi.",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Admin rad etish xabarini yangilashda xato: {e}")
        
        # MA'LUMOTLARNI SAQLASH
        try:
            save_data()
            logger.info(f"💾 Ma'lumotlar saqlandi")
        except Exception as e:
            logger.error(f"❌ Saqlashda xato: {e}")
            
    except Exception as e:
        logger.error(f"❌ admin_driver_action da katta xato: {e}")
        import traceback
        traceback.print_exc()
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
    """Haydovchilar ro'yxatini ko'rish tugmasi"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    # user_data da kalitlar int, shuning uchun tekshirish
    if user_id not in user_data:
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
            f"Admin 5-10 daqiqa da tekshirib, ro'yxatni yuboradi.",
            reply_markup=confirm_payment_keyboard(),
            parse_mode=ParseMode.HTML
        )
    
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
            f"Admin 5-10 daqiqa da tekshirib, ro'yxatni yuboradi.",
            reply_markup=confirm_payment_keyboard(),
            parse_mode=ParseMode.HTML
        )
    
    elif query.data == 'cancel_payment':
        await query.edit_message_text(
            "❌ <b>To'lov bekor qilindi.</b>\n\n"
            "Bosh menyuga qaytish uchun /start ni bosing.",
            parse_mode=ParseMode.HTML
        )
    
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

async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Screenshot qabul qilish"""
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
    """Admin to'lovni tasdiqlash yoki rad etish"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        await query.answer("Siz admin emassiz!", show_alert=True)
        return
    
    if '_' not in query.data:
        return
    
    parts = query.data.split('_')
    if len(parts) < 2:
        return
    
    action = parts[0]  # verify yoki reject
    payment_id = '_'.join(parts[1:])  # pay_... qismi
    
    logger.info(f"💰 To'lov action: {action}, ID: {payment_id}")
    
    for user_id_str, payments in payments_data.items():
        for payment in payments:
            if payment['id'] == payment_id:
                if action == 'verify':
                    payment['status'] = 'verified'
                    payment['verified_by'] = query.from_user.id
                    payment['verified_at'] = datetime.now().isoformat()
                    
                    user_id_int = int(user_id_str)
                    await send_drivers_list_to_user(context, user_id_int)
                    
                    await context.bot.send_message(
                        chat_id=user_id_int,
                        text="✅ *To'lovingiz tasdiqlandi!*\n\nHaydovchilar ro'yxati sizga yuborildi. 24 soat davomida yangi haydovchilar qo'shilganda xabar olasiz.\n\nRahmat! 🚗",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                    try:
                        await query.edit_message_text(
                            f"✅ *To'lov tasdiqlandi!*\n\nFoydalanuvchiga haydovchilar ro'yxati yuborildi.",
                            parse_mode=ParseMode.MARKDOWN
                        )
                    except:
                        pass
                    
                elif action == 'reject':
                    payment['status'] = 'rejected'
                    payment['rejected_by'] = query.from_user.id
                    payment['rejected_at'] = datetime.now().isoformat()
                    
                    await context.bot.send_message(
                        chat_id=int(user_id_str),
                        text="❌ *To'lov rad etildi!*\n\nSizning to'lovingiz tasdiqlanmadi. Sabab:\n• Screenshot noaniq\n• To'lov summasi noto'g'ri\n• Boshqa xatolik\n\nQayta urinib ko'ring yoki admin bilan bog'laning.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    
                    try:
                        await query.edit_message_text(
                            f"❌ *To'lov rad etildi!*\n\nFoydalanuvchiga rad etilganligi haqida xabar yuborildi.",
                            parse_mode=ParseMode.MARKDOWN
                        )
                    except:
                        pass
                
                save_data()
                return
    
    await query.answer("To'lov topilmadi!", show_alert=True)

# ==================== BUTTON HANDLER ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Barcha callback querylarni boshqarish"""
    query = update.callback_query
    user_id = query.from_user.id
    callback_data = query.data
    
    logger.info(f"🔔 Callback query: {callback_data} from user {user_id}")
    
    # ✅ Birinchi navbatda callback query ni javob berish
    try:
        await query.answer()
    except Exception as e:
        logger.warning(f"⚠️ answer() xatosi: {e}")
        # Agar answer() ishlamasa ham davom etamiz
    
    try:
        if callback_data == 'role_driver':
            user_states[user_id] = 'registering_driver_name'
            await query.edit_message_text('Iltimos, ismingizni kiriting:')
            
        elif callback_data == 'role_passenger':
            user_states[user_id] = 'registering_passenger_name'
            await query.edit_message_text('Iltimos, ismingizni kiriting:')
            
        elif callback_data.startswith('car_type_'):
            car_type = callback_data[9:]
            if user_id not in user_data:
                user_data[user_id] = {}
            user_data[user_id]['car_type'] = car_type
            user_states[user_id] = 'registering_driver_price'
            await query.edit_message_text('Bir safar narxini kiriting (masalan: 150000 soʻm):')
            
        elif callback_data.startswith('car_pref_'):
            pref = callback_data[9:]
            if user_id not in user_data:
                user_data[user_id] = {}
            user_data[user_id]['car_preference'] = pref
            user_states[user_id] = 'registering_passenger_time'
            await query.edit_message_text('Qachon joʻnamoqchisiz?', reply_markup=time_keyboard())
            
        elif callback_data.startswith('time_'):
            time_text = callback_data[5:]
            if time_text == 'Boshqa':
                user_states[user_id] = 'registering_passenger_time_manual'
                await query.edit_message_text('Vaqtni oʻzingiz yozing (masalan: 15:30, ertaga soat 10:00):')
            else:
                user_data[user_id]['departure_time'] = time_text
                await complete_passenger_application(update, context)
                
        elif callback_data == 'show_drivers':
            await show_drivers_callback(update, context)
            
        elif callback_data in ['pay_card', 'pay_click', 'pay_payme', 'cancel_payment', 'confirm_payment']:
            await payment_method_callback(update, context)
            
        elif callback_data.startswith('verify_') or callback_data.startswith('reject_'):
            logger.info(f"📞 To'lov tasdiqlash callback: {callback_data}")
            await admin_payment_action(update, context)
            
        elif callback_data.startswith('admin_verify_driver_') or callback_data.startswith('admin_reject_driver_'):
            logger.info(f"🚗 Haydovchi tasdiqlash callback: {callback_data}")
            await admin_driver_action(update, context)
            
        else:
            logger.warning(f"⚠️ Noma'lum callback: {callback_data}")
            try:
                await query.answer("Noma'lum tugma!", show_alert=True)
            except:
                pass
                
    except Exception as e:
        logger.error(f"❌ button_handler da xato: {e}")
        try:
            await query.answer(f"Xatolik: {str(e)[:50]}...", show_alert=True)
        except:
            pass

# ==================== MESSAGE HANDLER ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Barcha matnli xabarlarni boshqarish"""
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
            user_data[user_id]['departure'] = f"Location: {message.location.latitude}, {message.location.longitude}"
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
            user_data[user_id]['destination'] = f"Location: {message.location.latitude}, {message.location.longitude}"
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

# ==================== YO'LOVCHI ARIZASINI YAKUNLASH ====================
async def complete_passenger_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yo'lovchi arizasini yakunlash"""
    try:
        # Foydalanuvchi ma'lumotlarini olish
        if hasattr(update, 'callback_query'):
            user_id = update.callback_query.from_user.id
            chat_id = update.callback_query.message.chat_id
            message_to_reply = update.callback_query.message
            is_callback = True
        elif hasattr(update, 'message'):
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
            message_to_reply = update.message
            is_callback = False
        else:
            logger.error("❌ Xato: update obyektida message yoki callback_query topilmadi")
            return
        
        logger.info(f"🔍 Foydalanuvchi {user_id} uchun ariza yakunlanmoqda...")
        
        # Foydalanuvchi ma'lumotlarini tekshirish
        if user_id not in user_data:
            if is_callback:
                await message_to_reply.edit_text("❌ Xatolik! Iltimos, qaytadan /start boshlang.")
            else:
                await message_to_reply.reply_text("❌ Xatolik! Iltimos, qaytadan /start boshlang.")
            return
        
        # Kerakli maydonlarni tekshirish
        required_fields = ['first_name', 'phone', 'car_preference', 'departure_time']
        missing_fields = []
        
        for field in required_fields:
            if field not in user_data[user_id]:
                missing_fields.append(field)
        
        if missing_fields:
            logger.warning(f"❌ Yetishmayotgan maydonlar: {missing_fields}")
            error_text = f"❌ Quyidagi maydonlar to'ldirilmagan: {', '.join(missing_fields)}\nIltimos, qaytadan /start boshlang."
            
            if is_callback:
                await message_to_reply.edit_text(error_text)
            else:
                await context.bot.send_message(chat_id=chat_id, text=error_text)
            return
        
        # Rolni o'rnatish
        user_data[user_id]['role'] = 'passenger'
        
        # Ariza ID sini yaratish
        global application_counter
        app_id = f"P{application_counter:04d}"
        application_counter += 1
        
        # Ma'lumotlarni saqlash
        passenger_applications[app_id] = {
            'user_id': user_id,
            'first_name': user_data[user_id]['first_name'],
            'phone': user_data[user_id]['phone'],
            'departure': user_data[user_id].get('departure'),
            'departure_location': user_data[user_id].get('departure_location'),
            'destination': user_data[user_id].get('destination'),
            'destination_location': user_data[user_id].get('destination_location'),
            'car_preference': user_data[user_id]['car_preference'],
            'departure_time': user_data[user_id]['departure_time'],
            'date': datetime.now().isoformat()
        }
        
        logger.info(f"✅ Ariza #{app_id} saqlandi")
        
        # Kanalga xabar yuborish
        departure_text = user_data[user_id].get('departure') or "Lokatsiya yuborilgan"
        destination_text = user_data[user_id].get('destination') or "Lokatsiya yuborilgan"
        
        application_text = (
            f"🚶 YANGI YOʻLOVCHI ARIZASI #{app_id}\n\n"
            f"Ism: {user_data[user_id]['first_name']}\n"
            f"Telefon: {user_data[user_id]['phone']}\n"
            f"Joʻnash: {departure_text}\n"
            f"Borish: {destination_text}\n"
            f"Mashina: {user_data[user_id]['car_preference']}\n"
            f"Vaqt: {user_data[user_id]['departure_time']}\n"
            f"User ID: {user_id}"
        )
        
        try:
            # Lokatsiyalarni yuborish
            if user_data[user_id].get('departure_location'):
                await context.bot.send_location(
                    chat_id=CHANNEL_ID,
                    latitude=user_data[user_id]['departure_location']['latitude'],
                    longitude=user_data[user_id]['departure_location']['longitude']
                )
            
            if user_data[user_id].get('destination_location'):
                await context.bot.send_location(
                    chat_id=CHANNEL_ID,
                    latitude=user_data[user_id]['destination_location']['latitude'],
                    longitude=user_data[user_id]['destination_location']['longitude']
                )
            
            # Asosiy xabarni yuborish
            await context.bot.send_message(chat_id=CHANNEL_ID, text=application_text)
            logger.info(f"📤 Kanalga xabar yuborildi: {CHANNEL_ID}")
            
        except Exception as e:
            logger.error(f"⚠️ Kanalga xabar yuborishda xato: {e}")
        
        # User_states dan o'chirish
        if user_id in user_states:
            del user_states[user_id]
        
        # Ma'lumotlarni saqlash
        save_data()
        
        # Foydalanuvchiga to'lov xabarini yuborish
        reply_text = (
            f"✅ Rahmat, {user_data[user_id]['first_name']}!\n"
            f"Yangi arizangiz qabul qilindi (ID: {app_id})\n\n"
            f"🚗 *Haydovchilar ro'yxatini ko'rish uchun 5,000 so'm to'lang*\n"
            f"24 soat davomida cheksiz haydovchilarni ko'rishingiz mumkin!\n\n"
            f"To'lov qilish uchun:"
        )
        
        # To'lov menyusini yuborish
        if is_callback:
            await message_to_reply.edit_text(
                reply_text,
                reply_markup=payment_methods_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=reply_text,
                reply_markup=payment_methods_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
        
        logger.info(f"💰 {user_id} ga to'lov menyusi yuborildi")
        
    except Exception as e:
        logger.error(f"❌ complete_passenger_application da katta xato: {e}")
        import traceback
        traceback.print_exc()
        try:
            if hasattr(update, 'callback_query'):
                await update.callback_query.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qaytadan /start boshlang.")
            else:
                await update.message.reply_text("❌ Xatolik yuz berdi. Iltimos, qaytadan /start boshlang.")
        except:
            pass

# ==================== BOSHQA FUNKSIYALAR ====================
async def my_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchining arizasini ko'rish"""
    user_id = update.effective_user.id
    
    # Haydovchi arizasini tekshirish
    for app_id, app in driver_applications.items():
        if app.get('user_id') == user_id:
            status_text = "⏳ Admin tasdiqlashini kutyapti"
            if app.get('status') == 'verified':
                status_text = "✅ Tasdiqlangan"
            elif app.get('status') == 'rejected':
                status_text = "❌ Rad etilgan"
            
            await update.message.reply_text(
                f"🚗 *Sizning haydovchi arizangiz* ({app_id})\n\n"
                f"👤 Ism: {app['first_name']}\n"
                f"📞 Telefon: {app['phone']}\n"
                f"🚘 Mashina: {app['car_type']}\n"
                f"💰 Narx: {app['price']}\n"
                f"📅 Sana: {app['date'][:10]}\n"
                f"📊 Status: {status_text}",
                parse_mode=ParseMode.MARKDOWN
            )
            return
    
    # Yo'lovchi arizasini tekshirish
    passenger_apps = []
    for app_id, app in passenger_applications.items():
        if app.get('user_id') == user_id:
            passenger_apps.append((app_id, app))
    
    if passenger_apps:
        app_id, app = passenger_apps[-1]
        departure = app.get('departure') or "Lokatsiya"
        destination = app.get('destination') or "Lokatsiya"
        
        await update.message.reply_text(
            f"🚶 *Sizning yoʻlovchi arizangiz* ({app_id})\n\n"
            f"👤 Ism: {app['first_name']}\n"
            f"📞 Telefon: {app['phone']}\n"
            f"📍 Joʻnash: {departure}\n"
            f"🎯 Borish: {destination}\n"
            f"🕐 Vaqt: {app['departure_time']}\n"
            f"🚗 Mashina: {app['car_preference']}\n"
            f"📅 Sana: {app['date'][:10]}",
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
    """Yordam komandasi"""
    await update.message.reply_text(
        "🚕 *Ride Sharing Bot - Yordam*\n\n/start - Botni ishga tushirish\n/myapp - Ariza holatini ko'rish\n/help - Yordam\n\n💰 *Xizmat narxi:* 5,000 so'm (yo'lovchidan)\n⏱️ *Access muddati:* 24 soat\n👥 *Haydovchilar:* Bepul ro'yxatdan o'tadi\n\n📞 *Admin:* @username (murojaat uchun)",
        parse_mode=ParseMode.MARKDOWN
    )

# ==================== ADMIN KOMANDALARI ====================
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin statistikasini ko'rish"""
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
    """Admin to'lovlar ro'yxatini ko'rish (to'liq ma'lumotlar)"""
    if update.effective_user.id != ADMIN_ID:
        return
    
    if not payments_data:
        await update.message.reply_text("📭 To'lovlar mavjud emas")
        return
    
    text = "💰 *TO'LOVLAR RO'YXATI*\n\n"
    
    total_amount = 0
    verified_amount = 0
    pending_amount = 0
    rejected_amount = 0
    
    all_payments = []
    
    # Barcha to'lovlarni yig'ish
    for user_id_str, payments in payments_data.items():
        for payment in payments:
            # Foydalanuvchi ma'lumotlarini olish
            user_name = "Noma'lum"
            user_phone = "Yo'q"
            
            user_id_int = int(user_id_str)
            if user_id_int in user_data:
                user_name = user_data[user_id_int].get('first_name', 'Noma\'lum')
                user_phone = user_data[user_id_int].get('phone', 'Yo\'q')
            
            payment['user_name'] = user_name
            payment['user_phone'] = user_phone
            payment['user_id'] = user_id_int
            
            all_payments.append(payment)
            
            # Statistika
            total_amount += payment['amount']
            if payment['status'] == 'verified':
                verified_amount += payment['amount']
            elif payment['status'] == 'pending':
                pending_amount += payment['amount']
            elif payment['status'] == 'rejected':
                rejected_amount += payment['amount']
    
    # Statistika
    text += f"📊 *STATISTIKA:*\n"
    text += f"• Jami to'lovlar: {len(all_payments)} ta\n"
    text += f"• Jami summa: {total_amount:,} so'm\n"
    text += f"• ✅ Tasdiqlangan: {verified_amount:,} so'm\n"
    text += f"• ⏳ Kutilayotgan: {pending_amount:,} so'm\n"
    text += f"• ❌ Rad etilgan: {rejected_amount:,} so'm\n\n"
    
    # Oxirgi 10 ta to'lov
    text += "🔄 *OXIRGI TO'LOVLAR:*\n\n"
    
    # Vaqt bo'yicha tartiblash (eng yangilari birinchi)
    all_payments.sort(key=lambda x: x['date'], reverse=True)
    
    for i, payment in enumerate(all_payments[:15], 1):
        status_emoji = "✅" if payment['status'] == 'verified' else "⏳" if payment['status'] == 'pending' else "❌"
        
        text += f"{i}. {status_emoji} *{payment['user_name']}*admin_paymentsCo\n"
        text += f"   📞 {payment['user_phone']}\n"
        text += f"   🆔 {payment['user_id']}\n"
        text += f"   💰 {payment['amount']:,} so'm\n"
        text += f"   💳 {payment['method']}\n"
        
        # Vaqtni formatlash
        try:
            payment_time = datetime.fromisoformat(payment['date']).strftime('%d.%m.%Y %H:%M')
            text += f"   🕐 {payment_time}\n"
        except:
            text += f"   📅 {payment['date'][:16]}\n"
        
        text += f"   📊 {payment['status'].upper()}\n"
        text += f"   🔗 ID: {payment['id']}\n"
        text += "   " + "─" * 20 + "\n"
    
    if len(all_payments) > 15:
        text += f"\n... va yana {len(all_payments) - 15} ta to'lov\n"
    
    # Xabar uzunligini tekshirish
    if len(text) > 4000:
        await update.message.reply_text(text[:4000], parse_mode=ParseMode.MARKDOWN)
        if len(text) > 4000:
            await update.message.reply_text(text[4000:], parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin broadcast xabar yuborish"""
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
                chat_id=user_id,  # user_id allaqachon int
                text=f"📢 *Admin xabari:*\n\n{message}",
                parse_mode=ParseMode.MARKDOWN
            )
            success += 1
        except Exception as e:
            logger.error(f"Xabar yuborishda xato user_id {user_id}: {e}")
            failed += 1
    
    await update.message.reply_text(
        f"✅ *Xabar yuborildi!*\n\n✅ Muvaffaqiyatli: {success}\n❌ Muvaffaqiyatsiz: {failed}",
        parse_mode=ParseMode.MARKDOWN
    )

# ==================== ADMIN KOMANDALARI ====================
async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin foydalanuvchilar ro'yxatini ko'rish (to'liq ma'lumotlar)"""
    if update.effective_user.id != ADMIN_ID:
        return
    
    # Agar hech qanday ma'lumot bo'lmasa
    if not user_data and not driver_applications and not passenger_applications:
        await update.message.reply_text("📭 Hozircha hech qanday ma'lumot mavjud emas")
        return
    
    text = "👥 *BARCHA FOYDALANUVCHILAR*\n\n"
    
    # 1. HAYDOVCHILAR
    if driver_applications:
        verified_count = len([d for d in driver_applications.values() if d.get('status') == 'verified'])
        pending_count = len([d for d in driver_applications.values() if d.get('status') == 'pending'])
        rejected_count = len([d for d in driver_applications.values() if d.get('status') == 'rejected'])
        
        text += f"🚗 *HAYDOVCHILAR: {len(driver_applications)} ta*\n"
        text += f"   ✅ Tasdiqlangan: {verified_count} ta\n"
        text += f"   ⏳ Kutilayotgan: {pending_count} ta\n"
        text += f"   ❌ Rad etilgan: {rejected_count} ta\n\n"
        
        # Tasdiqlangan haydovchilar
        if verified_count > 0:
            text += "   *Tasdiqlangan haydovchilar:*\n"
            verified_drivers = [d for d in driver_applications.values() if d.get('status') == 'verified']
            for i, driver in enumerate(verified_drivers[:10], 1):
                text += f"   {i}. {driver.get('first_name', 'Noma\'lum')}\n"
                text += f"      📞 {driver.get('phone', 'Yo\'q')}\n"
                text += f"      🚘 {driver.get('car_type', 'Yo\'q')}\n"
                text += f"      💰 {driver.get('price', 'Yo\'q')}\n"
                text += "      ──────────\n"
        
        text += "\n"
    
    # 2. YO'LOVCHILAR
    if passenger_applications:
        text += f"🚶 *YO'LOVCHILAR: {len(passenger_applications)} ta*\n\n"
        
        for i, (app_id, passenger) in enumerate(list(passenger_applications.items())[:10], 1):
            text += f"{i}. {passenger.get('first_name', 'Noma\'lum')}\n"
            text += f"   📞 {passenger.get('phone', 'Yo\'q')}\n"
            
            departure = passenger.get('departure', '')
            destination = passenger.get('destination', '')
            
            if departure and len(departure) > 30:
                departure = departure[:27] + "..."
            if destination and len(destination) > 30:
                destination = destination[:27] + "..."
            
            text += f"   📍 {departure or 'Yo\'q'}\n"
            text += f"   🎯 {destination or 'Yo\'q'}\n"
            text += f"   🚗 {passenger.get('car_preference', 'Yo\'q')}\n"
            text += f"   🕐 {passenger.get('departure_time', 'Yo\'q')}\n"
            text += f"   📅 {passenger.get('date', '')[:10]}\n"
            text += "   ──────────\n"
        
        if len(passenger_applications) > 10:
            text += f"\n... va yana {len(passenger_applications) - 10} ta yo'lovchi\n"
    
    # 3. RO'YXATDAN O'TGANLAR
    if user_data:
        drivers_in_user_data = len([u for u in user_data.values() if u.get('role') == 'driver'])
        passengers_in_user_data = len([u for u in user_data.values() if u.get('role') == 'passenger'])
        
        text += f"\n📋 *RO'YXATDAN O'TGANLAR: {len(user_data)} ta*\n"
        text += f"   🚗 Haydovchi: {drivers_in_user_data} ta\n"
        text += f"   🚶 Yo'lovchi: {passengers_in_user_data} ta\n"
        
        # Oxirgi 5 ta ro'yxatdan o'tgan
        text += "\n   *Oxirgi ro'yxatdan o'tganlar:*\n"
        recent_users = list(user_data.items())[-5:]
        for user_id_str, user_info in recent_users:
            role = "🚗" if user_info.get('role') == 'driver' else "🚶"
            text += f"   {role} {user_info.get('first_name', 'Noma\'lum')}\n"
            text += f"      📞 {user_info.get('phone', 'Yo\'q')}\n"
            if user_info.get('role') == 'driver':
                text += f"      🚘 {user_info.get('car_type', 'Yo\'q')}\n"
            text += "      ─\n"
    
    # Xabar uzunligini tekshirish
    if len(text) > 4000:
        # Ikki qismga bo'lish
        await update.message.reply_text(text[:4000], parse_mode=ParseMode.MARKDOWN)
        await update.message.reply_text(text[4000:8000] if len(text) > 8000 else text[4000:], 
                                       parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin statistikasini ko'rish"""
    if update.effective_user.id != ADMIN_ID:
        return
    
    total_users = len(user_data)
    total_drivers = len(driver_applications)
    total_passengers = len(passenger_applications)
    
    # Haydovchi statistikasi
    verified_drivers = len([d for d in driver_applications.values() if d.get('status') == 'verified'])
    pending_drivers = len([d for d in driver_applications.values() if d.get('status') == 'pending'])
    rejected_drivers = len([d for d in driver_applications.values() if d.get('status') == 'rejected'])
    
    # To'lov statistikasi
    total_payments = 0
    verified_payments = 0
    pending_payments = 0
    total_income = 0
    
    for user_payments in payments_data.values():
        for payment in user_payments:
            total_payments += 1
            if payment.get('status') == 'verified':
                verified_payments += 1
                total_income += PAYMENT_AMOUNT
            elif payment.get('status') == 'pending':
                pending_payments += 1
    
    stats_text = (
        f"📊 *BOT STATISTIKASI*\n\n"
        f"👥 *Umumiy foydalanuvchilar:* {total_users}\n"
        f"🚗 *Haydovchilar:* {total_drivers}\n"
        f"   ├ ✅ Tasdiqlangan: {verified_drivers}\n"
        f"   ├ ⏳ Kutilayotgan: {pending_drivers}\n"
        f"   └ ❌ Rad etilgan: {rejected_drivers}\n"
        f"🚶 *Yo'lovchilar:* {total_passengers}\n\n"
        f"💰 *TO'LOVLAR:*\n"
        f"• Umumiy to'lovlar: {total_payments}\n"
        f"• ✅ Tasdiqlangan: {verified_payments}\n"
        f"• ⏳ Kutilayotgan: {pending_payments}\n"
        f"• 💰 Daromad: {total_income:,} so'm\n\n"
        f"📅 *Bugun:* {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        f"📈 *Bot ishga tushgan:* {datetime.now().strftime('%d.%m.%Y')}"
    )
    
    await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)

async def admin_detailed_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Batafsil foydalanuvchilar ro'yxati (yangi versiya)"""
    if update.effective_user.id != ADMIN_ID:
        return
    
    text = "📋 *BARCHA MA'LUMOTLAR - Batafsil*\n\n"
    
    # 1. HAYDOVCHILAR (Batafsil)
    if driver_applications:
        verified_count = len([d for d in driver_applications.values() if d.get('status') == 'verified'])
        pending_count = len([d for d in driver_applications.values() if d.get('status') == 'pending'])
        rejected_count = len([d for d in driver_applications.values() if d.get('status') == 'rejected'])
        
        text += f"🚗 *HAYDOVCHILAR: {len(driver_applications)} ta*\n"
        text += f"   ✅ Tasdiqlangan: {verified_count} ta\n"
        text += f"   ⏳ Kutilayotgan: {pending_count} ta\n"
        text += f"   ❌ Rad etilgan: {rejected_count} ta\n\n"
        
        for app_id, driver in list(driver_applications.items())[:15]:
            status_emoji = "✅" if driver.get('status') == 'verified' else "⏳" if driver.get('status') == 'pending' else "❌"
            status_text = "Tasdiqlangan" if driver.get('status') == 'verified' else "Kutilayotgan" if driver.get('status') == 'pending' else "Rad etilgan"
            
            text += f"{status_emoji} *{driver.get('first_name', 'Noma\'lum')}* (#{app_id})\n"
            text += f"   📞 {driver.get('phone', 'Yo\'q')}\n"
            text += f"   👤 User ID: {driver.get('user_id', 'Noma\'lum')}\n"
            text += f"   🚘 {driver.get('car_type', 'Yo\'q')}\n"
            text += f"   💰 {driver.get('price', 'Yo\'q')}\n"
            text += f"   📊 Status: {status_text}\n"
            
            if driver.get('verified_at'):
                verified_time = datetime.fromisoformat(driver['verified_at']).strftime('%d.%m.%Y %H:%M')
                text += f"   ✅ Tasdiqlangan: {verified_time}\n"
            elif driver.get('rejected_at'):
                rejected_time = datetime.fromisoformat(driver['rejected_at']).strftime('%d.%m.%Y %H:%M')
                text += f"   ❌ Rad etilgan: {rejected_time}\n"
            
            text += f"   📅 {driver.get('date', '')[:10]}\n"
            text += "   " + "─" * 20 + "\n"
        
        if len(driver_applications) > 15:
            text += f"\n... va yana {len(driver_applications) - 15} ta haydovchi\n"
        
        text += "\n"
    
    # 2. YO'LOVCHILAR (Batafsil)
    if passenger_applications:
        text += f"🚶 *YO'LOVCHILAR: {len(passenger_applications)} ta*\n\n"
        
        for app_id, passenger in list(passenger_applications.items())[:15]:
            text += f"*{passenger.get('first_name', 'Noma\'lum')}* (#{app_id})\n"
            text += f"   📞 {passenger.get('phone', 'Yo\'q')}\n"
            text += f"   👤 User ID: {passenger.get('user_id', 'Noma\'lum')}\n"
            
            departure = passenger.get('departure', '')
            destination = passenger.get('destination', '')
            
            if departure:
                text += f"   📍 {departure[:40]}{'...' if len(departure) > 40 else ''}\n"
            if destination:
                text += f"   🎯 {destination[:40]}{'...' if len(destination) > 40 else ''}\n"
            
            text += f"   🚗 {passenger.get('car_preference', 'Yo\'q')}\n"
            text += f"   🕐 {passenger.get('departure_time', 'Yo\'q')}\n"
            text += f"   📅 {passenger.get('date', '')[:10]}\n"
            text += "   " + "─" * 20 + "\n"
        
        if len(passenger_applications) > 15:
            text += f"\n... va yana {len(passenger_applications) - 15} ta yo'lovchi\n"
    
    # 3. TO'LOV QILGANLAR
    if payments_data:
        paid_users = []
        total_payments = 0
        
        for user_id_str, payments in payments_data.items():
            for payment in payments:
                if payment.get('status') == 'verified':
                    total_payments += 1
                    
                    # Foydalanuvchi ma'lumotlarini olish
                    user_name = "Noma'lum"
                    user_phone = "Yo'q"
                    
                    user_id_int = int(user_id_str)
                    if user_id_int in user_data:
                        user_name = user_data[user_id_int].get('first_name', 'Noma\'lum')
                        user_phone = user_data[user_id_int].get('phone', 'Yo\'q')
                    
                    paid_users.append({
                        'name': user_name,
                        'phone': user_phone,
                        'user_id': user_id_int,
                        'amount': payment['amount'],
                        'date': payment['date'],
                        'method': payment['method']
                    })
        
        if paid_users:
            text += f"\n💰 *TO'LOV QILGANLAR: {len(paid_users)} ta foydalanuvchi*\n"
            text += f"   Jami to'lovlar: {total_payments} ta\n"
            text += f"   Jami summa: {sum([p['amount'] for p in paid_users]):,} so'm\n\n"
            
            for i, payment in enumerate(paid_users[:10], 1):
                text += f"{i}. *{payment['name']}*\n"
                text += f"   📞 {payment['phone']}\n"
                text += f"   👤 ID: {payment['user_id']}\n"
                text += f"   💰 {payment['amount']:,} so'm\n"
                text += f"   💳 {payment['method']}\n"
                
                try:
                    payment_time = datetime.fromisoformat(payment['date']).strftime('%d.%m.%Y')
                    text += f"   📅 {payment_time}\n"
                except:
                    text += f"   📅 {payment['date'][:10]}\n"
                
                text += "   " + "─" * 15 + "\n"
            
            if len(paid_users) > 10:
                text += f"\n... va yana {len(paid_users) - 10} ta to'lov qilgan foydalanuvchi\n"
    
    if not driver_applications and not passenger_applications and not payments_data:
        await update.message.reply_text("📭 Hozircha hech qanday ma'lumot mavjud emas")
        return
    
    # Xabar uzunligini tekshirish
    if len(text) > 4000:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for i, part in enumerate(parts, 1):
            if i == 1:
                await update.message.reply_text(part, parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text(f"*(davomi {i}/{len(parts)})*\n" + part, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# ==================== BOTNI ISHGA TUSHIRISH ====================
# ==================== BOTNI ISHGA TUSHIRISH ====================

def run_telegram_bot():
    """Telegram botni ishga tushiradi"""
    logger.info("🤖 Telegram bot ishga tushmoqda...")
    logger.info(f"💰 To'lov summasi: {PAYMENT_AMOUNT:,} so'm")
    logger.info(f"👑 Admin ID: {ADMIN_ID}")
    logger.info(f"📢 Kanal ID: {CHANNEL_ID}")
    logger.info("=" * 50)
    
    try:
        app = ApplicationBuilder() \
            .token(BOT_TOKEN) \
            .connect_timeout(30) \
            .read_timeout(30) \
            .write_timeout(30) \
            .pool_timeout(30) \
            .get_updates_connect_timeout(30) \
            .get_updates_read_timeout(30) \
            .get_updates_write_timeout(30) \
            .get_updates_pool_timeout(30) \
            .build()
        
        # Error handler
       
        
        # Command handlerlar
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("myapp", my_application))
        app.add_handler(CommandHandler("help", help_command))
        
        # Admin commandlar
        app.add_handler(CommandHandler("stats", admin_stats))
        app.add_handler(CommandHandler("payments", admin_payments))
        app.add_handler(CommandHandler("broadcast", admin_broadcast))
        app.add_handler(CommandHandler("users", admin_users))
        app.add_handler(CommandHandler("allusers", admin_detailed_users))  # Yangi komanda
        
        # Callback handler
        app.add_handler(CallbackQueryHandler(button_handler))
        
        # Message handlerlar
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.add_handler(MessageHandler(filters.PHOTO, handle_message))
        app.add_handler(MessageHandler(filters.LOCATION, handle_message))
        app.add_handler(MessageHandler(filters.CONTACT, handle_message))

        app.add_error_handler(error_handler)
        
        logger.info("✅ Bot ishga tushdi! Polling rejimida...")
        app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"❌ Botni ishga tushirishda xato: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # 1. Flask serverni alohida threadda ishga tushiramiz
    flask_thread = threading.Thread(target=run_flask_server, daemon=True)
    flask_thread.start()
    
    # 2. Asosiy threadda Telegram botni ishga tushiramiz
    run_telegram_bot()

