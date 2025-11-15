"""
Payment Bot - To'lov qabul qilish va guruhga qo'shish
Individual invite link tizimi bilan

Ish jarayoni:
1. Foydalanuvchi botga username yuboradi
2. Bot karta raqam va to'lov summasi ko'rsatadi
3. Foydalanuvchi screenshot yuboradi
4. Admin tasdiqlaydi
5. Foydalanuvchiga INDIVIDUAL invite link yuboriladi (faqat bir marta)
"""

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
import json
from datetime import datetime
from pathlib import Path

# Config
PAYMENT_BOT_TOKEN = "YOUR_PAYMENT_BOT_TOKEN_HERE"  # Bu yerga payment bot tokenini kiriting
ADMIN_IDS = [7106025530, 5129045986]  # Adminlar ro'yxati
TARGET_GROUP_ID = "YOUR_TARGET_GROUP_ID"  # Asosiy guruh ID (-100 bilan)

# To'lov sozlamalari
PAYMENT_SETTINGS = {
    "card_number": "8600 1234 5678 9012",  # Karta raqam
    "card_holder": "ABDUMAJID ABDUMAJIDOV",  # Karta egasi
    "amount": 30000,  # Narx (so'm)
    "validity_days": 30  # Obuna muddati (kun)
}

# Ma'lumotlar fayllari
PAYMENT_REQUESTS_FILE = "payment_requests.json"
APPROVED_USERS_FILE = "approved_users.json"

router = Router()


class PaymentForm(StatesGroup):
    """To'lov jarayoni FSM states"""
    waiting_username = State()
    waiting_screenshot = State()


def load_json(file_path: str) -> dict:
    """JSON fayldan ma'lumot yuklash"""
    if not Path(file_path).exists():
        return {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}


def save_json(file_path: str, data: dict):
    """JSON faylga ma'lumot saqlash"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main_keyboard():
    """Asosiy keyboard"""
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [KeyboardButton(text="💳 Guruhga qo'shilish")],
            [KeyboardButton(text="ℹ️ Ma'lumot"), KeyboardButton(text="📞 Yordam")]
        ]
    )


def admin_keyboard():
    """Admin keyboard"""
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [KeyboardButton(text="📊 Statistika")],
            [KeyboardButton(text="📋 To'lov arizalari")],
            [KeyboardButton(text="👥 Tasdiqlangan foydalanuvchilar")],
            [KeyboardButton(text="⚙️ Sozlamalar")]
        ]
    )


@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    """Start handler"""
    user_id = message.from_user.id

    # Admin uchun
    if user_id in ADMIN_IDS:
        await message.answer(
            "👋 <b>Admin Panel</b>\n\n"
            "Guruhga qo'shilish uchun to'lov qabul qilish tizimi",
            reply_markup=admin_keyboard(),
            parse_mode='html'
        )
    else:
        # Oddiy foydalanuvchi
        await message.answer(
            "👋 <b>Xush kelibsiz!</b>\n\n"
            "🎯 <b>Premium guruhga qo'shilish</b>\n\n"
            "💰 Narx: <b>30,000 so'm</b> / oy\n"
            "⏱ Obuna muddati: <b>30 kun</b>\n\n"
            "📝 Ro'yxatdan o'tish uchun pastdagi tugmani bosing",
            reply_markup=main_keyboard(),
            parse_mode='html'
        )

    await state.clear()


@router.message(F.text == "💳 Guruhga qo'shilish")
async def join_group_handler(message: Message, state: FSMContext):
    """Guruhga qo'shilish jarayonini boshlash"""
    user_id = message.from_user.id

    # Avval tasdiqlangan foydalanuvchilarni tekshirish
    approved_users = load_json(APPROVED_USERS_FILE)

    if str(user_id) in approved_users:
        user_data = approved_users[str(user_id)]
        await message.answer(
            "✅ <b>Siz allaqachon guruhga qo'shilgansiz!</b>\n\n"
            f"📅 Qo'shilgan sana: {user_data.get('approved_at', 'Noma\\'lum')}\n"
            f"⏱ Obuna tugash sanasi: {user_data.get('expires_at', 'Noma\\'lum')}",
            parse_mode='html'
        )
        return

    # To'lov jarayonini boshlash
    await message.answer(
        "📝 <b>Ro'yxatdan o'tish</b>\n\n"
        "Telegram akkauntingizning <b>username</b>ini kiriting\n"
        "Misol: @abdumajid\n\n"
        "⚠️ <i>Username bo'lmasa, avval sozlamalarda yarating</i>",
        parse_mode='html'
    )
    await state.set_state(PaymentForm.waiting_username)


@router.message(PaymentForm.waiting_username)
async def process_username(message: Message, state: FSMContext):
    """Username qabul qilish"""
    username = message.text.strip()

    # Username formatini tekshirish
    if not username.startswith('@'):
        username = '@' + username

    # Ma'lumotlarni saqlash
    await state.update_data(
        username=username,
        user_id=message.from_user.id,
        full_name=message.from_user.full_name,
        started_at=datetime.now().isoformat()
    )

    # Karta ma'lumotlarini yuborish
    card_info = (
        f"💳 <b>To'lov ma'lumotlari</b>\n\n"
        f"Karta raqam: <code>{PAYMENT_SETTINGS['card_number']}</code>\n"
        f"Karta egasi: <b>{PAYMENT_SETTINGS['card_holder']}</b>\n"
        f"Summa: <b>{PAYMENT_SETTINGS['amount']:,} so'm</b>\n\n"
        f"📸 <b>To'lovni amalga oshirgandan keyin screenshot yuboring</b>\n\n"
        f"⚠️ Screenshot aniq va o'qilishi oson bo'lishi kerak!"
    )

    await message.answer(card_info, parse_mode='html')
    await state.set_state(PaymentForm.waiting_screenshot)


@router.message(PaymentForm.waiting_screenshot, F.photo)
async def process_screenshot(message: Message, state: FSMContext, bot: Bot):
    """Screenshot qabul qilish va adminga yuborish"""
    user_data = await state.get_data()

    # Request ID yaratish
    request_id = f"PAY_{message.from_user.id}_{int(datetime.now().timestamp())}"

    # To'lov arizasini saqlash
    payment_requests = load_json(PAYMENT_REQUESTS_FILE)

    payment_requests[request_id] = {
        "request_id": request_id,
        "user_id": message.from_user.id,
        "username": user_data['username'],
        "full_name": user_data['full_name'],
        "screenshot_file_id": message.photo[-1].file_id,
        "requested_at": datetime.now().isoformat(),
        "status": "pending",
        "amount": PAYMENT_SETTINGS['amount']
    }

    save_json(PAYMENT_REQUESTS_FILE, payment_requests)

    # Foydalanuvchiga javob
    await message.answer(
        "✅ <b>Arizangiz qabul qilindi!</b>\n\n"
        "⏳ Admin tekshirgandan keyin sizga guruh havolasi yuboriladi.\n"
        "⏱ Odatda 5-10 daqiqa ichida javob beriladi.\n\n"
        "📞 Yordam kerak bo'lsa: /help",
        parse_mode='html'
    )

    # Adminga xabar yuborish
    admin_message = (
        f"🆕 <b>Yangi to'lov arizasi!</b>\n\n"
        f"👤 Foydalanuvchi: {user_data['full_name']}\n"
        f"📱 Username: {user_data['username']}\n"
        f"🆔 User ID: <code>{message.from_user.id}</code>\n"
        f"💰 Summa: <b>{PAYMENT_SETTINGS['amount']:,} so'm</b>\n"
        f"📅 Sana: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        f"🔑 Ariza ID: <code>{request_id}</code>"
    )

    # Tasdiqlash tugmalari
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{request_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{request_id}")
        ]
    ])

    # Barcha adminlarga yuborish
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_photo(
                chat_id=admin_id,
                photo=message.photo[-1].file_id,
                caption=admin_message,
                reply_markup=keyboard,
                parse_mode='html'
            )
        except Exception as e:
            print(f"Admin {admin_id} ga yuborishda xatolik: {e}")

    await state.clear()


@router.message(PaymentForm.waiting_screenshot)
async def wrong_screenshot_format(message: Message):
    """Noto'g'ri format (rasm emas)"""
    await message.answer(
        "❌ <b>Iltimos, to'lov screenshotini rasm sifatida yuboring!</b>\n\n"
        "📸 Rasm yuborish uchun:\n"
        "1. Telefoningizda screenshotni oching\n"
        "2. Botga rasm sifatida yuboring\n\n"
        "⚠️ Fayl, dokument yoki link emas!",
        parse_mode='html'
    )


@router.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: CallbackQuery, bot: Bot):
    """To'lovni tasdiqlash va guruh linki yuborish"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Sizda ruxsat yo'q!", show_alert=True)
        return

    request_id = callback.data.replace("approve_", "")

    # Arizani yuklash
    payment_requests = load_json(PAYMENT_REQUESTS_FILE)

    if request_id not in payment_requests:
        await callback.answer("❌ Ariza topilmadi!", show_alert=True)
        return

    request_data = payment_requests[request_id]

    if request_data['status'] != 'pending':
        await callback.answer("⚠️ Bu ariza allaqachon ko'rib chiqilgan!", show_alert=True)
        return

    try:
        # INDIVIDUAL invite link yaratish (faqat 1 marta, 1 kishi uchun)
        invite_link = await bot.create_chat_invite_link(
            chat_id=TARGET_GROUP_ID,
            member_limit=1,  # Faqat 1 kishi
            expire_date=None,  # Muddatsiz
            name=f"Premium - {request_data['username']}"
        )

        # Arizani tasdiqlangan deb belgilash
        request_data['status'] = 'approved'
        request_data['approved_at'] = datetime.now().isoformat()
        request_data['approved_by'] = callback.from_user.id
        request_data['invite_link'] = invite_link.invite_link
        payment_requests[request_id] = request_data
        save_json(PAYMENT_REQUESTS_FILE, payment_requests)

        # Tasdiqlangan foydalanuvchilar ro'yxatiga qo'shish
        approved_users = load_json(APPROVED_USERS_FILE)
        approved_users[str(request_data['user_id'])] = {
            "user_id": request_data['user_id'],
            "username": request_data['username'],
            "full_name": request_data['full_name'],
            "approved_at": datetime.now().isoformat(),
            "expires_at": None,  # Keyinchalik qo'shish mumkin
            "paid_amount": request_data['amount'],
            "invite_link": invite_link.invite_link
        }
        save_json(APPROVED_USERS_FILE, approved_users)

        # Foydalanuvchiga guruh linkini yuborish
        user_message = (
            f"🎉 <b>Tabriklaymiz!</b>\n\n"
            f"✅ To'lovingiz tasdiqlandi!\n"
            f"💰 Summa: {request_data['amount']:,} so'm\n\n"
            f"🔗 <b>Guruhga kirish uchun havola:</b>\n"
            f"{invite_link.invite_link}\n\n"
            f"⚠️ <b>MUHIM:</b>\n"
            f"• Bu havola faqat SIZ uchun\n"
            f"• Faqat 1 marta ishlatiladi\n"
            f"• Boshqalar bilan bo'lishish MUMKIN EMAS\n\n"
            f"📝 Guruhda barcha xabarlar 30 kun davomida mavjud bo'ladi"
        )

        await bot.send_message(
            chat_id=request_data['user_id'],
            text=user_message,
            parse_mode='html'
        )

        # Adminga tasdiqlangan xabar
        await callback.message.edit_caption(
            caption=callback.message.caption + f"\n\n✅ <b>TASDIQLANDI</b> - {callback.from_user.full_name}",
            parse_mode='html'
        )

        await callback.answer("✅ To'lov tasdiqlandi va link yuborildi!", show_alert=True)

    except Exception as e:
        await callback.answer(f"❌ Xatolik: {e}", show_alert=True)
        print(f"Tasdiqlashda xatolik: {e}")


@router.callback_query(F.data.startswith("reject_"))
async def reject_payment(callback: CallbackQuery, bot: Bot):
    """To'lovni rad etish"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Sizda ruxsat yo'q!", show_alert=True)
        return

    request_id = callback.data.replace("reject_", "")

    # Arizani yuklash
    payment_requests = load_json(PAYMENT_REQUESTS_FILE)

    if request_id not in payment_requests:
        await callback.answer("❌ Ariza topilmadi!", show_alert=True)
        return

    request_data = payment_requests[request_id]

    if request_data['status'] != 'pending':
        await callback.answer("⚠️ Bu ariza allaqachon ko'rib chiqilgan!", show_alert=True)
        return

    # Arizani rad etilgan deb belgilash
    request_data['status'] = 'rejected'
    request_data['rejected_at'] = datetime.now().isoformat()
    request_data['rejected_by'] = callback.from_user.id
    payment_requests[request_id] = request_data
    save_json(PAYMENT_REQUESTS_FILE, payment_requests)

    # Foydalanuvchiga xabar
    await bot.send_message(
        chat_id=request_data['user_id'],
        text=(
            "❌ <b>To'lovingiz rad etildi</b>\n\n"
            "⚠️ Sabab: Screenshot noaniq yoki to'lov summasi to'g'ri kelmaydi\n\n"
            "📞 Yordam uchun admin bilan bog'laning:\n"
            "@admin"
        ),
        parse_mode='html'
    )

    # Adminga xabar
    await callback.message.edit_caption(
        caption=callback.message.caption + f"\n\n❌ <b>RAD ETILDI</b> - {callback.from_user.full_name}",
        parse_mode='html'
    )

    await callback.answer("❌ To'lov rad etildi", show_alert=True)


@router.message(F.text == "📊 Statistika")
async def stats_handler(message: Message):
    """Statistika (faqat adminlar)"""
    if message.from_user.id not in ADMIN_IDS:
        return

    payment_requests = load_json(PAYMENT_REQUESTS_FILE)
    approved_users = load_json(APPROVED_USERS_FILE)

    total_requests = len(payment_requests)
    pending = sum(1 for r in payment_requests.values() if r['status'] == 'pending')
    approved = sum(1 for r in payment_requests.values() if r['status'] == 'approved')
    rejected = sum(1 for r in payment_requests.values() if r['status'] == 'rejected')

    total_revenue = sum(r['amount'] for r in payment_requests.values() if r['status'] == 'approved')

    stats_text = (
        f"📊 <b>Statistika</b>\n\n"
        f"📋 Jami arizalar: {total_requests}\n"
        f"⏳ Kutilmoqda: {pending}\n"
        f"✅ Tasdiqlangan: {approved}\n"
        f"❌ Rad etilgan: {rejected}\n\n"
        f"👥 Aktiv foydalanuvchilar: {len(approved_users)}\n"
        f"💰 Jami daromad: {total_revenue:,} so'm"
    )

    await message.answer(stats_text, parse_mode='html')


@router.message(F.text == "📋 To'lov arizalari")
async def pending_requests_handler(message: Message):
    """Kutilayotgan arizalar (faqat adminlar)"""
    if message.from_user.id not in ADMIN_IDS:
        return

    payment_requests = load_json(PAYMENT_REQUESTS_FILE)

    pending = [r for r in payment_requests.values() if r['status'] == 'pending']

    if not pending:
        await message.answer("✅ Kutilayotgan arizalar yo'q")
        return

    text = f"📋 <b>Kutilayotgan arizalar: {len(pending)} ta</b>\n\n"

    for i, req in enumerate(pending[:10], 1):
        text += (
            f"{i}. {req['full_name']} ({req['username']})\n"
            f"   💰 {req['amount']:,} so'm\n"
            f"   📅 {req['requested_at'][:16]}\n\n"
        )

    await message.answer(text, parse_mode='html')


@router.message(F.text == "ℹ️ Ma'lumot")
async def info_handler(message: Message):
    """Ma'lumot"""
    info_text = (
        "ℹ️ <b>Premium Guruh haqida</b>\n\n"
        "💰 Narx: <b>30,000 so'm</b> / oy\n"
        "⏱ Obuna muddati: <b>30 kun</b>\n\n"
        "📝 <b>Nima olasiz:</b>\n"
        "• Taksi zakazlari (real-time)\n"
        "• Kalit so'zlar bo'yicha filter\n"
        "• 24/7 yangilanishlar\n\n"
        "🔒 <b>Xavfsizlik:</b>\n"
        "• Har bir foydalanuvchi uchun individual link\n"
        "• Link faqat 1 marta ishlatiladi\n"
        "• Boshqalar sizning linkingizdan foydalana olmaydi"
    )

    await message.answer(info_text, parse_mode='html')


async def run_payment_bot():
    """Payment botni ishga tushirish"""
    bot = Bot(token=PAYMENT_BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    print("💳 Payment Bot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_payment_bot())
