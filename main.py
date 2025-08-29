import time
import os
import requests
import json
import logging
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import asyncio
import threading

# .env faylni yuklash
load_dotenv()

# === Logging sozlamalari ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# === 1. Firebasega ulanish ===
def initialize_firebase():
    """Firebase admin SDK ni ishga tushirish"""
    try:
        SA_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "server-accaunt.json")
        
        logger.info(f"Service account fayl yo'li: {SA_PATH}")
        
        if not os.path.exists(SA_PATH):
            raise FileNotFoundError(f"Service account file topilmadi: {SA_PATH}")
        
        cred = credentials.Certificate(SA_PATH)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        logger.info("Firebase muvaffaqiyatli ishga tushirildi")
        return db
    except Exception as e:
        logger.error(f"Firebase ishga tushirishda xatolik: {e}")
        raise

# === 2. Telegram sozlamalari ===
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Debug: Environment variables tekshirish
logger.info(f"Bot Token mavjud: {'✅' if BOT_TOKEN else '❌'}")
logger.info(f"Chat ID mavjud: {'✅' if CHAT_ID else '❌'}")

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("TELEGRAM_TOKEN va TELEGRAM_CHAT_ID .env faylda o'rnatilishi kerak")

# Global database variable
db = None

# === 3. Klaviatura sozlamalari ===
def get_main_keyboard():
    """Asosiy klaviatura tugmalarini qaytarish"""
    keyboard = [
        [KeyboardButton("👨‍🏫 O'qituvchilar"), KeyboardButton("📊 Statistika")],
        [KeyboardButton("📈 O'qituvchilar statistikasi"), KeyboardButton("ℹ️ Yordam")],
        [KeyboardButton("🔄 Yangilash")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# === 4. Firebase ma'lumotlar bilan ishlash ===
def get_all_teachers():
    """Barcha o'qituvchilarni olish"""
    try:
        teachers = []
        docs = db.collection("teachers").stream()
        for doc in docs:
            data = doc.to_dict()
            teachers.append({
                'id': doc.id,
                'name': data.get('name', 'Nomsiz')
            })
        return teachers
    except Exception as e:
        logger.error(f"O'qituvchilarni olishda xatolik: {e}")
        return []

def get_all_users():
    """Barcha foydalanuvchilarni olish"""
    try:
        users = []
        docs = db.collection("users").stream()
        for doc in docs:
            data = doc.to_dict()
            users.append({
                'id': doc.id,
                'name': data.get('name', 'Nomsiz'),
                'role': data.get('role', 'Unknown'),
                'subject': data.get('subject', '—'),
                'totalPayments': data.get('totalPayments', 0),
                'totalStudents': data.get('totalStudents', 0),
                'password': data.get('password', '—')
            })
        return users
    except Exception as e:
        logger.error(f"Foydalanuvchilarni olishda xatolik: {e}")
        return []

def get_teachers_from_users():
    """Users kolleksiyasidan o'qituvchilarni olish"""
    try:
        teachers = []
        docs = db.collection("users").stream()
        for doc in docs:
            data = doc.to_dict()
            if data.get('role') == 'teacher':
                teachers.append({
                    'id': doc.id,
                    'name': data.get('name', 'Nomsiz'),
                    'subject': data.get('subject', '—'),
                    'totalPayments': data.get('totalPayments', 0),
                    'totalStudents': data.get('totalStudents', 0),
                    'password': data.get('password', '—')
                })
        return teachers
    except Exception as e:
        logger.error(f"O'qituvchilarni olishda xatolik: {e}")
        return []

def get_user_by_id(user_id):
    """User ID bo'yicha to'liq ma'lumotni olish"""
    try:
        doc = db.collection("users").document(user_id).get()
        if doc.exists:
            data = doc.to_dict()
            return {
                'id': doc.id,
                'name': data.get('name', 'Nomsiz'),
                'role': data.get('role', 'Unknown'),
                'subject': data.get('subject', '—'),
                'totalPayments': data.get('totalPayments', 0),
                'totalStudents': data.get('totalStudents', 0),
                'password': data.get('password', '—')
            }
        return None
    except Exception as e:
        logger.error(f"Foydalanuvchi ma'lumotlarini olishda xatolik: {e}")
        return None

def get_students_by_teacher(teacher_name):
    """O'qituvchi bo'yicha o'quvchilarni olish"""
    try:
        students = []
        docs = db.collection("students").stream()
        for doc in docs:
            data = doc.to_dict()
            teacher_info = data.get('teacher', {})
            
            # Teacher name ni tekshirish
            if isinstance(teacher_info, dict):
                current_teacher_name = teacher_info.get('name', '')
            else:
                current_teacher_name = str(teacher_info)
            
            if current_teacher_name == teacher_name:
                students.append({
                    'id': doc.id,
                    'surname': data.get('surname', data.get('surename', '—')),
                    'name': data.get('name', '—'),
                    'phone': data.get('phone', '—'),
                    'date': data.get('date', '—'),
                    'teacher': current_teacher_name
                })
        return students
    except Exception as e:
        logger.error(f"O'quvchilarni olishda xatolik: {e}")
        return []

def get_student_by_id(student_id):
    """Student ID bo'yicha to'liq ma'lumotni olish"""
    try:
        doc = db.collection("students").document(student_id).get()
        if doc.exists:
            data = doc.to_dict()
            return {
                'id': doc.id,
                'surname': data.get('surname', data.get('surename', '—')),
                'name': data.get('name', '—'),
                'phone': data.get('phone', '—'),
                'date': data.get('date', '—'),
                'teacher': data.get('teacher', {}).get('name', '—') if isinstance(data.get('teacher'), dict) else str(data.get('teacher', '—'))
            }
        return None
    except Exception as e:
        logger.error(f"O'quvchi ma'lumotlarini olishda xatolik: {e}")
        return None

def delete_student(student_id):
    """O'quvchini o'chirish"""
    try:
        db.collection("students").document(student_id).delete()
        logger.info(f"O'quvchi {student_id} o'chirildi")
        return True
    except Exception as e:
        logger.error(f"O'quvchini o'chirishda xatolik: {e}")
        return False

def get_statistics():
    """Umumiy statistikalarni olish"""
    try:
        # O'quvchilar soni
        students_count = len(list(db.collection("students").stream()))
        
        # O'qituvchilar soni
        teachers_count = len(list(db.collection("teachers").stream()))
        
        # Foydalanuvchilar soni
        users_count = len(list(db.collection("users").stream()))
        
        # Jami to'lovlar
        total_payments = 0
        users_docs = db.collection("users").stream()
        for doc in users_docs:
            data = doc.to_dict()
            payments = data.get('totalPayments', 0)
            if isinstance(payments, (int, float)):
                total_payments += payments
        
        return {
            'students': students_count,
            'teachers': teachers_count,
            'users': users_count,
            'total_payments': total_payments
        }
    except Exception as e:
        logger.error(f"Statistikalarni olishda xatolik: {e}")
        return None

# === 5. Telegram bot handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot boshlanishi"""
    await update.message.reply_text(
        "🎓 *O'quvchilar boshqaruv tizimi*\n\n"
        "Xush kelibsiz! Quyidagi tugmalar orqali tizimni boshqaring:",
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown'
    )

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Matn xabarlarni qayta ishlash"""
    text = update.message.text
    
    if text == "👨‍🏫 O'qituvchilar":
        await show_teachers_list(update.message)
    elif text == "📊 Statistika":
        await show_statistics(update.message)
    elif text == "📈 O'qituvchilar statistikasi":
        await show_teachers_statistics(update.message)
    elif text == "ℹ️ Yordam":
        await show_help(update.message)
    elif text == "🔄 Yangilash":
        await update.message.reply_text(
            "🔄 Ma'lumotlar yangilandi!",
            reply_markup=get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ Noto'g'ri buyruq. Quyidagi tugmalardan foydalaning:",
            reply_markup=get_main_keyboard()
        )

async def show_help(message):
    """Yordam bo'limi"""
    help_text = """ℹ️ *Yordam bo'limi*

🔹 *O'qituvchilar* - Barcha o'qituvchilar va ularning o'quvchilari ro'yxati
🔹 *Statistika* - Umumiy statistikalar va ma'lumotlar
🔹 *O'qituvchilar statistikasi* - Har bir o'qituvchi bo'yicha batafsil statistika
🔹 *Yangilash* - Ma'lumotlarni yangilash
🔹 *Yordam* - Bu bo'lim

*Qo'shimcha imkoniyatlar:*
• O'quvchi ma'lumotlarini ko'rish
• O'quvchilarni o'chirish
• Real-time yangilanishlar
• O'qituvchilar bo'yicha to'lovlar statistikasi

*Texnik yordam uchun: @Musurmon_dev*
*London Language Center* - O'quvchilar boshqaruv tizimi
"""
    
    await message.reply_text(
        help_text,
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown'
    )

async def show_statistics(message):
    """Statistikalarni ko'rsatish"""
    stats = get_statistics()
    
    if not stats:
        await message.reply_text(
            "❌ Statistikalarni olishda xatolik yuz berdi",
            reply_markup=get_main_keyboard()
        )
        return
    
    # To'lovlarni formatlash
    formatted_payments = f"{stats['total_payments']:,}".replace(',', ' ')
    
    stats_text = f"""📊 *Tizim statistikasi*

👥 *Foydalanuvchilar:* {stats['users']} ta
👨‍🏫 *O'qituvchilar:* {stats['teachers']} ta
🧑‍🎓 *O'quvchilar:* {stats['students']} ta
💰 *Jami to'lovlar:* {formatted_payments} so'm

📅 *Oxirgi yangilanish:* {datetime.now().strftime('%d.%m.%Y %H:%M')}"""
    
    await message.reply_text(
        stats_text,
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown'
    )

async def show_teachers_statistics(message):
    """O'qituvchilar statistikasini ko'rsatish"""
    teachers = get_teachers_from_users()
    
    if not teachers:
        await message.reply_text(
            "❌ O'qituvchilar statistikasi topilmadi",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Inline keyboard yaratish
    keyboard = []
    for teacher in teachers:
        # To'lovlarni formatlash
        formatted_payments = f"{teacher['totalPayments']:,}".replace(',', ' ')
        
        keyboard.append([
            InlineKeyboardButton(
                f"👨‍🏫 {teacher['name']} ({teacher['subject']})", 
                callback_data=f"teacher_stats_{teacher['id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🏠 Asosiy menu", callback_data="back_to_main")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Umumiy statistika
    total_payments = sum(teacher['totalPayments'] for teacher in teachers)
    total_students = sum(teacher['totalStudents'] for teacher in teachers)
    formatted_total = f"{total_payments:,}".replace(',', ' ')
    
    stats_text = f"""📈 *O'qituvchilar statistikasi*

👥 *Jami o'qituvchilar:* {len(teachers)} ta
🧑‍🎓 *Jami o'quvchilar:* {total_students} ta
💰 *Jami to'lovlar:* {formatted_total} so'm

📋 *Har bir o'qituvchi bo'yicha batafsil ma'lumot:*"""
    
    await message.reply_text(
        stats_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_teachers_list(message):
    """O'qituvchilar ro'yxatini ko'rsatish"""
    teachers = get_all_teachers()
    
    if not teachers:
        await message.reply_text(
            "❌ O'qituvchilar topilmadi",
            reply_markup=get_main_keyboard()
        )
        return
    
    keyboard = []
    for teacher in teachers:
        keyboard.append([
            InlineKeyboardButton(
                f"👨‍🏫 {teacher['name']}", 
                callback_data=f"teacher_{teacher['name']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🏠 Asosiy menu", callback_data="back_to_main")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message.reply_text(
        f"👨‍🏫 *O'qituvchilar ro'yxati:*\n\n"
        f"📊 Jami: {len(teachers)} ta o'qituvchi\n\n"
        "O'qituvchini tanlab, uning o'quvchilarini ko'ring:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline button handler"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "back_to_main":
        await query.edit_message_text(
            "🏠 Asosiy menu",
            reply_markup=InlineKeyboardMarkup([[]])
        )
    elif data.startswith("teacher_stats_"):
        teacher_id = data.replace("teacher_stats_", "")
        await show_teacher_detailed_stats(query, teacher_id)
    elif data.startswith("teacher_"):
        teacher_name = data.replace("teacher_", "")
        await show_students_by_teacher(query, teacher_name)
    elif data.startswith("student_"):
        student_id = data.replace("student_", "")
        await show_student_details(query, student_id)
    elif data.startswith("delete_"):
        student_id = data.replace("delete_", "")
        await delete_student_handler(query, student_id)
    elif data.startswith("back_to_students_"):
        teacher_name = data.replace("back_to_students_", "")
        await show_students_by_teacher(query, teacher_name)

async def show_teacher_detailed_stats(query, teacher_id):
    """O'qituvchi bo'yicha batafsil statistika"""
    teacher = get_user_by_id(teacher_id)
    
    if not teacher or teacher['role'] != 'teacher':
        await query.edit_message_text("❌ O'qituvchi topilmadi")
        return
    
    # To'lovlarni formatlash
    formatted_payments = f"{teacher['totalPayments']:,}".replace(',', ' ')
    
    # Faollik darajasini alohida o'zgaruvchiga ajratish
    if teacher['totalStudents'] > 5:
        activity_level = 'Yuqori'
    elif teacher['totalStudents'] > 0:
        activity_level = "O'rta"
    else:
        activity_level = 'Past'
    
    stats_text = f"""👨‍🏫 *{teacher['name']} - Batafsil statistika*

📚 *Fan:* {teacher['subject']}
🧑‍🎓 *O'quvchilar soni:* {teacher['totalStudents']} ta
💰 *Jami to'lovlar:* {formatted_payments} so'm
🔐 *Parol:* {teacher['password']}

📊 *Qo'shimcha ma'lumotlar:*
• Har bir o'quvchidan o'rtacha: {formatted_payments.split()[0] if teacher['totalStudents'] > 0 else '0'} so'm
• Faollik darajasi: {activity_level}"""
    
    keyboard = [
        [InlineKeyboardButton("📈 Statistikalar", callback_data="back_to_main")],
        [InlineKeyboardButton("🏠 Asosiy menu", callback_data="back_to_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        stats_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_students_by_teacher(query, teacher_name):
    """O'qituvchi bo'yicha o'quvchilarni ko'rsatish"""
    students = get_students_by_teacher(teacher_name)
    
    if not students:
        keyboard = [
            [InlineKeyboardButton("🏠 Asosiy menu", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"❌ *{teacher_name}* o'qituvchisida o'quvchilar topilmadi",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    keyboard = []
    for student in students:
        keyboard.append([
            InlineKeyboardButton(
                f"🧑‍🎓 {student['surname']} {student['name']}", 
                callback_data=f"student_{student['id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🏠 Asosiy menu", callback_data="back_to_main")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"👨‍🏫 *{teacher_name}* o'qituvchisining o'quvchilari:\n\n"
        f"📊 Jami: {len(students)} ta o'quvchi\n\n"
        "O'quvchini tanlab, to'liq ma'lumotini ko'ring:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_student_details(query, student_id):
    """O'quvchi to'liq ma'lumotlarini ko'rsatish"""
    student = get_student_by_id(student_id)
    
    if not student:
        await query.edit_message_text("❌ O'quvchi topilmadi")
        return
    
    # Sana formatini yaxshilash
    date_str = student['date']
    if date_str != '—':
        try:
            if isinstance(date_str, datetime):
                date_str = date_str.strftime('%d.%m.%Y %H:%M')
            else:
                date_str = str(date_str)
        except:
            date_str = str(date_str)
    
    text = f"""👤 *O'quvchi ma'lumotlari:*

🆔 *ID:* {student['id']}
👤 *Familiya:* {student['surname']}
🧑‍🎓 *Ismi:* {student['name']}
📞 *Telefon:* {student['phone']}
📅 *Sana:* {date_str}
👨‍🏫 *O'qituvchi:* {student['teacher']}"""
    
    keyboard = [
        [InlineKeyboardButton("🗑️ O'chirish", callback_data=f"delete_{student_id}")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data=f"back_to_students_{student['teacher']}")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def delete_student_handler(query, student_id):
    """O'quvchini o'chirish handler (yangilangan)"""
    student = get_student_by_id(student_id)
    
    if not student:
        await query.edit_message_text("❌ O'quvchi topilmadi")
        return
    
    # O'chirish jarayoni
    if delete_student(student_id):
        keyboard = [
            [InlineKeyboardButton("🏠 Asosiy menu", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ *O'quvchi muvaffaqiyatli o'chirildi!*\n\n"
            f"👤 {student['surname']} {student['name']}\n"
            f"👨‍🏫 O'qituvchi: {student['teacher']}\n\n"
            f"📢 *Barcha adminlarga notifikatsiya yuborildi*",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # Qo'shimcha notifikatsiya (bot orqali o'chirilganligi haqida)
        try:
            text = f"""🤖 *Bot orqali o'quvchi o'chirildi!*

👤 *O'chirilgan o'quvchi:* {student['surname']} {student['name']}
👨‍🏫 *O'qituvchi:* {student['teacher']}
🕐 *O'chirilgan vaqt:* {datetime.now().strftime('%d.%m.%Y %H:%M')}
👤 *Kim o'chirdi:* Bot admin"""
            
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, json={
                "chat_id": CHAT_ID,
                "text": text,
                "parse_mode": "Markdown"
            })
        except Exception as e:
            logger.error(f"Qo'shimcha notifikatsiya yuborishda xatolik: {e}")
    else:
        await query.edit_message_text("❌ O'quvchini o'chirishda xatolik")

# === 6. Yangi o'quvchi qo'shilganda notifikatsiya ===
def send_new_student_notification(student_data):
    """Yangi o'quvchi qo'shilganda notifikatsiya yuborish"""
    try:
        surname = student_data.get('surname', student_data.get('surename', '—'))
        name = student_data.get('name', '—')
        phone = student_data.get('phone', '—')
        date = student_data.get('date', '—')
        
        if date != '—':
            try:
                if isinstance(date, datetime):
                    date = date.strftime('%d.%m.%Y %H:%M')
                else:
                    date = str(date)
            except:
                date = str(date)
        
        teacher_info = student_data.get('teacher', {})
        teacher_name = '—'
        if isinstance(teacher_info, dict):
            teacher_name = teacher_info.get('name', '—')
        elif isinstance(teacher_info, str):
            teacher_name = teacher_info
        
        text = f"""🔔 *Yangi o'quvchi qo'shildi!*

👤 *Familiya:* {surname}
🧑‍🎓 *Ismi:* {name}
📞 *Telefon:* {phone}
📅 *Sana:* {date}
👨‍🏫 *O'qituvchi:* {teacher_name}"""
        
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        response = requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        })
        
        if response.status_code == 200:
            logger.info("Yangi o'quvchi notifikatsiyasi yuborildi")
            return True
        else:
            logger.error(f"Notifikatsiya yuborishda xatolik: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Notifikatsiya yuborishda xatolik: {e}")
        return False

# === 7. O'chirish notifikatsiyasi funksiyasi ===
def send_deleted_student_notification(student_data):
    """O'quvchi o'chirilganda notifikatsiya yuborish"""
    try:
        surname = student_data.get('surname', student_data.get('surename', '—'))
        name = student_data.get('name', '—')
        phone = student_data.get('phone', '—')
        date = student_data.get('date', '—')
        
        if date != '—':
            try:
                if isinstance(date, datetime):
                    date = date.strftime('%d.%m.%Y %H:%M')
                else:
                    date = str(date)
            except:
                date = str(date)
        
        teacher_info = student_data.get('teacher', {})
        teacher_name = '—'
        if isinstance(teacher_info, dict):
            teacher_name = teacher_info.get('name', '—')
        elif isinstance(teacher_info, str):
            teacher_name = teacher_info
        
        text = f"""🗑️ *O'quvchi o'chirildi!*

👤 *Familiya:* {surname}
🧑‍🎓 *Ismi:* {name}
📞 *Telefon:* {phone}
📅 *Sana:* {date}
👨‍🏫 *O'qituvchi:* {teacher_name}
🕐 *O'chirilgan vaqt:* {datetime.now().strftime('%d.%m.%Y %H:%M')}"""
        
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        response = requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        })
        
        if response.status_code == 200:
            logger.info("O'quvchi o'chirilish notifikatsiyasi yuborildi")
            return True
        else:
            logger.error(f"O'chirish notifikatsiyasini yuborishda xatolik: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"O'chirish notifikatsiyasini yuborishda xatolik: {e}")
        return False

# === 8. O'zgartirilgan notifikatsiyalar uchun yangi funksiya ===
def send_modified_student_notification(old_data, new_data):
    """O'quvchi ma'lumotlari o'zgartirilganda notifikatsiya"""
    try:
        # O'zgarishlarni aniqlash
        changes = []
        
        # Familiya o'zgarishi
        old_surname = old_data.get('surname', old_data.get('surename', '—'))
        new_surname = new_data.get('surname', new_data.get('surename', '—'))
        if old_surname != new_surname:
            changes.append(f"Familiya: {old_surname} → {new_surname}")
        
        # Ism o'zgarishi
        old_name = old_data.get('name', '—')
        new_name = new_data.get('name', '—')
        if old_name != new_name:
            changes.append(f"Ism: {old_name} → {new_name}")
        
        # Telefon o'zgarishi
        old_phone = old_data.get('phone', '—')
        new_phone = new_data.get('phone', '—')
        if old_phone != new_phone:
            changes.append(f"Telefon: {old_phone} → {new_phone}")
        
        # O'qituvchi o'zgarishi
        old_teacher = old_data.get('teacher', {})
        new_teacher = new_data.get('teacher', {})
        
        old_teacher_name = '—'
        new_teacher_name = '—'
        
        if isinstance(old_teacher, dict):
            old_teacher_name = old_teacher.get('name', '—')
        elif isinstance(old_teacher, str):
            old_teacher_name = old_teacher
            
        if isinstance(new_teacher, dict):
            new_teacher_name = new_teacher.get('name', '—')
        elif isinstance(new_teacher, str):
            new_teacher_name = new_teacher
        
        if old_teacher_name != new_teacher_name:
            changes.append(f"O'qituvchi: {old_teacher_name} → {new_teacher_name}")
        
        if changes:
            text = f"""✏️ *O'quvchi ma'lumotlari o'zgartirildi!*

👤 *O'quvchi:* {new_surname} {new_name}
📝 *O'zgarishlar:*
{chr(10).join(f'• {change}' for change in changes)}
🕐 *O'zgartirilgan vaqt:* {datetime.now().strftime('%d.%m.%Y %H:%M')}"""
            
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            response = requests.post(url, json={
                "chat_id": CHAT_ID,
                "text": text,
                "parse_mode": "Markdown"
            })
            
            if response.status_code == 200:
                logger.info("O'quvchi o'zgarishi notifikatsiyasi yuborildi")
                return True
            else:
                logger.error(f"O'zgarish notifikatsiyasini yuborishda xatolik: {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"O'zgarish notifikatsiyasini yuborishda xatolik: {e}")
        return False

# === 9. To'liq Real-time listener (barcha o'zgarishlar bilan) ===
def setup_complete_realtime_listener():
    """Barcha real-time o'zgarishlarni kuzatish"""
    
    # O'zgartirilgan ma'lumotlarni saqlash uchun
    old_documents = {}
    
    def on_snapshot(col_snapshot, changes, read_time):
        """Firestore o'zgarishlarni qayta ishlash"""
        for change in changes:
            # Yangi qo'shilgan o'quvchilar
            if change.type.name == 'ADDED':
                doc_data = change.document.to_dict()
                
                # Yangi hujjat ma'lumotlarini saqlash
                old_documents[change.document.id] = doc_data
                
                if not doc_data.get('notified', False):
                    logger.info(f"Yangi o'quvchi topildi: {change.document.id}")
                    
                    if send_new_student_notification(doc_data):
                        try:
                            change.document.reference.update({
                                "notified": True,
                                "notification_sent_at": firestore.SERVER_TIMESTAMP
                            })
                            logger.info(f"O'quvchi {change.document.id} notified qilindi")
                        except Exception as e:
                            logger.error(f"Notified flagini o'rnatishda xatolik: {e}")
            
            # O'chirilgan o'quvchilar
            elif change.type.name == 'REMOVED':
                doc_data = change.document.to_dict()
                logger.info(f"O'quvchi o'chirildi: {change.document.id}")
                send_deleted_student_notification(doc_data)
                
                # O'chirilgan hujjatni eski ma'lumotlardan ham o'chirish
                if change.document.id in old_documents:
                    del old_documents[change.document.id]
            
            # O'zgartirilgan o'quvchilar
            elif change.type.name == 'MODIFIED':
                doc_data = change.document.to_dict()
                doc_id = change.document.id
                
                logger.info(f"O'quvchi o'zgartirildi: {doc_id}")
                
                # Agar eski ma'lumot mavjud bo'lsa, solishtirish
                if doc_id in old_documents:
                    old_data = old_documents[doc_id]
                    send_modified_student_notification(old_data, doc_data)
                else:
                    # Oddiy o'zgarish notifikatsiyasi
                    try:
                        surname = doc_data.get('surname', doc_data.get('surename', '—'))
                        name = doc_data.get('name', '—')
                        
                        text = f"""✏️ *O'quvchi ma'lumotlari yangilandi!*

👤 *O'quvchi:* {surname} {name}
🆔 *ID:* {doc_id}
🕐 *Yangilangan vaqt:* {datetime.now().strftime('%d.%m.%Y %H:%M')}

_Batafsil o'zgarishlarni ko'rish uchun botdan o'quvchi ma'lumotlarini tekshiring._"""
                        
                        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                        requests.post(url, json={
                            "chat_id": CHAT_ID,
                            "text": text,
                            "parse_mode": "Markdown"
                        })
                        
                        logger.info("O'quvchi yangilanish notifikatsiyasi yuborildi")
                    except Exception as e:
                        logger.error(f"Yangilanish notifikatsiyasini yuborishda xatolik: {e}")
                
                # Yangi ma'lumotni saqlash
                old_documents[doc_id] = doc_data
    
    # Barcha students hujjatlarini kuzatish
    query = db.collection("students")
    query.on_snapshot(on_snapshot)
    logger.info("To'liq real-time listener ishga tushirildi (CRUD operatsiyalar)")

# === 10. Qo'shimcha notifikatsiya funksiyalari ===
def send_system_notification(message, notification_type="INFO"):
    """Tizim notifikatsiyalari yuborish"""
    try:
        emoji_map = {
            "INFO": "ℹ️",
            "SUCCESS": "✅", 
            "ERROR": "❌",
            "WARNING": "⚠️"
        }
        
        emoji = emoji_map.get(notification_type, "ℹ️")
        
        text = f"""{emoji} *Tizim xabari*

{message}

🕐 *Vaqt:* {datetime.now().strftime('%d.%m.%Y %H:%M')}"""
        
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        response = requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        })
        
        if response.status_code == 200:
            logger.info(f"Tizim notifikatsiyasi yuborildi: {notification_type}")
            return True
        else:
            logger.error(f"Tizim notifikatsiyasini yuborishda xatolik: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Tizim notifikatsiyasini yuborishda xatolik: {e}")
        return False

def send_daily_statistics():
    """Kunlik statistikalarni yuborish"""
    try:
        stats = get_statistics()
        if not stats:
            return False
        
        # To'lovlarni formatlash
        formatted_payments = f"{stats['total_payments']:,}".replace(',', ' ')
        
        text = f"""📈 *Kunlik statistika hisoboti*

📅 *Sana:* {datetime.now().strftime('%d.%m.%Y')}

👥 *Foydalanuvchilar:* {stats['users']} ta
👨‍🏫 *O'qituvchilar:* {stats['teachers']} ta
🧑‍🎓 *O'quvchilar:* {stats['students']} ta
💰 *Jami to'lovlar:* {formatted_payments} so'm

🏢 *London Language Center*"""
        
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        response = requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        })
        
        if response.status_code == 200:
            logger.info("Kunlik statistika yuborildi")
            return True
        else:
            logger.error(f"Kunlik statistika yuborishda xatolik: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Kunlik statistika yuborishda xatolik: {e}")
        return False

# === 11. Backup va debug funksiyalari ===
async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Backup yaratish buyrugi"""
    try:
        # Barcha ma'lumotlarni olish
        students = []
        teachers = get_all_teachers()
        users = get_all_users()
        
        # O'quvchilar ma'lumotlarini olish
        docs = db.collection("students").stream()
        for doc in docs:
            data = doc.to_dict()
            students.append({
                'id': doc.id,
                **data
            })
        
        backup_data = {
            'timestamp': datetime.now().isoformat(),
            'students': students,
            'teachers': teachers,
            'users': users,
            'statistics': get_statistics()
        }
        
        # JSON faylga saqlash
        backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(backup_filename, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        
        await update.message.reply_text(
            f"✅ *Backup yaratildi!*\n\n"
            f"📁 *Fayl nomi:* {backup_filename}\n"
            f"📊 *O'quvchilar:* {len(students)} ta\n"
            f"👨‍🏫 *O'qituvchilar:* {len(teachers)} ta\n"
            f"👥 *Foydalanuvchilar:* {len(users)} ta",
            parse_mode='Markdown'
        )
        
        # Tizim notifikatsiyasi
        send_system_notification(
            f"Backup yaratildi: {backup_filename}\nJami ma'lumotlar: {len(students) + len(teachers) + len(users)} ta",
            "SUCCESS"
        )
        
    except Exception as e:
        logger.error(f"Backup yaratishda xatolik: {e}")
        await update.message.reply_text(f"❌ Backup yaratishda xatolik: {str(e)}")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tizim holati ko'rsatish"""
    try:
    import time
import os
import requests
import json
import logging
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import asyncio
import threading

# .env faylni yuklash
load_dotenv()

# === Logging sozlamalari ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# === ADMIN TIZIMI ===
ADMIN_IDS = []
try:
    admin_ids_str = os.getenv("ADMIN_IDS", "")
    if admin_ids_str:
        ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]
    logger.info(f"Admin IDs yuklandi: {len(ADMIN_IDS)} ta admin")
except Exception as e:
    logger.error(f"Admin ID larni yuklashda xatolik: {e}")

def is_admin(user_id):
    """Foydalanuvchi admin ekanligini tekshirish"""
    return int(user_id) in ADMIN_IDS

def add_admin(user_id):
    """Yangi admin qo'shish"""
    try:
        user_id = int(user_id)
        if user_id not in ADMIN_IDS:
            ADMIN_IDS.append(user_id)
            logger.info(f"Yangi admin qo'shildi: {user_id}")
            return True
        return False
    except:
        return False

def remove_admin(user_id):
    """Adminni o'chirish"""
    try:
        user_id = int(user_id)
        if user_id in ADMIN_IDS:
            ADMIN_IDS.remove(user_id)
            logger.info(f"Admin o'chirildi: {user_id}")
            return True
        return False
    except:
        return False

# === Firebase sozlamalari ===
def initialize_firebase():
    """Firebase admin SDK ni ishga tushirish"""
    try:
        SA_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "server-accaunt.json")
        logger.info(f"Service account fayl yo'li: {SA_PATH}")
        
        if not os.path.exists(SA_PATH):
            raise FileNotFoundError(f"Service account file topilmadi: {SA_PATH}")
        
        # Firebase app allaqachon ishga tushirilganligini tekshirish
        try:
            firebase_admin.get_app()
            logger.info("Firebase allaqachon ishga tushirilgan")
        except ValueError:
            # Agar app mavjud bo'lmasa, yangi app yaratish
            cred = credentials.Certificate(SA_PATH)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase muvaffaqiyatli ishga tushirildi")
        
        db = firestore.client()
        return db
    except Exception as e:
        logger.error(f"Firebase ishga tushirishda xatolik: {e}")
        raise

# === Telegram sozlamalari ===
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

logger.info(f"Bot Token mavjud: {'✅' if BOT_TOKEN else '❌'}")
logger.info(f"Chat ID mavjud: {'✅' if CHAT_ID else '❌'}")

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("TELEGRAM_TOKEN va TELEGRAM_CHAT_ID .env faylda o'rnatilishi kerak")

# Global database variable
db = None

# === Klaviatura sozlamalari ===
def get_main_keyboard(user_id=None):
    """Foydalanuvchi darajasiga qarab klaviatura qaytarish"""
    if is_admin(user_id):
        keyboard = [
            [KeyboardButton("👨‍🏫 O'qituvchilar"), KeyboardButton("📊 Statistika")],
            [KeyboardButton("📈 O'qituvchilar statistikasi"), KeyboardButton("ℹ️ Yordam")],
            [KeyboardButton("🔄 Yangilash"), KeyboardButton("👑 Admin Panel")]
        ]
    else:
        keyboard = [
            [KeyboardButton("ℹ️ Yordam")]
        ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_keyboard():
    """Admin panel klaviaturasi"""
    keyboard = [
        [KeyboardButton("➕ Admin qo'shish"), KeyboardButton("➖ Admin o'chirish")],
        [KeyboardButton("👑 Admin ro'yxati"), KeyboardButton("📊 Tizim holati")],
        [KeyboardButton("🏠 Asosiy menu")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# === Firebase ma'lumotlar bilan ishlash ===
def get_all_teachers():
    """Barcha o'qituvchilarni olish"""
    try:
        teachers = []
        docs = db.collection("teachers").stream()
        for doc in docs:
            data = doc.to_dict()
            teachers.append({
                'id': doc.id,
                'name': data.get('name', 'Nomsiz')
            })
        return teachers
    except Exception as e:
        logger.error(f"O'qituvchilarni olishda xatolik: {e}")
        return []

def get_all_users():
    """Barcha foydalanuvchilarni olish"""
    try:
        users = []
        docs = db.collection("users").stream()
        for doc in docs:
            data = doc.to_dict()
            users.append({
                'id': doc.id,
                'name': data.get('name', 'Nomsiz'),
                'role': data.get('role', 'Unknown'),
                'subject': data.get('subject', '—'),
                'totalPayments': data.get('totalPayments', 0),
                'totalStudents': data.get('totalStudents', 0),
                'password': data.get('password', '—')
            })
        return users
    except Exception as e:
        logger.error(f"Foydalanuvchilarni olishda xatolik: {e}")
        return []

def get_teachers_from_users():
    """Users kolleksiyasidan o'qituvchilarni olish"""
    try:
        teachers = []
        docs = db.collection("users").stream()
        for doc in docs:
            data = doc.to_dict()
            if data.get('role') == 'teacher':
                teachers.append({
                    'id': doc.id,
                    'name': data.get('name', 'Nomsiz'),
                    'subject': data.get('subject', '—'),
                    'totalPayments': data.get('totalPayments', 0),
                    'totalStudents': data.get('totalStudents', 0),
                    'password': data.get('password', '—')
                })
        return teachers
    except Exception as e:
        logger.error(f"O'qituvchilarni olishda xatolik: {e}")
        return []

def get_user_by_id(user_id):
    """User ID bo'yicha to'liq ma'lumotni olish"""
    try:
        doc = db.collection("users").document(user_id).get()
        if doc.exists:
            data = doc.to_dict()
            return {
                'id': doc.id,
                'name': data.get('name', 'Nomsiz'),
                'role': data.get('role', 'Unknown'),
                'subject': data.get('subject', '—'),
                'totalPayments': data.get('totalPayments', 0),
                'totalStudents': data.get('totalStudents', 0),
                'password': data.get('password', '—')
            }
        return None
    except Exception as e:
        logger.error(f"Foydalanuvchi ma'lumotlarini olishda xatolik: {e}")
        return None

def get_students_by_teacher(teacher_name):
    """O'qituvchi bo'yicha o'quvchilarni olish"""
    try:
        students = []
        docs = db.collection("students").stream()
        for doc in docs:
            data = doc.to_dict()
            teacher_info = data.get('teacher', {})
            
            if isinstance(teacher_info, dict):
                current_teacher_name = teacher_info.get('name', '')
            else:
                current_teacher_name = str(teacher_info)
            
            if current_teacher_name == teacher_name:
                students.append({
                    'id': doc.id,
                    'surname': data.get('surname', data.get('surename', '—')),
                    'name': data.get('name', '—'),
                    'phone': data.get('phone', '—'),
                    'date': data.get('date', '—'),
                    'teacher': current_teacher_name
                })
        return students
    except Exception as e:
        logger.error(f"O'quvchilarni olishda xatolik: {e}")
        return []

def get_student_by_id(student_id):
    """Student ID bo'yicha to'liq ma'lumotni olish"""
    try:
        doc = db.collection("students").document(student_id).get()
        if doc.exists:
            data = doc.to_dict()
            return {
                'id': doc.id,
                'surname': data.get('surname', data.get('surename', '—')),
                'name': data.get('name', '—'),
                'phone': data.get('phone', '—'),
                'date': data.get('date', '—'),
                'teacher': data.get('teacher', {}).get('name', '—') if isinstance(data.get('teacher'), dict) else str(data.get('teacher', '—'))
            }
        return None
    except Exception as e:
        logger.error(f"O'quvchi ma'lumotlarini olishda xatolik: {e}")
        return None

def delete_student(student_id):
    """O'quvchini o'chirish"""
    try:
        db.collection("students").document(student_id).delete()
        logger.info(f"O'quvchi {student_id} o'chirildi")
        return True
    except Exception as e:
        logger.error(f"O'quvchini o'chirishda xatolik: {e}")
        return False

def get_statistics():
    """Umumiy statistikalarni olish"""
    try:
        students_count = len(list(db.collection("students").stream()))
        teachers_count = len(list(db.collection("teachers").stream()))
        users_count = len(list(db.collection("users").stream()))
        
        total_payments = 0
        users_docs = db.collection("users").stream()
        for doc in users_docs:
            data = doc.to_dict()
            payments = data.get('totalPayments', 0)
            if isinstance(payments, (int, float)):
                total_payments += payments
        
        return {
            'students': students_count,
            'teachers': teachers_count,
            'users': users_count,
            'total_payments': total_payments
        }
    except Exception as e:
        logger.error(f"Statistikalarni olishda xatolik: {e}")
        return None

# === Telegram bot handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot boshlanishi"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or "Foydalanuvchi"
    
    if is_admin(user_id):
        welcome_text = f"👑 *Admin panel*\n\nXush kelibsiz, {user_name}!\nSiz admin huquqlariga egasiz."
    else:
        welcome_text = f"🎓 *O'quvchilar boshqaruv tizimi*\n\nXush kelibsiz, {user_name}!\nSizda cheklangan huquqlar mavjud."
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard(user_id),
        parse_mode='Markdown'
    )

async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Matn xabarlarni qayta ishlash"""
    text = update.message.text
    user_id = update.effective_user.id
    
    # Admin bo'lmagan foydalanuvchilar uchun cheklash
    if not is_admin(user_id):
        if text in ["👨‍🏫 O'qituvchilar", "📊 Statistika", "📈 O'qituvchilar statistikasi", "🔄 Yangilash"]:
            await update.message.reply_text(
                "❌ *Ruxsat rad etildi!*\n\nSizda bu bo'limga kirish huquqi yo'q.\nFaqat adminlar bu funksiyalardan foydalana oladi.",
                reply_markup=get_main_keyboard(user_id),
                parse_mode='Markdown'
            )
            return
    
    # Admin va oddiy foydalanuvchilar uchun umumiy buyruqlar
    if text == "ℹ️ Yordam":
        await show_help(update.message, user_id)
    elif text == "🏠 Asosiy menu":
        await update.message.reply_text(
            "🏠 Asosiy menu",
            reply_markup=get_main_keyboard(user_id)
        )
    # Faqat adminlar uchun buyruqlar
    elif is_admin(user_id):
        if text == "👨‍🏫 O'qituvchilar":
            await show_teachers_list(update.message)
        elif text == "📊 Statistika":
            await show_statistics(update.message)
        elif text == "📈 O'qituvchilar statistikasi":
            await show_teachers_statistics(update.message)
        elif text == "🔄 Yangilash":
            await update.message.reply_text(
                "🔄 Ma'lumotlar yangilandi!",
                reply_markup=get_main_keyboard(user_id)
            )
        elif text == "👑 Admin Panel":
            await show_admin_panel(update.message)
        elif text == "👑 Admin ro'yxati":
            await show_admin_list(update.message)
        elif text == "📊 Tizim holati":
            await show_system_status(update.message)
        elif text.startswith("➕"):
            context.user_data['waiting_for'] = 'add_admin'
            await update.message.reply_text(
                "👑 *Admin qo'shish*\n\nYangi admin user ID sini yuboring:",
                parse_mode='Markdown'
            )
        elif text.startswith("➖"):
            context.user_data['waiting_for'] = 'remove_admin'
            await update.message.reply_text(
                "👑 *Admin o'chirish*\n\nO'chirmoqchi bo'lgan admin user ID sini yuboring:",
                parse_mode='Markdown'
            )
        else:
            # Admin panels uchun maxsus buyruqlarni tekshirish
            if context.user_data.get('waiting_for') == 'add_admin':
                await handle_add_admin(update, context)
            elif context.user_data.get('waiting_for') == 'remove_admin':
                await handle_remove_admin(update, context)
            else:
                await update.message.reply_text(
                    "❌ Noto'g'ri buyruq. Quyidagi tugmalardan foydalaning:",
                    reply_markup=get_main_keyboard(user_id)
                )
    else:
        await update.message.reply_text(
            "❌ Noto'g'ri buyruq. Quyidagi tugmalardan foydalaning:",
            reply_markup=get_main_keyboard(user_id)
        )

# === Admin panel funksiyalari ===
async def show_admin_panel(message):
    """Admin panelini ko'rsatish"""
    admin_text = f"""👑 *Admin Panel*

🔹 *Admin qo'shish* - Yangi admin qo'shish
🔹 *Admin o'chirish* - Adminni olib tashlash  
🔹 *Admin ro'yxati* - Barcha adminlarni ko'rish
🔹 *Tizim holati* - Bot va tizim holati
🔹 *Asosiy menu* - Bosh menyuga qaytish

*Hozirgi adminlar soni:* {len(ADMIN_IDS)} ta
*Sizning ID:* {message.from_user.id}"""
    
    await message.reply_text(
        admin_text,
        reply_markup=get_admin_keyboard(),
        parse_mode='Markdown'
    )

async def show_admin_list(message):
    """Admin ro'yxatini ko'rsatish"""
    if not ADMIN_IDS:
        admin_text = "❌ Hech qanday admin topilmadi!"
    else:
        admin_text = f"👑 *Admin ro'yxati* ({len(ADMIN_IDS)} ta):\n\n"
        for i, admin_id in enumerate(ADMIN_IDS, 1):
            admin_text += f"{i}. `{admin_id}`\n"
    
    await message.reply_text(
        admin_text,
        reply_markup=get_admin_keyboard(),
        parse_mode='Markdown'
    )

async def show_system_status(message):
    """Tizim holatini ko'rsatish"""
    try:
        # Firebase connection tekshirish
        try:
            list(db.collection("students").limit(1).stream())
            firebase_status = "✅ Ulangan"
        except:
            firebase_status = "❌ Ulanmagan"
        
        # Statistics
        stats = get_statistics()
        
        status_text = f"""🔧 *Tizim holati*

🤖 *Bot:* ✅ Ishlamoqda
🔥 *Firebase:* {firebase_status}
📊 *Ma'lumotlar bazasi:* {'✅ Mavjud' if stats else '❌ Xatolik'}
👑 *Adminlar:* {len(ADMIN_IDS)} ta

📈 *Joriy statistika:*
• O'quvchilar: {stats['students'] if stats else 'N/A'} ta
• O'qituvchilar: {stats['teachers'] if stats else 'N/A'} ta
• Foydalanuvchilar: {stats['users'] if stats else 'N/A'} ta

🕐 *Tekshirilgan vaqt:* {datetime.now().strftime('%d.%m.%Y %H:%M')}"""
        
        await message.reply_text(
            status_text,
            reply_markup=get_admin_keyboard(),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Status ko'rsatishda xatolik: {e}")
        await message.reply_text(f"❌ Status olishda xatolik: {str(e)}")

async def handle_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin qo'shish"""
    try:
        user_id = int(update.message.text.strip())
        
        if add_admin(user_id):
            await update.message.reply_text(
                f"✅ *Yangi admin qo'shildi!*\n\n👑 User ID: `{user_id}`\nJami adminlar: {len(ADMIN_IDS)} ta",
                reply_markup=get_admin_keyboard(),
                parse_mode='Markdown'
            )
            
            # Yangi adminga xabar yuborish (ixtiyoriy)
            try:
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                requests.post(url, json={
                    "chat_id": user_id,
                    "text": "🎉 *Tabriklaymiz!*\n\nSiz admin qilib tayinlandingiz!\n/start buyrug'ini bosing va admin panelidan foydalaning.",
                    "parse_mode": "Markdown"
                })
            except:
                pass
            
        else:
            await update.message.reply_text(
                f"❌ Bu foydalanuvchi allaqachon admin: `{user_id}`",
                reply_markup=get_admin_keyboard(),
                parse_mode='Markdown'
            )
    except ValueError:
        await update.message.reply_text(
            "❌ Noto'g'ri format! Faqat raqam kiriting.",
            reply_markup=get_admin_keyboard()
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Xatolik: {str(e)}",
            reply_markup=get_admin_keyboard()
        )
    
    # Kutish holatini tozalash
    context.user_data.pop('waiting_for', None)

async def handle_remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin o'chirish"""
    try:
        user_id = int(update.message.text.strip())
        current_user_id = update.effective_user.id
        
        # O'zini o'chirishga ruxsat bermaslik
        if user_id == current_user_id:
            await update.message.reply_text(
                "❌ Siz o'zingizni admin ro'yxatidan o'chira olmaysiz!",
                reply_markup=get_admin_keyboard()
            )
            context.user_data.pop('waiting_for', None)
            return
        
        if remove_admin(user_id):
            await update.message.reply_text(
                f"✅ *Admin o'chirildi!*\n\n👑 User ID: `{user_id}`\nQolgan adminlar: {len(ADMIN_IDS)} ta",
                reply_markup=get_admin_keyboard(),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"❌ Bu foydalanuvchi admin emas: `{user_id}`",
                reply_markup=get_admin_keyboard(),
                parse_mode='Markdown'
            )
    except ValueError:
        await update.message.reply_text(
            "❌ Noto'g'ri format! Faqat raqam kiriting.",
            reply_markup=get_admin_keyboard()
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Xatolik: {str(e)}",
            reply_markup=get_admin_keyboard()
        )
    
    # Kutish holatini tozalash
    context.user_data.pop('waiting_for', None)

async def show_help(message, user_id=None):
    """Yordam bo'limi"""
    if is_admin(user_id):
        help_text = """ℹ️ *Admin Yordam Bo'limi*

🔹 *O'qituvchilar* - Barcha o'qituvchilar va ularning o'quvchilari ro'yxati
🔹 *Statistika* - Umumiy statistikalar va ma'lumotlar
🔹 *O'qituvchilar statistikasi* - Har bir o'qituvchi bo'yicha batafsil statistika
🔹 *Admin Panel* - Admin boshqaruv paneli
🔹 *Yangilash* - Ma'lumotlarni yangilash

*Admin imkoniyatlari:*
• O'quvchi ma'lumotlarini ko'rish va o'chirish
• Real-time yangilanishlar
• Admin qo'shish/o'chirish
• Tizim holatini kuzatish
• To'liq statistikalar

*Texnik yordam: @Musurmon_dev*"""
    else:
        help_text = """ℹ️ *Yordam Bo'limi*

🔸 Siz oddiy foydalanuvchisiz
🔸 Sizda cheklangan huquqlar mavjud
🔸 Admin bo'lish uchun administratorga murojaat qiling

*Texnik yordam: @Musurmon_dev*

*London Language Center*"""
    
    await message.reply_text(
        help_text,
        reply_markup=get_main_keyboard(user_id),
        parse_mode='Markdown'
    )

async def show_statistics(message):
    """Statistikalarni ko'rsatish"""
    stats = get_statistics()
    
    if not stats:
        await message.reply_text(
            "❌ Statistikalarni olishda xatolik yuz berdi",
            reply_markup=get_main_keyboard(message.from_user.id)
        )
        return
    
    # To'lovlarni formatlash
    formatted_payments = f"{stats['total_payments']:,}".replace(',', ' ')
    
    stats_text = f"""📊 *Tizim statistikasi*

👥 *Foydalanuvchilar:* {stats['users']} ta
👨‍🏫 *O'qituvchilar:* {stats['teachers']} ta
🧑‍🎓 *O'quvchilar:* {stats['students']} ta
💰 *Jami to'lovlar:* {formatted_payments} so'm
👑 *Adminlar:* {len(ADMIN_IDS)} ta

📅 *Oxirgi yangilanish:* {datetime.now().strftime('%d.%m.%Y %H:%M')}"""
    
    await message.reply_text(
        stats_text,
        reply_markup=get_main_keyboard(message.from_user.id),
        parse_mode='Markdown'
    )

async def show_teachers_statistics(message):
    """O'qituvchilar statistikasini ko'rsatish"""
    teachers = get_teachers_from_users()
    
    if not teachers:
        await message.reply_text(
            "❌ O'qituvchilar statistikasi topilmadi",
            reply_markup=get_main_keyboard(message.from_user.id)
        )
        return
    
    # Inline keyboard yaratish
    keyboard = []
    for teacher in teachers:
        keyboard.append([
            InlineKeyboardButton(
                f"👨‍🏫 {teacher['name']} ({teacher['subject']})",
                callback_data=f"teacher_stats_{teacher['id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🏠 Asosiy menu", callback_data="back_to_main")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Umumiy statistika
    total_payments = sum(teacher['totalPayments'] for teacher in teachers)
    total_students = sum(teacher['totalStudents'] for teacher in teachers)
    formatted_total = f"{total_payments:,}".replace(',', ' ')
    
    stats_text = f"""📈 *O'qituvchilar statistikasi*

👥 *Jami o'qituvchilar:* {len(teachers)} ta
🧑‍🎓 *Jami o'quvchilar:* {total_students} ta
💰 *Jami to'lovlar:* {formatted_total} so'm

📋 *Har bir o'qituvchi bo'yicha batafsil ma'lumot:*"""
    
    await message.reply_text(
        stats_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_teachers_list(message):
    """O'qituvchilar ro'yxatini ko'rsatish"""
    teachers = get_all_teachers()
    
    if not teachers:
        await message.reply_text(
            "❌ O'qituvchilar topilmadi",
            reply_markup=get_main_keyboard(message.from_user.id)
        )
        return
    
    keyboard = []
    for teacher in teachers:
        keyboard.append([
            InlineKeyboardButton(
                f"👨‍🏫 {teacher['name']}",
                callback_data=f"teacher_{teacher['name']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🏠 Asosiy menu", callback_data="back_to_main")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message.reply_text(
        f"👨‍🏫 *O'qituvchilar ro'yxati:*\n\n"
        f"📊 Jami: {len(teachers)} ta o'qituvchi\n\n"
        "O'qituvchini tanlab, uning o'quvchilarini ko'ring:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline button handler"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Admin tekshiruvi
    if not is_admin(user_id):
        await query.answer("❌ Sizda bu amalni bajarish huquqi yo'q!", show_alert=True)
        return
    
    await query.answer()
    
    data = query.data
    
    if data == "back_to_main":
        await query.edit_message_text(
            "🏠 Asosiy menu",
            reply_markup=InlineKeyboardMarkup([[]])
        )
    elif data.startswith("teacher_stats_"):
        teacher_id = data.replace("teacher_stats_", "")
        await show_teacher_detailed_stats(query, teacher_id)
    elif data.startswith("teacher_"):
        teacher_name = data.replace("teacher_", "")
        await show_students_by_teacher(query, teacher_name)
    elif data.startswith("student_"):
        student_id = data.replace("student_", "")
        await show_student_details(query, student_id)
    elif data.startswith("delete_"):
        student_id = data.replace("delete_", "")
        await delete_student_handler(query, student_id)
    elif data.startswith("back_to_students_"):
        teacher_name = data.replace("back_to_students_", "")
        await show_students_by_teacher(query, teacher_name)

async def show_teacher_detailed_stats(query, teacher_id):
    """O'qituvchi bo'yicha batafsil statistika"""
    teacher = get_user_by_id(teacher_id)
    
    if not teacher or teacher['role'] != 'teacher':
        await query.edit_message_text("❌ O'qituvchi topilmadi")
        return
    
    # To'lovlarni formatlash
    formatted_payments = f"{teacher['totalPayments']:,}".replace(',', ' ')
    
    # Faollik darajasini alohida o'zgaruvchiga ajratish
    if teacher['totalStudents'] > 5:
        activity_level = 'Yuqori'
    elif teacher['totalStudents'] > 0:
        activity_level = "O'rta"
    else:
        activity_level = 'Past'
    
    stats_text = f"""👨‍🏫 *{teacher['name']} - Batafsil statistika*

📚 *Fan:* {teacher['subject']}
🧑‍🎓 *O'quvchilar soni:* {teacher['totalStudents']} ta
💰 *Jami to'lovlar:* {formatted_payments} so'm
🔐 *Parol:* {teacher['password']}

📊 *Qo'shimcha ma'lumotlar:*
• Har bir o'quvchidan o'rtacha: {formatted_payments.split()[0] if teacher['totalStudents'] > 0 else '0'} so'm
• Faollik darajasi: {activity_level}"""
    
    keyboard = [
        [InlineKeyboardButton("📈 Statistikalar", callback_data="back_to_main")],
        [InlineKeyboardButton("🏠 Asosiy menu", callback_data="back_to_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        stats_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_students_by_teacher(query, teacher_name):
    """O'qituvchi bo'yicha o'quvchilarni ko'rsatish"""
    students = get_students_by_teacher(teacher_name)
    
    if not students:
        keyboard = [
            [InlineKeyboardButton("🏠 Asosiy menu", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"❌ *{teacher_name}* o'qituvchisida o'quvchilar topilmadi",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    keyboard = []
    for student in students:
        keyboard.append([
            InlineKeyboardButton(
                f"🧑‍🎓 {student['surname']} {student['name']}",
                callback_data=f"student_{student['id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🏠 Asosiy menu", callback_data="back_to_main")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"👨‍🏫 *{teacher_name}* o'qituvchisining o'quvchilari:\n\n"
        f"📊 Jami: {len(students)} ta o'quvchi\n\n"
        "O'quvchini tanlab, to'liq ma'lumotini ko'ring:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_student_details(query, student_id):
    """O'quvchi to'liq ma'lumotlarini ko'rsatish"""
    student = get_student_by_id(student_id)
    
    if not student:
        await query.edit_message_text("❌ O'quvchi topilmadi")
        return
    
    # Sana formatini yaxshilash
    date_str = student['date']
    if date_str != '—':
        try:
            if isinstance(date_str, datetime):
                date_str = date_str.strftime('%d.%m.%Y %H:%M')
            else:
                date_str = str(date_str)
        except:
            date_str = str(date_str)
    
    text = f"""👤 *O'quvchi ma'lumotlari:*

🆔 *ID:* {student['id']}
👤 *Familiya:* {student['surname']}
🧑‍🎓 *Ismi:* {student['name']}
📞 *Telefon:* {student['phone']}
📅 *Sana:* {date_str}
👨‍🏫 *O'qituvchi:* {student['teacher']}"""
    
    keyboard = [
        [InlineKeyboardButton("🗑️ O'chirish", callback_data=f"delete_{student_id}")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data=f"back_to_students_{student['teacher']}")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def delete_student_handler(query, student_id):
    """O'quvchini o'chirish handler"""
    student = get_student_by_id(student_id)
    
    if not student:
        await query.edit_message_text("❌ O'quvchi topilmadi")
        return
    
    # O'chirish jarayoni
    if delete_student(student_id):
        keyboard = [
            [InlineKeyboardButton("🏠 Asosiy menu", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ *O'quvchi muvaffaqiyatli o'chirildi!*\n\n"
            f"👤 {student['surname']} {student['name']}\n"
            f"👨‍🏫 O'qituvchi: {student['teacher']}\n\n"
            f"📢 *Barcha adminlarga notifikatsiya yuborildi*",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # Qo'shimcha notifikatsiya
        try:
            text = f"""🤖 *Bot orqali o'quvchi o'chirildi!*

👤 *O'chirilgan o'quvchi:* {student['surname']} {student['name']}
👨‍🏫 *O'qituvchi:* {student['teacher']}
🕐 *O'chirilgan vaqt:* {datetime.now().strftime('%d.%m.%Y %H:%M')}
👤 *Kim o'chirdi:* Admin ({query.from_user.first_name or 'N/A'})"""
            
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, json={
                "chat_id": CHAT_ID,
                "text": text,
                "parse_mode": "Markdown"
            })
        except Exception as e:
            logger.error(f"Qo'shimcha notifikatsiya yuborishda xatolik: {e}")
    else:
        await query.edit_message_text("❌ O'quvchini o'chirishda xatolik")

# === Notifikatsiya funksiyalari ===
def send_new_student_notification(student_data):
    """Yangi o'quvchi qo'shilganda notifikatsiya yuborish"""
    try:
        surname = student_data.get('surname', student_data.get('surename', '—'))
        name = student_data.get('name', '—')
        phone = student_data.get('phone', '—')
        date = student_data.get('date', '—')
        
        if date != '—':
            try:
                if isinstance(date, datetime):
                    date = date.strftime('%d.%m.%Y %H:%M')
                else:
                    date = str(date)
            except:
                date = str(date)
        
        teacher_info = student_data.get('teacher', {})
        teacher_name = '—'
        if isinstance(teacher_info, dict):
            teacher_name = teacher_info.get('name', '—')
        elif isinstance(teacher_info, str):
            teacher_name = teacher_info
        
        text = f"""🔔 *Yangi o'quvchi qo'shildi!*

👤 *Familiya:* {surname}
🧑‍🎓 *Ismi:* {name}
📞 *Telefon:* {phone}
📅 *Sana:* {date}
👨‍🏫 *O'qituvchi:* {teacher_name}"""
        
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        response = requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        })
        
        if response.status_code == 200:
            logger.info("Yangi o'quvchi notifikatsiyasi yuborildi")
            return True
        else:
            logger.error(f"Notifikatsiya yuborishda xatolik: {response.text}")
            return False
        
    except Exception as e:
        logger.error(f"Notifikatsiya yuborishda xatolik: {e}")
        return False

def send_system_notification(message, notification_type="INFO"):
    """Tizim notifikatsiyalari yuborish"""
    try:
        emoji_map = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "ERROR": "❌",
            "WARNING": "⚠️"
        }
        
        emoji = emoji_map.get(notification_type, "ℹ️")
        
        text = f"""{emoji} *Tizim xabari*

{message}

🕐 *Vaqt:* {datetime.now().strftime('%d.%m.%Y %H:%M')}"""
        
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        response = requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        })
        
        if response.status_code == 200:
            logger.info(f"Tizim notifikatsiyasi yuborildi: {notification_type}")
            return True
        else:
            logger.error(f"Tizim notifikatsiyasini yuborishda xatolik: {response.text}")
            return False
        
    except Exception as e:
        logger.error(f"Tizim notifikatsiyasini yuborishda xatolik: {e}")
        return False

# === Real-time listener ===
def setup_realtime_listener():
    """Real-time listener ishga tushirish"""
    def on_snapshot(col_snapshot, changes, read_time):
        """Firestore o'zgarishlarni qayta ishlash"""
        try:
            for change in changes:
                if change.type.name == 'ADDED':
                    doc_data = change.document.to_dict()
                    if not doc_data.get('notified', False):
                        logger.info(f"Yangi o'quvchi topildi: {change.document.id}")
                        if send_new_student_notification(doc_data):
                            try:
                                change.document.reference.update({
                                    "notified": True,
                                    "notification_sent_at": firestore.SERVER_TIMESTAMP
                                })
                                logger.info(f"O'quvchi {change.document.id} notified qilindi")
                            except Exception as e:
                                logger.error(f"Notified flagini o'rnatishda xatolik: {e}")
        except Exception as e:
            logger.error(f"Snapshot qayta ishlashda xatolik: {e}")
    
    try:
        query = db.collection("students")
        query.on_snapshot(on_snapshot)
        logger.info("Real-time listener ishga tushirildi")
        
        send_system_notification(
            "🚀 Bot muvaffaqiyatli ishga tushdi!\n"
            "• Real-time monitoring faol\n"
            "• Barcha notifikatsiyalar yoqildi\n"
            f"• Adminlar soni: {len(ADMIN_IDS)} ta",
            "SUCCESS"
        )
        
    except Exception as e:
        logger.error(f"Real-time listener ishga tushirishda xatolik: {e}")
        send_system_notification(
            f"❌ Real-time listener ishga tushmadi: {str(e)}",
            "ERROR"
        )

# === Backup funksiyalari ===
async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Backup yaratish buyrugi"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text(
            "❌ *Ruxsat rad etildi!*\n\nSizda bu buyruqni ishlatish huquqi yo'q.",
            parse_mode='Markdown'
        )
        return
    
    try:
        # Barcha ma'lumotlarni olish
        students = []
        teachers = get_all_teachers()
        users = get_all_users()
        
        # O'quvchilar ma'lumotlarini olish
        docs = db.collection("students").stream()
        for doc in docs:
            data = doc.to_dict()
            students.append({
                'id': doc.id,
                **data
            })
        
        backup_data = {
            'timestamp': datetime.now().isoformat(),
            'students': students,
            'teachers': teachers,
            'users': users,
            'statistics': get_statistics(),
            'admin_count': len(ADMIN_IDS)
        }
        
        # JSON faylga saqlash
        backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(backup_filename, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        
        await update.message.reply_text(
            f"✅ *Backup yaratildi!*\n\n"
            f"📁 *Fayl nomi:* {backup_filename}\n"
            f"📊 *O'quvchilar:* {len(students)} ta\n"
            f"👨‍🏫 *O'qituvchilar:* {len(teachers)} ta\n"
            f"👥 *Foydalanuvchilar:* {len(users)} ta\n"
            f"👑 *Adminlar:* {len(ADMIN_IDS)} ta",
            parse_mode='Markdown'
        )
        
        # Tizim notifikatsiyasi
        send_system_notification(
            f"Backup yaratildi: {backup_filename}\nJami ma'lumotlar: {len(students) + len(teachers) + len(users)} ta\nAdmin tomonidan: {update.effective_user.first_name or 'N/A'}",
            "SUCCESS"
        )
        
    except Exception as e:
        logger.error(f"Backup yaratishda xatolik: {e}")
        await update.message.reply_text(f"❌ Backup yaratishda xatolik: {str(e)}")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tizim holati ko'rsatish"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text(
            "❌ *Ruxsat rad etildi!*\n\nSizda bu buyruqni ishlatish huquqi yo'q.",
            parse_mode='Markdown'
        )
        return
    
    try:
        # Firebase connection tekshirish
        try:
            list(db.collection("students").limit(1).stream())
            firebase_status = "✅ Ulangan"
        except:
            firebase_status = "❌ Ulanmagan"
        
        # Bot status
        bot_status = "✅ Ishlamoqda"
        
        # Statistics
        stats = get_statistics()
        
        status_text = f"""🔧 *Tizim holati*

🤖 *Bot:* {bot_status}
🔥 *Firebase:* {firebase_status}
📊 *Ma'lumotlar bazasi:* {'✅ Mavjud' if stats else '❌ Xatolik'}
👑 *Adminlar:* {len(ADMIN_IDS)} ta

📈 *Joriy statistika:*
• O'quvchilar: {stats['students'] if stats else 'N/A'} ta
• O'qituvchilar: {stats['teachers'] if stats else 'N/A'} ta
• Foydalanuvchilar: {stats['users'] if stats else 'N/A'} ta

🕐 *Tekshirilgan vaqt:* {datetime.now().strftime('%d.%m.%Y %H:%M')}"""
        
        await update.message.reply_text(
            status_text,
            reply_markup=get_admin_keyboard(),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Status ko'rsatishda xatolik: {e}")
        await update.message.reply_text(f"❌ Status olishda xatolik: {str(e)}")

# === Bot ishga tushirish ===
def main():
    """Botni ishga tushirish"""
    global db
    
    try:
        # Firebase'ni ishga tushirish
        if db is None:
            db = initialize_firebase()
        
        # Firebase connection tekshirish
        try:
            list(db.collection("students").limit(1).stream())
            logger.info("Firebase connection: OK")
            
            # Real-time listener ishga tushirish
            setup_realtime_listener()
            
        except Exception as e:
            logger.error(f"Firebase connection xatolik: {e}")
        
        # Bot yaratish
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Handlerlarni qo'shish
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("backup", backup_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
        application.add_handler(CallbackQueryHandler(button_handler))
        
        logger.info("Bot ishga tushmoqda...")
        
        # Polling boshlanishi
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"Botni ishga tushirishda xatolik: {e}")
        send_system_notification(
            f"Bot ishga tushmadi: {str(e)}",
            "ERROR"
        )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot to'xtatildi (Ctrl+C)")
        send_system_notification(
            "Bot qo'lda to'xtatildi",
            "WARNING"
        )
    except Exception as e:
        logger.error(f"Bot ishga tushirishda fatal xatolik: {e}")
        send_system_notification(
            f"Bot fatal xatolik bilan tugadi: {str(e)}",
            "ERROR"
        )
