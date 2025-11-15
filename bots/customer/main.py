"""
Customer Bot - Mijozlar va to'lovlar bilan ishlash
Adminlar: Boshqaruv paneli, statistika, ogohlantirishlar yuborish
Mijozlar: Account, to'lov qilish, support
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Project root path qo'shish
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command

from core.config import CUSTOMER_BOT_TOKEN, ADMIN_IDS, TEST_GROUP_LINK, TEST_GROUP_ID

# Ma'lumotlar fayllari
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

PAYMENT_REQUESTS_FILE = DATA_DIR / "payment_requests.json"
APPROVED_USERS_FILE = DATA_DIR / "approved_users.json"
SUBSCRIPTIONS_FILE = DATA_DIR / "subscriptions.json"

router = Router()


# ============================================================
# FSM STATES
# ============================================================
class AdminStates(StatesGroup):
    """Admin panel states"""
    sending_broadcast = State()  # Ommaviy xabar yuborish
    setting_price = State()  # Narx belgilash


class PaymentStates(StatesGroup):
    """To'lov states"""
    waiting_screenshot = State()  # Screenshot kutish
    choosing_period = State()  # Davr tanlash


# ============================================================
# DATA FUNCTIONS
# ============================================================
def load_json(file_path, default=None):
    """JSON faylni yuklash"""
    if default is None:
        default = []

    if not file_path.exists():
        save_json(file_path, default)
        return default

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return default


def save_json(file_path, data):
    """JSON faylga saqlash"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_payment_requests():
    """To'lov so'rovlarini olish"""
    return load_json(PAYMENT_REQUESTS_FILE, [])


def save_payment_request(user_id, username, screenshot_file_id, period="1_month"):
    """To'lov so'rovini saqlash"""
    requests = get_payment_requests()

    request = {
        "user_id": user_id,
        "username": username,
        "screenshot_file_id": screenshot_file_id,
        "period": period,
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }

    requests.append(request)
    save_json(PAYMENT_REQUESTS_FILE, requests)
    return request


def get_approved_users():
    """Tasdiqlangan userlarni olish"""
    return load_json(APPROVED_USERS_FILE, [])


def add_approved_user(user_id, username, period="1_month"):
    """Tasdiqlangan userga qo'shish"""
    users = get_approved_users()

    # Muddatni hisoblash
    if period == "1_month":
        expiry_date = datetime.now() + timedelta(days=30)
    elif period == "3_months":
        expiry_date = datetime.now() + timedelta(days=90)
    elif period == "1_year":
        expiry_date = datetime.now() + timedelta(days=365)
    else:
        expiry_date = datetime.now() + timedelta(days=30)

    user_data = {
        "user_id": user_id,
        "username": username,
        "period": period,
        "joined_at": datetime.now().isoformat(),
        "expiry_date": expiry_date.isoformat(),
        "status": "active"
    }

    users.append(user_data)
    save_json(APPROVED_USERS_FILE, users)
    return user_data


def get_subscriptions():
    """Obunalarni olish"""
    return load_json(SUBSCRIPTIONS_FILE, {
        "1_month": {"price": "50000", "name": "1 oylik"},
        "3_months": {"price": "135000", "name": "3 oylik"},
        "1_year": {"price": "480000", "name": "1 yillik"}
    })


def update_subscription_price(period, price):
    """Obuna narxini yangilash"""
    subs = get_subscriptions()
    if period in subs:
        subs[period]["price"] = price
        save_json(SUBSCRIPTIONS_FILE, subs)


# ============================================================
# KEYBOARDS
# ============================================================
def get_main_keyboard(is_admin=False):
    """Asosiy keyboard"""
    buttons = []

    if is_admin:
        # Admin uchun keyboard
        buttons = [
            [KeyboardButton(text="📊 Statistika")],
            [KeyboardButton(text="💰 Narxlar"), KeyboardButton(text="📢 Xabar yuborish")],
            [KeyboardButton(text="✅ So'rovlar"), KeyboardButton(text="👥 Foydalanuvchilar")],
            [KeyboardButton(text="ℹ️ Yo'riqnoma")]
        ]
    else:
        # Oddiy user uchun keyboard
        buttons = [
            [KeyboardButton(text="💳 To'lov qilish")],
            [KeyboardButton(text="📝 Mening accountim")],
            [KeyboardButton(text="💬 Yordam"), KeyboardButton(text="ℹ️ Yo'riqnoma")]
        ]

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def get_period_keyboard():
    """Davr tanlash keyboard"""
    subs = get_subscriptions()

    buttons = []
    for period, data in subs.items():
        text = f"{data['name']} - {data['price']} so'm"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"period_{period}")])

    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_request_keyboard(request_id):
    """Admin uchun so'rovni tasdiqlash/rad etish keyboard"""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{request_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{request_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================================
# HANDLERS - START & MAIN MENU
# ============================================================
@router.message(Command("start"))
async def cmd_start(message: Message):
    """Start command handler"""
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"

    is_admin = user_id in ADMIN_IDS

    if is_admin:
        text = (
            f"🔐 <b>Admin Panel</b>\n\n"
            f"Assalomu alaykum, Admin!\n\n"
            f"🎛 <b>Mavjud funksiyalar:</b>\n"
            f"• Statistika ko'rish\n"
            f"• Narxlarni boshqarish\n"
            f"• To'lov so'rovlarini ko'rish\n"
            f"• Foydalanuvchilarga xabar yuborish\n"
            f"• Foydalanuvchilar ro'yxati\n\n"
            f"Kerakli bo'limni tanlang 👇"
        )
    else:
        text = (
            f"👋 <b>Xush kelibsiz!</b>\n\n"
            f"Bu bot orqali siz premium guruhga obuna bo'lishingiz mumkin.\n\n"
            f"📌 <b>Imkoniyatlar:</b>\n"
            f"• To'lov qilish va screenshot yuklash\n"
            f"• Account holatingizni ko'rish\n"
            f"• Yordam va yo'riqnoma\n\n"
            f"Kerakli bo'limni tanlang 👇"
        )

    await message.answer(text, parse_mode='html', reply_markup=get_main_keyboard(is_admin))


# ============================================================
# ADMIN HANDLERS
# ============================================================
@router.message(F.text == "📊 Statistika")
async def show_stats(message: Message):
    """Statistika ko'rsatish"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔️ Bu bo'lim faqat adminlar uchun!")
        return

    approved_users = get_approved_users()
    payment_requests = get_payment_requests()

    # Active userlarni sanash
    active_users = [u for u in approved_users if u.get("status") == "active"]

    # Pending requestlarni sanash
    pending_requests = [r for r in payment_requests if r.get("status") == "pending"]

    text = (
        f"📊 <b>STATISTIKA</b>\n\n"
        f"👥 <b>Foydalanuvchilar:</b>\n"
        f"• Jami: {len(approved_users)} ta\n"
        f"• Aktiv: {len(active_users)} ta\n\n"
        f"💳 <b>To'lov so'rovlari:</b>\n"
        f"• Kutilmoqda: {len(pending_requests)} ta\n"
        f"• Jami: {len(payment_requests)} ta\n"
    )

    await message.answer(text, parse_mode='html')


@router.message(F.text == "💰 Narxlar")
async def show_prices(message: Message):
    """Narxlarni ko'rsatish va o'zgartirish"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔️ Bu bo'lim faqat adminlar uchun!")
        return

    subs = get_subscriptions()

    text = "💰 <b>JORIY NARXLAR</b>\n\n"
    for period, data in subs.items():
        text += f"• {data['name']}: <b>{data['price']}</b> so'm\n"

    text += "\nNarxni o'zgartirish uchun:\n"
    text += "<code>/setprice 1_month 60000</code>"

    await message.answer(text, parse_mode='html')


@router.message(F.text == "✅ So'rovlar")
async def show_requests(message: Message):
    """To'lov so'rovlarini ko'rsatish"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔️ Bu bo'lim faqat adminlar uchun!")
        return

    requests = get_payment_requests()
    pending_requests = [r for r in requests if r.get("status") == "pending"]

    if not pending_requests:
        await message.answer("📭 Hozircha yangi so'rovlar yo'q.")
        return

    await message.answer(f"✅ <b>{len(pending_requests)} ta yangi so'rov</b>\n\nScreenshotlar quyida 👇", parse_mode='html')

    bot = message.bot
    for i, req in enumerate(pending_requests, 1):
        user_id = req.get("user_id")
        username = req.get("username", "Noma'lum")
        period = req.get("period", "1_month")
        screenshot = req.get("screenshot_file_id")
        created_at = req.get("created_at", "")

        subs = get_subscriptions()
        period_name = subs.get(period, {}).get("name", period)

        caption = (
            f"<b>So'rov #{i}</b>\n\n"
            f"👤 User: @{username}\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"📅 Davr: {period_name}\n"
            f"⏰ Vaqt: {created_at[:16]}\n"
        )

        await bot.send_photo(
            chat_id=message.chat.id,
            photo=screenshot,
            caption=caption,
            parse_mode='html',
            reply_markup=get_admin_request_keyboard(i-1)
        )


@router.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: CallbackQuery):
    """To'lovni tasdiqlash"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return

    request_id = int(callback.data.split("_")[1])

    requests = get_payment_requests()
    if request_id >= len(requests):
        await callback.answer("❌ So'rov topilmadi!", show_alert=True)
        return

    req = requests[request_id]

    if req.get("status") != "pending":
        await callback.answer("⚠️ Bu so'rov allaqachon ko'rib chiqilgan!", show_alert=True)
        return

    # So'rovni tasdiqlash
    req["status"] = "approved"
    req["approved_by"] = callback.from_user.id
    req["approved_at"] = datetime.now().isoformat()
    save_json(PAYMENT_REQUESTS_FILE, requests)

    # Foydalanuvchini approved listga qo'shish
    user_data = add_approved_user(req["user_id"], req["username"], req["period"])

    # Individual link yaratish
    bot = callback.bot
    invite_link = None
    try:
        # Bir martalik link yaratish (faqat 1 kishi qo'shilishi mumkin)
        link = await bot.create_chat_invite_link(
            chat_id=TEST_GROUP_ID,
            member_limit=1,  # MUHIM: Faqat 1 kishi ishlatishi mumkin
            name=f"Premium - {req['username']}"
        )
        invite_link = link.invite_link
    except Exception as e:
        print(f"[XATO] Link yaratish: {e}")
        invite_link = TEST_GROUP_LINK  # Fallback

    # Userga xabar yuborish
    try:
        subs = get_subscriptions()
        period_name = subs.get(req["period"], {}).get("name", req["period"])

        user_text = (
            f"✅ <b>To'lovingiz tasdiqlandi!</b>\n\n"
            f"📅 Davr: {period_name}\n"
            f"⏰ Amal qilish muddati: {user_data['expiry_date'][:10]}\n\n"
            f"🔗 <b>Guruhga qo'shilish linki:</b>\n"
            f"{invite_link}\n\n"
            f"⚠️ <b>DIQQAT:</b> Link faqat bir marta ishlaydi!\n\n"
            f"Xizmatimizdan foydalanganingiz uchun rahmat! 🙏"
        )

        await bot.send_message(req["user_id"], user_text, parse_mode='html')
    except Exception as e:
        print(f"[XATO] Userga xabar: {e}")

    # Admindan xabar yangilash
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n✅ <b>TASDIQLANDI</b>",
        parse_mode='html'
    )

    await callback.answer("✅ To'lov tasdiqlandi va user xabardor qilindi!", show_alert=True)


@router.callback_query(F.data.startswith("reject_"))
async def reject_payment(callback: CallbackQuery):
    """To'lovni rad etish"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return

    request_id = int(callback.data.split("_")[1])

    requests = get_payment_requests()
    if request_id >= len(requests):
        await callback.answer("❌ So'rov topilmadi!", show_alert=True)
        return

    req = requests[request_id]

    if req.get("status") != "pending":
        await callback.answer("⚠️ Bu so'rov allaqachon ko'rib chiqilgan!", show_alert=True)
        return

    # So'rovni rad etish
    req["status"] = "rejected"
    req["rejected_by"] = callback.from_user.id
    req["rejected_at"] = datetime.now().isoformat()
    save_json(PAYMENT_REQUESTS_FILE, requests)

    # Userga xabar yuborish
    bot = callback.bot
    try:
        user_text = (
            f"❌ <b>To'lovingiz rad etildi</b>\n\n"
            f"Iltimos, to'lovni qayta tekshiring va yangi screenshot yuboring.\n\n"
            f"Yordam kerak bo'lsa: /help"
        )

        await bot.send_message(req["user_id"], user_text, parse_mode='html')
    except:
        pass

    # Admin xabarini yangilash
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n❌ <b>RAD ETILDI</b>",
        parse_mode='html'
    )

    await callback.answer("❌ To'lov rad etildi va user xabardor qilindi!", show_alert=True)


@router.message(F.text == "👥 Foydalanuvchilar")
async def show_users(message: Message):
    """Foydalanuvchilar ro'yxati"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔️ Bu bo'lim faqat adminlar uchun!")
        return

    users = get_approved_users()

    if not users:
        await message.answer("📭 Hozircha foydalanuvchilar yo'q.")
        return

    text = f"👥 <b>FOYDALANUVCHILAR ({len(users)} ta)</b>\n\n"

    for i, user in enumerate(users, 1):
        username = user.get("username", "Noma'lum")
        status = user.get("status", "active")
        expiry = user.get("expiry_date", "")[:10]

        status_emoji = "✅" if status == "active" else "❌"

        text += f"{i}. {status_emoji} @{username} (Tugaydi: {expiry})\n"

    await message.answer(text, parse_mode='html')


@router.message(F.text == "📢 Xabar yuborish")
async def start_broadcast(message: Message, state: FSMContext):
    """Ommaviy xabar yuborish"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔️ Bu bo'lim faqat adminlar uchun!")
        return

    await state.set_state(AdminStates.sending_broadcast)
    await message.answer(
        "📢 <b>Ommaviy xabar yuborish</b>\n\n"
        "Barcha foydalanuvchilarga yuborish uchun xabar yozing:\n\n"
        "Bekor qilish: /cancel",
        parse_mode='html'
    )


@router.message(AdminStates.sending_broadcast)
async def send_broadcast(message: Message, state: FSMContext):
    """Xabarni yuborish"""
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=get_main_keyboard(is_admin=True))
        return

    users = get_approved_users()

    if not users:
        await message.answer("📭 Foydalanuvchilar yo'q.")
        await state.clear()
        return

    await message.answer(f"📤 Xabar {len(users)} ta foydalanuvchiga yuborilmoqda...")

    success = 0
    failed = 0

    bot = message.bot
    for user in users:
        try:
            await bot.send_message(user["user_id"], message.text, parse_mode='html')
            success += 1
        except:
            failed += 1

    await message.answer(
        f"✅ Yuborildi!\n\n"
        f"• Muvaffaqiyatli: {success}\n"
        f"• Xato: {failed}",
        reply_markup=get_main_keyboard(is_admin=True)
    )

    await state.clear()


# ============================================================
# USER HANDLERS
# ============================================================
@router.message(F.text == "💳 To'lov qilish")
async def start_payment(message: Message, state: FSMContext):
    """To'lov jarayonini boshlash"""
    subs = get_subscriptions()

    text = (
        "💳 <b>TO'LOV QILISH</b>\n\n"
        "Davr tanlang 👇\n\n"
    )

    for period, data in subs.items():
        text += f"• {data['name']}: <b>{data['price']}</b> so'm\n"

    await message.answer(text, parse_mode='html', reply_markup=get_period_keyboard())


@router.callback_query(F.data.startswith("period_"))
async def choose_period(callback: CallbackQuery, state: FSMContext):
    """Davr tanlash"""
    period = callback.data.split("_", 1)[1]

    await state.update_data(period=period)
    await state.set_state(PaymentStates.waiting_screenshot)

    subs = get_subscriptions()
    period_data = subs.get(period, {})

    text = (
        f"💳 <b>To'lov ma'lumotlari</b>\n\n"
        f"📅 Davr: {period_data.get('name', period)}\n"
        f"💰 Narx: {period_data.get('price', 'N/A')} so'm\n\n"
        f"📱 <b>Click karta:</b> <code>9860 0601 7106 0255</code>\n\n"
        f"To'lovni amalga oshirgandan keyin screenshot yuboring 📸\n\n"
        f"Bekor qilish: /cancel"
    )

    await callback.message.edit_text(text, parse_mode='html')
    await callback.answer()


@router.message(PaymentStates.waiting_screenshot, F.photo)
async def receive_screenshot(message: Message, state: FSMContext):
    """Screenshot qabul qilish"""
    data = await state.get_data()
    period = data.get("period", "1_month")

    # Screenshot file_id
    screenshot_file_id = message.photo[-1].file_id

    # So'rovni saqlash
    username = message.from_user.username or f"user_{message.from_user.id}"
    request = save_payment_request(message.from_user.id, username, screenshot_file_id, period)

    # Adminlarga xabar yuborish
    bot = message.bot
    subs = get_subscriptions()
    period_name = subs.get(period, {}).get("name", period)

    # So'rov ID sini topish
    requests = get_payment_requests()
    request_id = len(requests) - 1  # Oxirgi so'rov

    admin_text = (
        f"🔔 <b>YANGI TO'LOV SO'ROVI</b>\n\n"
        f"👤 User: @{username}\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n"
        f"📅 Davr: {period_name}\n"
    )

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_photo(
                chat_id=admin_id,
                photo=screenshot_file_id,
                caption=admin_text,
                parse_mode='html',
                reply_markup=get_admin_request_keyboard(request_id)
            )
        except:
            pass

    # Userga javob
    await message.answer(
        "✅ <b>Screenshot qabul qilindi!</b>\n\n"
        "To'lovingiz ko'rib chiqilmoqda. Tez orada sizga xabar beramiz.\n\n"
        "Rahmat! 🙏",
        parse_mode='html',
        reply_markup=get_main_keyboard(is_admin=False)
    )

    await state.clear()


@router.message(F.text == "📝 Mening accountim")
async def show_account(message: Message):
    """Account ma'lumotlarini ko'rsatish"""
    user_id = message.from_user.id
    users = get_approved_users()

    user_data = None
    for u in users:
        if u.get("user_id") == user_id:
            user_data = u
            break

    if not user_data:
        await message.answer(
            "❌ Sizning accountingiz topilmadi.\n\n"
            "Iltimos avval to'lov qiling: /start"
        )
        return

    status = user_data.get("status", "active")
    status_emoji = "✅" if status == "active" else "❌"

    expiry_date = user_data.get("expiry_date", "")[:10]
    joined_date = user_data.get("joined_at", "")[:10]
    period = user_data.get("period", "")

    subs = get_subscriptions()
    period_name = subs.get(period, {}).get("name", period)

    text = (
        f"📝 <b>MENING ACCOUNTIM</b>\n\n"
        f"👤 Username: @{message.from_user.username}\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"📅 Qo'shilgan: {joined_date}\n"
        f"⏰ Amal qiladi: {expiry_date}\n"
        f"📊 Davr: {period_name}\n"
        f"🔐 Status: {status_emoji} {status.upper()}\n"
    )

    await message.answer(text, parse_mode='html')


@router.message(F.text == "ℹ️ Yo'riqnoma")
async def show_help(message: Message):
    """Yo'riqnoma"""
    is_admin = message.from_user.id in ADMIN_IDS

    if is_admin:
        text = (
            "ℹ️ <b>ADMIN YO'RIQNOMASI</b>\n\n"
            "📊 <b>Statistika</b> - Umumiy statistika\n"
            "💰 <b>Narxlar</b> - Narxlarni ko'rish va o'zgartirish\n"
            "✅ <b>So'rovlar</b> - To'lov so'rovlarini ko'rish\n"
            "👥 <b>Foydalanuvchilar</b> - Userlar ro'yxati\n"
            "📢 <b>Xabar yuborish</b> - Ommaviy xabar\n\n"
            "Yordam kerak bo'lsa: @support"
        )
    else:
        text = (
            "ℹ️ <b>YO'RIQNOMA</b>\n\n"
            "💳 <b>To'lov qilish</b>\n"
            "1. Davr tanlang\n"
            "2. Ko'rsatilgan kartaga to'lov qiling\n"
            "3. Screenshot yuboring\n"
            "4. Tasdiqlashni kuting\n\n"
            "📝 <b>Account</b> - Obuna ma'lumotlaringiz\n\n"
            "💬 <b>Yordam</b> - Support bilan bog'lanish\n\n"
            "Savol bo'lsa: @support"
        )

    await message.answer(text, parse_mode='html')


@router.message(F.text == "💬 Yordam")
async def contact_support(message: Message):
    """Support bilan bog'lanish"""
    text = (
        "💬 <b>YORDAM</b>\n\n"
        "Savol yoki muammolaringiz bo'lsa:\n\n"
        "📞 Telegram: @support\n"
        "📧 Email: support@example.com\n\n"
        "Biz sizga yordam berishga tayyormiz! 🙏"
    )

    await message.answer(text, parse_mode='html')


# ============================================================
# UTILS
# ============================================================
@router.message(Command("cancel"))
async def cancel_operation(message: Message, state: FSMContext):
    """Operatsiyani bekor qilish"""
    await state.clear()

    is_admin = message.from_user.id in ADMIN_IDS
    await message.answer("❌ Bekor qilindi.", reply_markup=get_main_keyboard(is_admin))


@router.callback_query(F.data == "cancel")
async def cancel_callback(callback: CallbackQuery, state: FSMContext):
    """Inline callback bekor qilish"""
    await state.clear()

    is_admin = callback.from_user.id in ADMIN_IDS
    await callback.message.delete()
    await callback.message.answer("❌ Bekor qilindi.", reply_markup=get_main_keyboard(is_admin))


# ============================================================
# RUN BOT
# ============================================================
async def run_customer_bot():
    """Customer Bot'ni ishga tushirish"""
    bot = Bot(token=CUSTOMER_BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    print("[START] Customer Bot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(run_customer_bot())
