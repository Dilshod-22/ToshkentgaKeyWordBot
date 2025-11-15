from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from core.storage import load_state, save_state, get_items, add_item, get_default_state, remove_item
from core.config import ADMIN_BOT_TOKEN, ADMIN_IDS

router = Router()
ITEMS_PER_PAGE = 20

class AdminForm(StatesGroup):
    input_value = State()
    context = State()
    group_type_selection = State()  # Source group type tanlash uchun

SECTION_KEYS = {
    "keyword": "keywords",
    "source": "source_groups",
    "target": "target_groups",
    "blackword": "blackwords"  # Yangi
}

SECTION_NAMES = {
    "keyword": "🔑 Kalit so'z",
    "source": "📥 Source guruh",
    "target": "📤 Target guruh",
    "blackword": "🚫 Qora ro'yxat so'z"  # Yangi
}

def main_keyboard():
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [KeyboardButton(text="🔑 Kalit so'zlar")],
            [KeyboardButton(text="🚫 Qora ro'yxat so'zlar")],  # Yangi
            [KeyboardButton(text="📥 Source guruhlar")],
            [KeyboardButton(text="📤 Target guruhlar")],
            [KeyboardButton(text="⚡ Buffer guruh")],
            [KeyboardButton(text="📊 Statistika")]
        ]
    )

def section_keyboard(section: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Qo'shish", callback_data=f"add_{section}"),
            InlineKeyboardButton(text="❌ O'chirish", callback_data=f"del_{section}")
        ],
        [InlineKeyboardButton(text="📄 Ro'yxat", callback_data=f"list_{section}_0")],
        [InlineKeyboardButton(text="🔙 Ortga", callback_data="back_main")]
    ])

@router.message(Command("start"))
async def start_handler(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Sizda huquq yo'q!")
        return
    
    await message.answer(
        "👋 <b>Admin panel</b>\n\n"
        "🔑 Kalit so'zlar\n"
        "🚫 Qora ro'yxat so'zlar\n"
        "📥 Source guruhlar\n"
        "📤 Target guruhlar",
        reply_markup=main_keyboard(),
        parse_mode='html'
    )

@router.message(F.text == "🔑 Kalit so'zlar")
async def keyword_menu(message: Message):
    await message.answer("🔑 <b>Kalit so'zlar</b>", reply_markup=section_keyboard("keyword"), parse_mode='html')

@router.message(F.text == "🚫 Qora ro'yxat so'zlar")
async def blackword_menu(message: Message):
    await message.answer(
        "🚫 <b>Qora ro'yxat so'zlar</b>\n\n"
        "ℹ️ Bu so'zlar xabarda bo'lsa, keyword topilsa ham xabar yuborilmaydi.\n"
        "Reklama va spam xabarlarni filterlash uchun.",
        reply_markup=section_keyboard("blackword"),
        parse_mode='html'
    )

@router.message(F.text == "📥 Source guruhlar")
async def source_menu(message: Message):
    await message.answer("📥 <b>Source guruhlar</b>", reply_markup=section_keyboard("source"), parse_mode='html')

@router.message(F.text == "📤 Target guruhlar")
async def target_menu(message: Message):
    await message.answer("📤 <b>Target guruhlar</b>", reply_markup=section_keyboard("target"), parse_mode='html')

@router.message(F.text == "⚡ Buffer guruh")
async def buffer_menu(message: Message):
    data = load_state()
    buffer = data.get("buffer_group", "")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ O'zgartirish", callback_data="edit_buffer")],
        [InlineKeyboardButton(text="🔙 Ortga", callback_data="back_main")]
    ])

    buffer_text = (
        f"⚡ <b>Buffer guruh/kanal</b>\n\n"
        f"Joriy buffer: <code>{buffer if buffer else '❌ Sozlanmagan'}</code>\n\n"
        f"ℹ️ Buffer guruh/kanal FAST source guruhlar uchun ishlatiladi.\n"
        f"Xabar darhol bu yerga yuboriladi (faqat message matni va User ID).\n\n"
        f"📌 Private channel link: https://t.me/+WwUJqcj886ozNzIy\n"
        f"📌 Channel ID ni olish uchun: @username_to_id_bot"
    )
    await message.answer(buffer_text, reply_markup=keyboard, parse_mode='html')


@router.callback_query(F.data == "edit_buffer")
async def edit_buffer_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "⚡ <b>Buffer guruh/kanal ID ni yuboring:</b>\n\n"
        "Misol: <code>-1001234567890</code>\n\n"
        "📌 Private channel: https://t.me/+WwUJqcj886ozNzIy\n"
        "📌 ID olish: @username_to_id_bot ga link yuboring\n\n"
        "Yoki bo'sh qoldirish uchun: <code>0</code>",
        parse_mode='html'
    )
    await state.update_data(context="buffer")
    await state.set_state(AdminForm.input_value)
    await callback.answer()


@router.message(F.text == "📊 Statistika")
async def stats_handler(message: Message):
    data = load_state()

    # Source guruhlarni type bo'yicha hisoblash
    source_groups = data.get('source_groups', [])
    fast_count = sum(1 for g in source_groups if isinstance(g, dict) and g.get('type') == 'fast')
    normal_count = sum(1 for g in source_groups if isinstance(g, dict) and g.get('type') == 'normal')

    buffer = data.get('buffer_group', '')

    stats_text = (
        f"📊 <b>Statistika</b>\n\n"
        f"🔑 Kalit so'zlar: {len(data.get('keywords', []))} ta\n"
        f"🚫 Qora ro'yxat so'zlar: {len(data.get('blackwords', []))} ta\n"
        f"📥 Source guruhlar: {len(source_groups)} ta\n"
        f"   ⚡ FAST: {fast_count} ta\n"
        f"   📝 NORMAL: {normal_count} ta\n"
        f"📤 Target guruhlar: {len(data.get('target_groups', []))} ta\n"
        f"⚡ Buffer guruh: {'✅ Sozlangan' if buffer else '❌ Sozlanmagan'}"
    )
    await message.answer(stats_text, parse_mode='html')

@router.callback_query(F.data.startswith("list_"))
async def list_items_handler(callback: CallbackQuery):
    parts = callback.data.split("_")
    section = parts[1]
    page = int(parts[2])
    
    key = SECTION_KEYS.get(section)
    items = get_items(key)
    
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_items = items[start:end]
    
    msg = "\n".join(f"{i+1+start}. <code>{v}</code>" for i, v in enumerate(page_items)) or "🚫 Bo'sh"
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"list_{section}_{page-1}"))
    if end < len(items):
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"list_{section}_{page+1}"))
    
    keyboard = []
    if nav_buttons:
        keyboard.append(nav_buttons)
    keyboard.append([InlineKeyboardButton(text="🔙 Ortga", callback_data=f"back_{section}")])
    
    await callback.message.edit_text(
        f"<b>{SECTION_NAMES.get(section)}</b>\n\n{msg}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode='html'
    )
    await callback.answer()

@router.callback_query(F.data.startswith("add_"))
async def add_item_prompt(callback: CallbackQuery, state: FSMContext):
    section = callback.data.replace("add_", "")

    # Source group uchun type tanlash
    if section == "source":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚡ FAST (admin botli guruh)", callback_data="type_fast")],
            [InlineKeyboardButton(text="📝 NORMAL (oddiy guruh)", callback_data="type_normal")],
            [InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="back_source")]
        ])
        await callback.message.edit_text(
            "⚙️ <b>Source guruh turini tanlang:</b>\n\n"
            "⚡ <b>FAST</b> - Admin botli guruhlar (xabar tez o'chib ketadi)\n"
            "   → Darhol buffer guruhga yuboriladi (username + telefon)\n"
            "   → Keyin formatlab asosiy guruhga yuboriladi\n\n"
            "📝 <b>NORMAL</b> - Oddiy guruhlar\n"
            "   → Bevosita formatlab asosiy guruhga yuboriladi",
            reply_markup=keyboard,
            parse_mode='html'
        )
        await state.update_data(context=section)
        await state.set_state(AdminForm.group_type_selection)
    else:
        await callback.message.edit_text(f"➕ Yangi {SECTION_NAMES.get(section)} yuboring:", parse_mode='html')
        await state.update_data(context=section)
        await state.set_state(AdminForm.input_value)

    await callback.answer()

@router.callback_query(F.data.startswith("type_"))
async def select_group_type(callback: CallbackQuery, state: FSMContext):
    """Source group type tanlaganda"""
    group_type = callback.data.replace("type_", "")  # "fast" yoki "normal"

    await state.update_data(selected_type=group_type)
    await callback.message.edit_text(
        f"➕ Yangi source guruh yuboring:\n"
        f"Turini: <b>{'⚡ FAST' if group_type == 'fast' else '📝 NORMAL'}</b>",
        parse_mode='html'
    )
    await state.set_state(AdminForm.input_value)
    await callback.answer()


@router.callback_query(F.data.startswith("back_"))
async def back_handler(callback: CallbackQuery):
    """Ortga tugmalari uchun handler"""
    section = callback.data.replace("back_", "")

    if section == "main":
        await callback.message.delete()
        await callback.message.answer(
            "👋 <b>Admin panel</b>\n\n"
            "🔑 Kalit so'zlar\n"
            "🚫 Qora ro'yxat so'zlar\n"
            "📥 Source guruhlar\n"
            "📤 Target guruhlar",
            reply_markup=main_keyboard(),
            parse_mode='html'
        )
    elif section == "keyword":
        await callback.message.edit_text("🔑 <b>Kalit so'zlar</b>", reply_markup=section_keyboard("keyword"), parse_mode='html')
    elif section == "blackword":
        await callback.message.edit_text(
            "🚫 <b>Qora ro'yxat so'zlar</b>\n\n"
            "ℹ️ Bu so'zlar xabarda bo'lsa, keyword topilsa ham xabar yuborilmaydi.",
            reply_markup=section_keyboard("blackword"),
            parse_mode='html'
        )
    elif section == "source":
        await callback.message.edit_text("📥 <b>Source guruhlar</b>", reply_markup=section_keyboard("source"), parse_mode='html')
    elif section == "target":
        await callback.message.edit_text("📤 <b>Target guruhlar</b>", reply_markup=section_keyboard("target"), parse_mode='html')

    await callback.answer()


@router.callback_query(F.data.startswith("del_"))
async def del_item_prompt(callback: CallbackQuery, state: FSMContext):
    section = callback.data.replace("del_", "")
    await callback.message.edit_text(f"❌ O'chirish uchun {SECTION_NAMES.get(section)}ni yuboring:", parse_mode='html')
    await state.update_data(context=f"del_{section}")
    await state.set_state(AdminForm.input_value)
    await callback.answer()

@router.message(AdminForm.input_value)
async def process_input(message: Message, state: FSMContext):
    user_data = await state.get_data()
    context = user_data.get("context")
    value = message.text.strip()

    # Buffer guruh sozlash
    if context == "buffer":
        data = load_state()
        if value == "0":
            data["buffer_group"] = ""
            await message.answer("⚡ Buffer guruh o'chirildi", parse_mode='html')
        else:
            data["buffer_group"] = value
            await message.answer(f"⚡ Buffer guruh o'zgartirildi: <code>{value}</code>", parse_mode='html')
        save_state(data)
        await state.clear()
        return

    if "t.me/" in value:
        value = value.split("/")[-1].strip()

    is_delete = context.startswith("del_")
    section = context.replace("del_", "")
    key = SECTION_KEYS.get(section)

    if is_delete:
        remove_item(key, value)
    else:
        # Source group uchun type ni o'tkazish
        if section == "source":
            selected_type = user_data.get("selected_type", "normal")
            add_item(key, value, item_type=selected_type)
        else:
            add_item(key, value)

    await state.clear()

async def run_admin_bot():
    bot = Bot(token=ADMIN_BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)