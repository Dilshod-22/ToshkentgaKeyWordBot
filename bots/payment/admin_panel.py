"""
Payment Admin Panel - To'lov tizimi uchun kengaytirilgan admin panel
payment_bot.py ga qo'shimcha funksiyalar

Funksiyalar:
- Foydalanuvchini qo'lda qo'shish
- Obuna muddatini uzaytirish
- Foydalanuvchini bloklash/blokdan chiqarish
- To'lov tarixini ko'rish
- Invite linkni qayta yaratish
"""

from aiogram import Bot, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
import json
from pathlib import Path

router = Router()

# Import from payment_bot
from payment_bot import (
    ADMIN_IDS, TARGET_GROUP_ID, PAYMENT_SETTINGS,
    load_json, save_json,
    PAYMENT_REQUESTS_FILE, APPROVED_USERS_FILE
)


class AdminManualAdd(StatesGroup):
    """Qo'lda foydalanuvchi qo'shish"""
    waiting_user_id = State()
    waiting_username = State()
    waiting_duration = State()


# ========================
# ADMIN PANEL KEYBOARDS
# ========================

def admin_main_keyboard():
    """Kengaytirilgan admin keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats"),
            InlineKeyboardButton(text="📋 Arizalar", callback_data="admin_requests")
        ],
        [
            InlineKeyboardButton(text="➕ Qo'lda qo'shish", callback_data="admin_manual_add"),
            InlineKeyboardButton(text="🔄 Obunani uzaytirish", callback_data="admin_extend")
        ],
        [
            InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="admin_users_list"),
            InlineKeyboardButton(text="📜 To'lov tarixi", callback_data="admin_payment_history")
        ],
        [
            InlineKeyboardButton(text="🔗 Linklar", callback_data="admin_links"),
            InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="admin_settings")
        ]
    ])


# ========================
# STATISTIKA
# ========================

@router.callback_query(F.data == "admin_stats")
async def show_detailed_stats(callback: CallbackQuery):
    """Batafsil statistika"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    payment_requests = load_json(PAYMENT_REQUESTS_FILE)
    approved_users = load_json(APPROVED_USERS_FILE)

    # Umumiy statistika
    total_requests = len(payment_requests)
    pending = sum(1 for r in payment_requests.values() if r['status'] == 'pending')
    approved = sum(1 for r in payment_requests.values() if r['status'] == 'approved')
    rejected = sum(1 for r in payment_requests.values() if r['status'] == 'rejected')

    # Daromad
    total_revenue = sum(r['amount'] for r in payment_requests.values() if r['status'] == 'approved')

    # Bugungi statistika
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    today_requests = sum(
        1 for r in payment_requests.values()
        if datetime.fromisoformat(r['requested_at']) >= today_start
    )

    today_revenue = sum(
        r['amount'] for r in payment_requests.values()
        if r['status'] == 'approved' and datetime.fromisoformat(r.get('approved_at', '2000-01-01')) >= today_start
    )

    # Faol foydalanuvchilar
    active_users = 0
    trial_users = 0
    expired_users = 0

    for user_data in approved_users.values():
        if user_data.get('expires_at'):
            expires_at = datetime.fromisoformat(user_data['expires_at'])
            if expires_at > now:
                active_users += 1
            else:
                expired_users += 1
        else:
            # Bepul trial
            approved_at = datetime.fromisoformat(user_data['approved_at'])
            trial_end = approved_at + timedelta(days=3)
            if trial_end > now:
                trial_users += 1
            else:
                expired_users += 1

    stats_text = (
        f"📊 <b>BATAFSIL STATISTIKA</b>\n\n"
        f"<b>📋 Arizalar:</b>\n"
        f"├ Jami: {total_requests}\n"
        f"├ ⏳ Kutilmoqda: {pending}\n"
        f"├ ✅ Tasdiqlangan: {approved}\n"
        f"└ ❌ Rad etilgan: {rejected}\n\n"
        f"<b>👥 Foydalanuvchilar:</b>\n"
        f"├ Jami: {len(approved_users)}\n"
        f"├ ✅ Faol: {active_users}\n"
        f"├ 🆓 Trial: {trial_users}\n"
        f"└ ❌ Tugagan: {expired_users}\n\n"
        f"<b>💰 Daromad:</b>\n"
        f"├ Jami: {total_revenue:,} so'm\n"
        f"└ Bugun: {today_revenue:,} so'm\n\n"
        f"<b>📅 Bugun:</b>\n"
        f"└ Arizalar: {today_requests} ta\n\n"
        f"🕐 {now.strftime('%d.%m.%Y %H:%M')}"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Ortga", callback_data="admin_panel")]
    ])

    await callback.message.edit_text(stats_text, reply_markup=keyboard, parse_mode='html')
    await callback.answer()


# ========================
# QO'LDA QO'SHISH
# ========================

@router.callback_query(F.data == "admin_manual_add")
async def manual_add_start(callback: CallbackQuery, state: FSMContext):
    """Qo'lda foydalanuvchi qo'shish"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    await callback.message.edit_text(
        "➕ <b>Qo'lda qo'shish</b>\n\n"
        "Foydalanuvchi ID sini kiriting:\n"
        "Misol: <code>123456789</code>\n\n"
        "📌 ID ni olish: @userinfobot",
        parse_mode='html'
    )

    await state.set_state(AdminManualAdd.waiting_user_id)
    await callback.answer()


@router.message(AdminManualAdd.waiting_user_id)
async def process_manual_user_id(message: Message, state: FSMContext):
    """User ID qabul qilish"""
    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        user_id = int(message.text.strip())
        await state.update_data(user_id=user_id)

        await message.answer(
            "📝 Username ni kiriting:\n"
            "Misol: <code>@abdumajid</code>",
            parse_mode='html'
        )

        await state.set_state(AdminManualAdd.waiting_username)

    except ValueError:
        await message.answer("❌ Noto'g'ri format! Faqat raqam kiriting.")


@router.message(AdminManualAdd.waiting_username)
async def process_manual_username(message: Message, state: FSMContext):
    """Username qabul qilish"""
    if message.from_user.id not in ADMIN_IDS:
        return

    username = message.text.strip()
    if not username.startswith('@'):
        username = '@' + username

    await state.update_data(username=username, full_name=username)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="7 kun", callback_data="manual_duration_7"),
            InlineKeyboardButton(text="30 kun", callback_data="manual_duration_30")
        ],
        [
            InlineKeyboardButton(text="90 kun", callback_data="manual_duration_90"),
            InlineKeyboardButton(text="365 kun", callback_data="manual_duration_365")
        ],
        [InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="admin_panel")]
    ])

    await message.answer(
        "⏱ Obuna muddatini tanlang:",
        reply_markup=keyboard
    )

    await state.set_state(AdminManualAdd.waiting_duration)


@router.callback_query(F.data.startswith("manual_duration_"))
async def process_manual_duration(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Muddatni tanlash va qo'shish"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    days = int(callback.data.replace("manual_duration_", ""))
    user_data = await state.get_data()

    user_id = user_data['user_id']
    username = user_data['username']
    full_name = user_data['full_name']

    try:
        # Invite link yaratish
        invite_link = await bot.create_chat_invite_link(
            chat_id=TARGET_GROUP_ID,
            member_limit=1,
            name=f"Manual - {username}"
        )

        # Approved users ga qo'shish
        approved_users = load_json(APPROVED_USERS_FILE)

        now = datetime.now()
        expires_at = now + timedelta(days=days)

        approved_users[str(user_id)] = {
            "user_id": user_id,
            "username": username,
            "full_name": full_name,
            "approved_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "paid_amount": 0,  # Qo'lda qo'shilgan
            "invite_link": invite_link.invite_link,
            "added_by": "manual",
            "admin_id": callback.from_user.id
        }

        save_json(APPROVED_USERS_FILE, approved_users)

        # Foydalanuvchiga xabar
        try:
            await bot.send_message(
                chat_id=user_id,
                text=(
                    f"🎉 <b>Sizga premium guruhga kirish ruxsati berildi!</b>\n\n"
                    f"⏱ Obuna muddati: {days} kun\n"
                    f"📅 Tugash sanasi: {expires_at.strftime('%d.%m.%Y')}\n\n"
                    f"🔗 Guruhga kirish:\n{invite_link.invite_link}\n\n"
                    f"⚠️ Bu havola faqat siz uchun!"
                ),
                parse_mode='html'
            )

            await callback.message.edit_text(
                f"✅ <b>Qo'shildi!</b>\n\n"
                f"👤 User ID: <code>{user_id}</code>\n"
                f"📱 Username: {username}\n"
                f"⏱ Muddat: {days} kun\n"
                f"📅 Tugaydi: {expires_at.strftime('%d.%m.%Y')}\n\n"
                f"🔗 Link yuborildi!",
                parse_mode='html'
            )

        except Exception as e:
            await callback.message.edit_text(
                f"✅ Qo'shildi, lekin xabar yuborib bo'lmadi:\n{e}\n\n"
                f"🔗 Link:\n{invite_link.invite_link}",
                parse_mode='html'
            )

        await state.clear()
        await callback.answer("✅ Qo'shildi!", show_alert=True)

    except Exception as e:
        await callback.answer(f"❌ Xatolik: {e}", show_alert=True)


# ========================
# OBUNANI UZAYTIRISH
# ========================

@router.callback_query(F.data == "admin_extend")
async def extend_subscription_menu(callback: CallbackQuery):
    """Obunani uzaytirish menyusi"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    approved_users = load_json(APPROVED_USERS_FILE)

    # So'nggi 20 ta foydalanuvchi
    users_list = list(approved_users.values())[-20:]
    users_list.reverse()

    keyboard_buttons = []

    for user in users_list:
        expires_at = user.get('expires_at', 'Noma\'lum')
        if expires_at != 'Noma\'lum':
            try:
                exp = datetime.fromisoformat(expires_at)
                days_left = (exp - datetime.now()).days
                status = f"📅 {days_left}k" if days_left > 0 else "❌"
            except:
                status = "❓"
        else:
            status = "🆓"

        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"{user['username']} {status}",
                callback_data=f"extend_user_{user['user_id']}"
            )
        ])

    keyboard_buttons.append([
        InlineKeyboardButton(text="🔙 Ortga", callback_data="admin_panel")
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await callback.message.edit_text(
        "🔄 <b>Obunani uzaytirish</b>\n\n"
        "Foydalanuvchini tanlang:",
        reply_markup=keyboard,
        parse_mode='html'
    )
    await callback.answer()


@router.callback_query(F.data.startswith("extend_user_"))
async def extend_user_select_duration(callback: CallbackQuery):
    """Foydalanuvchi uchun muddat tanlash"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    user_id = callback.data.replace("extend_user_", "")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="+7 kun", callback_data=f"extend_confirm_{user_id}_7"),
            InlineKeyboardButton(text="+30 kun", callback_data=f"extend_confirm_{user_id}_30")
        ],
        [
            InlineKeyboardButton(text="+90 kun", callback_data=f"extend_confirm_{user_id}_90"),
            InlineKeyboardButton(text="+365 kun", callback_data=f"extend_confirm_{user_id}_365")
        ],
        [InlineKeyboardButton(text="🔙 Ortga", callback_data="admin_extend")]
    ])

    await callback.message.edit_text(
        f"🔄 User ID: <code>{user_id}</code>\n\n"
        "Qancha uzaytirish kerak?",
        reply_markup=keyboard,
        parse_mode='html'
    )
    await callback.answer()


@router.callback_query(F.data.startswith("extend_confirm_"))
async def extend_confirm(callback: CallbackQuery, bot: Bot):
    """Obunani uzaytirish"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    parts = callback.data.replace("extend_confirm_", "").split("_")
    user_id = parts[0]
    days = int(parts[1])

    approved_users = load_json(APPROVED_USERS_FILE)

    if user_id not in approved_users:
        await callback.answer("❌ Foydalanuvchi topilmadi!", show_alert=True)
        return

    user_data = approved_users[user_id]
    now = datetime.now()

    # Hozirgi muddat
    if user_data.get('expires_at'):
        current_expires = datetime.fromisoformat(user_data['expires_at'])
        if current_expires > now:
            new_expires = current_expires + timedelta(days=days)
        else:
            new_expires = now + timedelta(days=days)
    else:
        new_expires = now + timedelta(days=days)

    user_data['expires_at'] = new_expires.isoformat()
    approved_users[user_id] = user_data
    save_json(APPROVED_USERS_FILE, approved_users)

    # Foydalanuvchiga xabar
    try:
        await bot.send_message(
            chat_id=int(user_id),
            text=(
                f"🎉 <b>Obunangiz uzaytirildi!</b>\n\n"
                f"➕ Qo'shildi: {days} kun\n"
                f"📅 Yangi tugash sanasi: {new_expires.strftime('%d.%m.%Y')}\n\n"
                f"✅ Guruhda faoliyat davom ettirishingiz mumkin!"
            ),
            parse_mode='html'
        )
    except:
        pass

    await callback.message.edit_text(
        f"✅ <b>Uzaytirildi!</b>\n\n"
        f"👤 {user_data['username']}\n"
        f"➕ {days} kun\n"
        f"📅 Tugaydi: {new_expires.strftime('%d.%m.%Y')}",
        parse_mode='html'
    )

    await callback.answer("✅ Uzaytirildi!", show_alert=True)


# ========================
# ADMIN PANEL
# ========================

@router.callback_query(F.data == "admin_panel")
async def show_admin_panel(callback: CallbackQuery):
    """Admin panelni ko'rsatish"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    await callback.message.edit_text(
        "👨‍💼 <b>Admin Panel</b>\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=admin_main_keyboard(),
        parse_mode='html'
    )
    await callback.answer()


@router.message(F.text == "/admin")
async def admin_command(message: Message):
    """Admin panel buyrug'i"""
    if message.from_user.id not in ADMIN_IDS:
        return

    await message.answer(
        "👨‍💼 <b>Admin Panel</b>\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=admin_main_keyboard(),
        parse_mode='html'
    )
