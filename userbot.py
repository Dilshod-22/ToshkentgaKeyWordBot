import re
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.raw import types, functions
from pyrogram.raw.types import (
    UpdateNewMessage,
    UpdateNewChannelMessage,
    PeerChannel,
    Message,
    MessageEntityPhone
)
from storage import save_state, load_state

# ⚡ TEZLIK UCHUN: uvloop event loop (agar mavjud bo'lsa)
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    print("⚡ uvloop yoqildi (maksimal tezlik)")
except ImportError:
    print("ℹ️  uvloop topilmadi, standart asyncio ishlatilmoqda")

# API credentials
api_id = 35590072
api_hash = "48e5dad8bef68a54aac5b2ce0702b82c"

# ⚡ PYROGRAM CLIENT - TEZROQ VA ZAMONAVIY
app = Client(
    "pyrogram_session",
    api_id=api_id,
    api_hash=api_hash
)

handler_registered = False

# ⚡ CACHE: Tezlik uchun source guruhlarni xotirada saqlash
source_groups_cache = {
    "fast": {},      # {chat_id: group_info}
    "normal": {}     # {chat_id: group_info}
}


def check_keyword_match(text, keywords):
    """Kalit so'zlarni tekshirish - OPTIMIZATSIYA QILINGAN"""
    if not text:
        return None

    text_lower = text.lower()

    # 1. Ko'p so'zli kalit so'zlar (tez tekshirish)
    for kw in keywords:
        if ' ' in kw and kw in text_lower:
            return kw

    # 2. Bitta so'zli kalit so'zlar
    words = set(re.findall(r'\b\w+\b', text_lower))
    for kw in keywords:
        if ' ' not in kw and kw in words:
            return kw

    return None


def check_blackword(text, blackwords):
    """Qora ro'yxat so'zlarini tekshirish"""
    if not text or not blackwords:
        return None

    text_lower = text.lower()

    # Qora ro'yxat so'zlarini tekshirish
    for bw in blackwords:
        if ' ' in bw:
            # Ko'p so'zli blackword
            if bw in text_lower:
                return bw
        else:
            # Bitta so'zli blackword
            words = set(re.findall(r'\b\w+\b', text_lower))
            if bw in words:
                return bw

    return None


async def get_sender_details(chat_id, user_id):
    """
    Sender ma'lumotlarini olish (async) - NORMAL guruhlar uchun
    Pyrogram orqali to'liq ma'lumot olish
    """
    try:
        # Chat member ma'lumotlarini olish
        member = await app.get_chat_member(chat_id, user_id)
        user = member.user

        if user is None:
            return None

        user_info = {
            "name": f"{user.first_name or ''} {user.last_name or ''}".strip(),
            "username": f"@{user.username}" if user.username else None,
            "phone": user.phone_number if hasattr(user, 'phone_number') else None,
            "user_id": user.id
        }

        return user_info
    except Exception as e:
        print(f"⚠️  Sender details xatolik: {e}")
        return None


async def update_source_groups():
    """
    Cache'ni yangilash - bot_state.json dan configured guruhlarni o'qib cache'ga yuklash
    ESLATMA: Bu funksiya bot_state.json ni O'ZGARTIRMAYDI, faqat cache'ni yangilaydi!
    """
    print("🔄 Cache yangilanmoqda...")

    # FAQAT cache'ni yangilash - bot_state.json ga tegmaslik!
    await rebuild_cache()

    state = load_state()
    configured_sources = state.get("source_groups", [])
    print(f"✅ {len(configured_sources)} ta configured guruh cache'ga yuklandi")


async def rebuild_cache():
    """Cache'ni qayta qurish - TEZLIK UCHUN"""
    global source_groups_cache

    state = load_state()
    source_groups = state.get("source_groups", [])

    # Cache'ni tozalash
    source_groups_cache = {"fast": {}, "normal": {}}

    for group in source_groups:
        if isinstance(group, dict):
            group_id = group.get("id")
            group_type = group.get("type", "normal")
        else:
            group_id = group
            group_type = "normal"

        try:
            # Guruhni olish (Pyrogram)
            if group_id.isdigit() or (group_id.startswith('-') and group_id[1:].isdigit()):
                chat = await app.get_chat(int(group_id))
            else:
                chat = await app.get_chat(group_id)

            chat_id = chat.id
            username = chat.username

            group_info = {
                "id": chat_id,
                "username": username,
                "original_key": group_id
            }

            # Cache'ga qo'shish
            source_groups_cache[group_type][chat_id] = group_info

            # ⚡ QOSIMCHA: FAST guruhlar uchun userlarni cache'ga yuklash
            if group_type == "fast":
                try:
                    print(f"📥 {group_id} guruhidan userlarni cache'ga yuklash...")
                    # Oxirgi 100 ta xabarni olish (Pyrogram cache'ga yuklaydi)
                    count = 0
                    async for message in app.get_chat_history(chat_id, limit=100):
                        count += 1
                    print(f"✅ {group_id} cache'ga yuklandi ({count} xabar)")
                except Exception as e:
                    print(f"⚠️ Cache yuklash xatolik {group_id}: {e}")

        except Exception as e:
            print(f"⚠️  Guruhni yuklab bo'lmadi: {group_id} - {e}")

    fast_count = len(source_groups_cache["fast"])
    normal_count = len(source_groups_cache["normal"])
    print(f"📦 Cache: {fast_count} ta fast, {normal_count} ta normal guruh")


async def handle_fast_message(message, chat_id, chat_username, matched_keyword, user_identifier=None):
    """
    ⚡ FAST guruhlar uchun - FAQAT RAW MESSAGE
    user_identifier = username yoki telefon raqami
    """
    state = load_state()
    buffer_group = state.get("buffer_group", "")
    target_groups = state.get("target_groups", [])

    # ⚡ DARHOL BUFFER GURUHGA YUBORISH
    if buffer_group:
        try:
            # Buffer ID ni olish
            if buffer_group.lstrip('-').isdigit():
                buffer_id = int(buffer_group)
            elif buffer_group.startswith('https://t.me/+') or buffer_group.startswith('https://t.me/joinchat/'):
                buffer_id = buffer_group
            else:
                buffer_id = buffer_group

            # TEZKOR yuborish
            message_text = message.message or "[Media/Sticker/File]"

            # User identifier formatini yaratish
            if user_identifier:
                if user_identifier.startswith('+'):
                    # Telefon raqami
                    user_display = f"📞 {user_identifier}"
                elif user_identifier.startswith('@'):
                    # Username
                    user_display = user_identifier
                else:
                    # Boshqa format
                    user_display = f"@{user_identifier}"
            else:
                user_display = "❌ Topilmadi"

            buffer_caption = (
                f"💬 <b>Kontakt:</b> {user_display}\n\n"
                f"📝 <b>Xabar:</b>\n{message_text}"
            )

            await app.send_message(
                chat_id=buffer_id,
                text=buffer_caption,
                disable_web_page_preview=True
            )
            print(f"⚡ FAST → buffer: {user_display}")

        except Exception as e:
            print(f"❌ Buffer xatolik: {e}")

    # Target guruhlarga yuborish
    if target_groups:
        asyncio.create_task(
            send_to_targets_fast(message, chat_id, chat_username, matched_keyword, target_groups, user_identifier)
        )


async def send_to_targets_fast(message, chat_id, chat_username, matched_keyword, target_groups, user_identifier=None):
    """
    Target guruhlarga yuborish - FAST mode uchun
    """
    try:
        # RAW ma'lumotlar
        user_id = message.from_id.user_id if hasattr(message.from_id, 'user_id') else None
        message_text = message.message or "[Media/Sticker/File]"
        timestamp = datetime.fromtimestamp(message.date).strftime('%d.%m.%Y %H:%M')

        # Link yaratish
        if chat_username:
            message_link = f"https://t.me/{chat_username}/{message.id}"
        else:
            # Private group uchun
            pure_id = str(chat_id).removeprefix("-100")
            message_link = f"https://t.me/c/{pure_id}/{message.id}"

        # User identifier formatini yaratish
        if user_identifier:
            if user_identifier.startswith('+'):
                user_display = f"📞 {user_identifier}"
            elif user_identifier.startswith('@'):
                user_display = user_identifier
            else:
                user_display = f"@{user_identifier}"
        else:
            user_display = "❌ Topilmadi"

        # Format
        caption = (
            f"⚡ <b>FAST Zakaz!</b>\n\n"
            f"🔑 <b>Kalit so'z:</b> {matched_keyword}\n"
            f"📅 <b>Sana:</b> {timestamp}\n"
            f"📍 <b>Guruh:</b> {chat_username or chat_id}\n"
            f"🔗 <b>Link:</b> <a href='{message_link}'>Ko'rish</a>\n"
            f"💬 <b>Kontakt:</b> {user_display}\n"
            f"🆔 <b>User ID:</b> <code>{user_id}</code>\n\n"
            f"💬 <b>Xabar:</b>\n{message_text}"
        )

        # Target guruhlarga yuborish
        for target in target_groups:
            try:
                target_id = int(target) if isinstance(target, str) and target.lstrip('-').isdigit() else target

                await app.send_message(
                    chat_id=target_id,
                    text=caption,
                    disable_web_page_preview=True
                )
                print(f"✅ Target → {target}")

            except Exception as e:
                print(f"❌ Target xatolik {target}: {e}")

    except Exception as e:
        print(f"❌ send_to_targets_fast xatolik: {e}")


async def handle_normal_message(message, chat_id, chat_username, matched_keyword):
    """
    📝 NORMAL guruhlar uchun - to'liq ma'lumot bilan
    """
    state = load_state()
    target_groups = state.get("target_groups", [])

    await format_and_send_to_targets(message, chat_id, chat_username, matched_keyword, target_groups, is_fast=False)


async def format_and_send_to_targets(message, chat_id, chat_username, matched_keyword, target_groups, is_fast=False):
    """Xabarni formatlab target guruhlarga yuborish"""
    try:
        # User ID ni darhol olish (message dan)
        user_id = message.from_id.user_id if hasattr(message.from_id, 'user_id') else None

        # Foydalanuvchi ma'lumotlarini olishga harakat (sekinroq)
        user_info = await get_sender_details(chat_id, user_id) if user_id else None

        if user_info and user_info.get('user_id'):
            # To'liq ma'lumot olingan
            sender_name = user_info['name'] or "Noma'lum"
            sender_username = user_info['username'] or "❌ Yo'q"
            sender_phone = user_info['phone'] or "❌ Yo'q"
            user_id = user_info['user_id']
        else:
            # Xabar o'chirilgan - faqat user_id bor
            sender_name = "❌ Xabar o'chirilgan"
            sender_username = "❌ Yo'q"
            sender_phone = "❌ Yo'q"

        timestamp = datetime.fromtimestamp(message.date).strftime('%d.%m.%Y %H:%M')

        # Link yaratish
        if chat_username:
            message_link = f"https://t.me/{chat_username}/{message.id}"
        else:
            pure_id = str(chat_id).removeprefix("-100")
            message_link = f"https://t.me/c/{pure_id}/{message.id}"

        # Xabar matni
        message_text = message.message or "[Media/Sticker/File]"

        # Format
        speed_emoji = "⚡" if is_fast else "📝"
        caption = (
            f"{speed_emoji} <b>Yangi zakaz!</b>\n\n"
            f"🔑 <b>Kalit so'z:</b> {matched_keyword}\n"
            f"📅 <b>Sana:</b> {timestamp}\n"
            f"📍 <b>Guruh:</b> {chat_username or 'Private'}\n"
            f"🔗 <b>Link:</b> <a href='{message_link}'>Ko'rish</a>\n\n"
            f"👤 <b>Yuboruvchi:</b> {sender_name}\n"
            f"💬 <b>Username:</b> {sender_username}\n"
            f"📞 <b>Telefon:</b> {sender_phone}\n"
            f"🆔 <b>User ID:</b> <code>{user_id}</code>\n\n"
            f"💬 <b>Xabar:</b>\n{message_text}"
        )

        # Target guruhlarga yuborish
        for target in target_groups:
            try:
                target_id = int(target) if isinstance(target, str) and target.lstrip('-').isdigit() else target

                await app.send_message(
                    chat_id=target_id,
                    text=caption,
                    disable_web_page_preview=True
                )
                print(f"✅ Yuborildi → {target}")

            except Exception as e:
                print(f"❌ Target xatolik {target}: {e}")

    except Exception as e:
        print(f"❌ Format xatolik: {e}")


async def setup_raw_handler():
    """
    ⚡ RAW EVENT HANDLER - MAKSIMAL TEZLIK (Pyrogram)
    UpdateNewMessage va UpdateNewChannelMessage ni bevosita ushlash
    """
    global handler_registered

    if handler_registered:
        return

    print("⚡ Raw handler sozlanmoqda...")
    await update_source_groups()

    @app.on_raw_update()
    async def raw_message_handler(client, update, users, chats):
        """RAW xabarlarni real-time ushlash - PYROGRAM"""
        try:
            # Faqat yangi xabarlar
            if not isinstance(update, (UpdateNewMessage, UpdateNewChannelMessage)):
                return

            # Message obyektini olish
            message = None
            if hasattr(update, 'message') and isinstance(update.message, Message):
                message = update.message
            else:
                return

            # Xabar matni yo'q bo'lsa, o'tkazib yuborish
            if not message.message:
                return

            # Chat ID ni aniqlash
            peer = message.peer_id
            if isinstance(peer, PeerChannel):
                chat_id = peer.channel_id
                # Pyrogram negativ ID ishlatadi
                if chat_id > 0:
                    chat_id = int(f"-100{chat_id}")
            else:
                return

            # Cache'dan tekshirish - JUDA TEZ
            group_type = None

            # Cache'da pozitiv ID va negativ ID ikkalasini ham tekshirish
            positive_id = abs(chat_id)
            negative_id = -abs(chat_id)

            if positive_id in source_groups_cache["fast"] or negative_id in source_groups_cache["fast"]:
                group_type = "fast"
                chat_id = positive_id if positive_id in source_groups_cache["fast"] else negative_id
            elif positive_id in source_groups_cache["normal"] or negative_id in source_groups_cache["normal"]:
                group_type = "normal"
                chat_id = positive_id if positive_id in source_groups_cache["normal"] else negative_id
            else:
                return  # Bu guruh bizning ro'yxatimizda yo'q

            # Kalit so'zni tekshirish
            state = load_state()
            keywords = [kw.lower().strip() for kw in state.get("keywords", [])]

            if not keywords:
                return

            matched_keyword = check_keyword_match(message.message, keywords)
            if not matched_keyword:
                return

            # ⚠️ BLACKWORD TEKSHIRUVI
            blackwords = [bw.lower().strip() for bw in state.get("blackwords", [])]
            if blackwords:
                found_blackword = check_blackword(message.message, blackwords)
                if found_blackword:
                    print(f"🚫 Blackword topildi: '{found_blackword}' - xabar o'tkazib yuborildi")
                    return

            print(f"🎯 Kalit so'z topildi: '{matched_keyword}' [{group_type.upper()}]")

            # Chat username ni olish
            chat_username = source_groups_cache[group_type][chat_id].get("username")

            # ⚡ USERNAME yoki TELEFON ni tezkor topish
            user_identifier = None

            # 1. Telefon raqami (entities'dan - eng ishonchli)
            if hasattr(message, 'entities') and message.entities:
                for entity in message.entities:
                    if isinstance(entity, MessageEntityPhone):
                        phone_start = entity.offset
                        phone_length = entity.length
                        user_identifier = message.message[phone_start:phone_start + phone_length]
                        break

            # 2. post_author (ba'zi guruhlar)
            if not user_identifier and hasattr(message, 'post_author') and message.post_author:
                user_identifier = message.post_author

            # 3. from_id dan username olishga harakat
            if not user_identifier and hasattr(message, 'from_id'):
                try:
                    # users dict'dan topish (Pyrogram raw update'da users keladi)
                    if hasattr(message.from_id, 'user_id') and message.from_id.user_id in users:
                        user = users[message.from_id.user_id]
                        if hasattr(user, 'username') and user.username:
                            user_identifier = user.username
                except:
                    pass

            # Guruh tipiga qarab ishlov berish
            if group_type == "fast":
                # ⚡ FAST: DARHOL buffer ga yuborish
                asyncio.create_task(handle_fast_message(message, chat_id, chat_username, matched_keyword, user_identifier))
            else:
                # 📝 NORMAL: oddiy jarayon
                asyncio.create_task(handle_normal_message(message, chat_id, chat_username, matched_keyword))

        except Exception as e:
            print(f"❌ Raw handler xatolik: {e}")

    handler_registered = True
    print("✅ Raw handler yoqildi (Pyrogram - maksimal tezlik)")


async def run_userbot():
    """Userbotni ishga tushirish - PYROGRAM"""
    print("🚀 UserBot ishga tushmoqda (Pyrogram)...")

    await app.start()
    print("✅ UserBot ulandi (Pyrogram)")

    # Raw handler'ni sozlash
    await setup_raw_handler()

    # Har 30 daqiqada yangilash
    while True:
        await asyncio.sleep(1800)  # 30 daqiqa
        try:
            await update_source_groups()
        except Exception as e:
            print(f"❌ Yangilash xatolik: {e}")
