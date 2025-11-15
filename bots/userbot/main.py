import re
import asyncio
from datetime import datetime
from telethon import TelegramClient, events
from telethon.tl.types import (
    UpdateNewMessage,
    UpdateNewChannelMessage,
    PeerChannel,
    Message,
    MessageEntityPhone
)
from core.storage import save_state, load_state
from core.config import USERBOT_API_ID, USERBOT_API_HASH, session_path

# TEZLIK UCHUN: uvloop event loop (agar mavjud bo'lsa)
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    print("[OK] uvloop yoqildi (maksimal tezlik)")
except ImportError:
    print("[INFO] uvloop topilmadi, standart asyncio ishlatilmoqda")

# Telethon client
client = TelegramClient(session_path, USERBOT_API_ID, USERBOT_API_HASH)
handler_registered = False

# [FAST] CACHE: Tezlik uchun source guruhlarni xotirada saqlash
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


def get_quick_user_info(message):
    """
    [FAST] TEZKOR user ma'lumotlarini olish - faqat message obyektidan
    ASYNC emas - xabar o'chib ketgunga qadar tezkor ishlaydi
    """
    try:
        # User ID
        user_id = message.sender_id
        
        # Username ni topishga harakat (turli maydonlardan)
        username = None
        
        # 1. message.from_id dan (agar mavjud bo'lsa)
        if hasattr(message, 'from_id') and hasattr(message.from_id, 'user_id'):
            user_id = message.from_id.user_id
        
        # 2. post_author maydoni (ba'zi guruhlar uchun)
        if hasattr(message, 'post_author') and message.post_author:
            username = message.post_author
        
        user_info = {
            "name": "Noma'lum",
            "username": username,
            "phone": None,
            "user_id": user_id
        }
        
        return user_info
    except Exception as e:
        print(f"[OGOHLANTIRISH]  Quick user info xatolik: {e}")
        return None


async def get_sender_details(message):
    """
    Sender ma'lumotlarini olish (async) - faqat NORMAL guruhlar uchun
    Bu sekinroq, lekin to'liq ma'lumot beradi
    """
    try:
        sender = await message.get_sender()

        # Agar sender None bo'lsa (xabar o'chirilgan)
        if sender is None:
            return None

        # Username va telefon
        username = getattr(sender, 'username', None)
        phone = getattr(sender, 'phone', None)

        # Ism
        first_name = getattr(sender, 'first_name', '')
        last_name = getattr(sender, 'last_name', '')
        full_name = f"{first_name} {last_name}".strip() or "Noma'lum"

        user_info = {
            "name": full_name,
            "username": f"@{username}" if username else None,
            "phone": f"+{phone}" if phone else None,
            "user_id": sender.id
        }

        return user_info
    except Exception as e:
        print(f"[OGOHLANTIRISH]  Sender details xatolik: {e}")
        return None


async def update_source_groups():
    """Source guruhlarni yangilash va cache'ga yuklash"""
    print("[YANGILANMOQDA] Source guruhlar yangilanmoqda...")

    dialogs = await client.get_dialogs()
    state = load_state()

    # Target guruhlarni exclude qilish
    exclude_targets = set(str(t) for t in state.get("target_groups", []))

    # Mavjud source_groups ni o'qish
    configured_sources = state.get("source_groups", [])

    # Yangi struktura
    new_sources = []

    for dialog in dialogs:
        entity = dialog.entity

        # Faqat guruhlar (supergroup/megagroup/gigagroup)
        if not hasattr(entity, 'megagroup') and not getattr(entity, 'gigagroup', False):
            continue

        if getattr(entity, 'broadcast', False):
            continue

        chat_id = str(entity.id)
        username = getattr(entity, "username", None)

        # Target guruhlarda bo'lmasligi kerak
        if chat_id in exclude_targets or f"-100{chat_id}" in exclude_targets:
            continue

        group_key = username.lower() if username else chat_id

        # Configured sources dan type ni olish
        existing_type = "normal"
        for src in configured_sources:
            if isinstance(src, dict):
                if src.get("id") == group_key:
                    existing_type = src.get("type", "normal")
                    break
            elif src == group_key:
                existing_type = "normal"
                break

        new_sources.append({
            "id": group_key,
            "type": existing_type
        })

    # Saqlash
    state["source_groups"] = new_sources
    save_state(state)

    # Cache'ni yangilash
    await rebuild_cache()

    print(f"[OK] {len(new_sources)} ta guruh yangilandi")


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
            # Guruhni olish
            entity = await client.get_entity(group_id)
            chat_id = entity.id
            username = getattr(entity, 'username', None)

            group_info = {
                "id": chat_id,
                "username": username,
                "original_key": group_id
            }

            # Cache'ga qo'shish
            source_groups_cache[group_type][chat_id] = group_info
            
            # [FAST] QOSIMCHA: FAST guruhlar uchun userlarni cache'ga yuklash
            if group_type == "fast":
                try:
                    print(f"[YUKLASH] {group_id} guruhidan userlarni cache'ga yuklash...")
                    # Oxirgi 100 ta xabarni olish (userlar cache'ga tushadi)
                    async for message in client.iter_messages(entity, limit=100):
                        pass  # Faqat iterate qilish - cache'ga tushadigan userlar
                    print(f"[OK] {group_id} cache'ga yuklandi")
                except Exception as e:
                    print(f"[OGOHLANTIRISH] Cache yuklash xatolik {group_id}: {e}")

        except Exception as e:
            print(f"[OGOHLANTIRISH]  Guruhni yuklab bo'lmadi: {group_id} - {e}")

    fast_count = len(source_groups_cache["fast"])
    normal_count = len(source_groups_cache["normal"])
    print(f"[CACHE] Cache: {fast_count} ta fast, {normal_count} ta normal guruh")


async def handle_fast_message(message, chat, matched_keyword, user_identifier=None):
    """
    [FAST] FAST guruhlar uchun - FAQAT RAW MESSAGE
    user_identifier = username yoki telefon raqami
    """
    state = load_state()
    buffer_group = state.get("buffer_group", "")
    target_groups = state.get("target_groups", [])

    # [FAST] DARHOL BUFFER GURUHGA YUBORISH
    if buffer_group:
        try:
            buffer_id = int(buffer_group) if buffer_group.lstrip('-').isdigit() else buffer_group
            
            # TEZKOR yuborish
            message_text = message.message or "[Media/Sticker/File]"
            
            # User identifier formatini yaratish
            if user_identifier:
                if user_identifier.startswith('+'):
                    # Telefon raqami
                    user_display = f"[TEL] {user_identifier}"
                elif user_identifier.startswith('@'):
                    # Username
                    user_display = user_identifier
                else:
                    # Boshqa format
                    user_display = f"@{user_identifier}"
            else:
                user_display = "[X] Topilmadi"
            
            buffer_caption = (
                f"[XABAR] <b>Kontakt:</b> {user_display}\n\n"
                f"[MATN] <b>Xabar:</b>\n{message_text}"
            )
            
            await client.send_message(
                entity=buffer_id,
                message=buffer_caption,
                parse_mode='html',
                link_preview=False
            )
            print(f"[FAST] FAST → buffer: {user_display}")
            
        except Exception as e:
            print(f"[X] Buffer xatolik: {e}")

    # Target guruhlarga yuborish
    if target_groups:
        asyncio.create_task(
            send_to_targets_fast(message, chat, matched_keyword, target_groups, user_identifier)
        )


async def find_and_update_username(sent_msg, message, update, buffer_id):
    """
    ESKI FUNKSIYA - endi ishlatilmaydi
    """
    pass


async def send_to_targets_fast(message, chat, matched_keyword, target_groups, user_identifier=None):
    """
    Target guruhlarga yuborish - FAST mode uchun
    Sodda va chiroyli format
    """
    try:
        # RAW ma'lumotlar
        message_text = message.message or "[Media/Sticker/File]"

        # Guruh ma'lumotlari
        chat_username = getattr(chat, 'username', None)
        chat_title = getattr(chat, 'title', chat_username or 'Noma\'lum')
        chat_id = str(chat.id)

        # Link yaratish
        if chat_username:
            message_link = f"https://t.me/{chat_username}/{message.id}"
        else:
            pure_id = chat_id.removeprefix("-100")
            message_link = f"https://t.me/c/{pure_id}/{message.id}"

        # User identifier formatini yaratish
        if user_identifier:
            if user_identifier.startswith('+'):
                user_display = f"[TEL] {user_identifier}"
            elif user_identifier.startswith('@'):
                user_display = user_identifier
            else:
                user_display = f"@{user_identifier}"
        else:
            user_display = "[X] Topilmadi"

        # [FAST] FAST Format - sodda va chiroyli
        caption = (
            f"[⚡️] <b>FAST Guruh</b>\n\n"
            f"[🔑] <b>Kalit so'z:</b> {matched_keyword}\n"
            f"[📍] <b>Guruh:</b> {chat_title}\n"
            f"[XABAR] <b>Kontakt:</b> {user_display}\n\n"
            f"[💬] <b>Xabar:</b>\n{message_text}\n\n"
            f"[🔗] <a href='{message_link}'>Xabarni ko'rish</a>"
        )
        
        # Target guruhlarga yuborish
        for target in target_groups:
            try:
                target_id = int(target) if isinstance(target, str) and target.lstrip('-').isdigit() else target
                
                await client.send_message(
                    entity=target_id,
                    message=caption,
                    parse_mode='html',
                    link_preview=False
                )
                print(f"[OK] Target → {target}")
                
            except Exception as e:
                print(f"[X] Target xatolik {target}: {e}")
    
    except Exception as e:
        print(f"[X] send_to_targets_fast xatolik: {e}")


async def handle_normal_message(message, chat, matched_keyword):
    """
    [MATN] NORMAL guruhlar uchun - to'liq ma'lumot bilan
    """
    state = load_state()
    target_groups = state.get("target_groups", [])

    await format_and_send_to_targets(message, chat, matched_keyword, target_groups, is_fast=False)


async def format_and_send_to_targets(message, chat, matched_keyword, target_groups, is_fast=False):
    """Xabarni formatlab target guruhlarga yuborish"""
    try:
        # Foydalanuvchi ma'lumotlarini olishga harakat
        user_info = await get_sender_details(message)

        if user_info and user_info.get('user_id'):
            # To'liq ma'lumot olingan
            sender_name = user_info['name'] or "Noma'lum"
            sender_username = user_info['username'] or "[X] Yo'q"
            sender_phone = user_info['phone'] or "[X] Yo'q"
        else:
            # Xabar o'chirilgan yoki sender topilmadi
            sender_name = "[X] Xabar o'chirilgan"
            sender_username = "[X] Yo'q"
            sender_phone = "[X] Yo'q"
        
        timestamp = message.date.strftime('%d.%m.%Y %H:%M')

        # Guruh ma'lumotlari
        chat_username = getattr(chat, 'username', None)
        chat_id = str(chat.id)

        # Link yaratish
        if chat_username:
            message_link = f"https://t.me/{chat_username}/{message.id}"
        else:
            pure_id = chat_id.removeprefix("-100")
            message_link = f"https://t.me/c/{pure_id}/{message.id}"

        # Xabar matni
        message_text = message.message or "[Media/Sticker/File]"

        # Guruh nomi
        chat_title = getattr(chat, 'title', chat_username or 'Noma\'lum')

        # Kontakt ma'lumotini formatlash - eng muhimini ko'rsatish
        if sender_username and sender_username != "[X] Yo'q":
            contact_display = sender_username
        elif sender_phone and sender_phone != "[X] Yo'q":
            contact_display = f"[TEL] {sender_phone}"
        else:
            contact_display = sender_name if sender_name != "[X] Xabar o'chirilgan" else "[X] Topilmadi"

        # Format - sodda va chiroyli
        caption = (
            f"[MATN] <b>Yangi zakaz!</b>\n\n"
            f"[KEY] <b>Kalit so'z:</b> {matched_keyword}\n"
            f"[SANA] <b>Sana:</b> {timestamp}\n"
            f"[GEO] <b>Guruh:</b> {chat_title}\n"
            f"[XABAR] <b>Kontakt:</b> {contact_display}\n\n"
            f"[MATN] <b>Xabar:</b>\n{message_text}\n\n"
            f"[LINK] <a href='{message_link}'>Xabarni ko'rish</a>"
        )

        # Target guruhlarga yuborish
        for target in target_groups:
            try:
                target_id = int(target) if isinstance(target, str) and target.lstrip('-').isdigit() else target

                await client.send_message(
                    entity=target_id,
                    message=caption,
                    parse_mode='html',
                    link_preview=False
                )
                print(f"[OK] Yuborildi → {target}")

            except Exception as e:
                print(f"[X] Target xatolik {target}: {e}")

    except Exception as e:
        print(f"[X] Format xatolik: {e}")


async def setup_raw_handler():
    """
    [FAST] RAW EVENT HANDLER - MAKSIMAL TEZLIK
    UpdateNewMessage va UpdateNewChannelMessage ni bevosita ushlash
    """
    global handler_registered

    if handler_registered:
        return

    print("[FAST] Raw handler sozlanmoqda...")
    await update_source_groups()

    @client.on(events.Raw(types=[UpdateNewMessage, UpdateNewChannelMessage]))
    async def raw_message_handler(update):
        """RAW xabarlarni real-time ushlash"""
        try:
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
            else:
                return

            # Cache'dan tekshirish - JUDA TEZ
            group_type = None

            if chat_id in source_groups_cache["fast"]:
                group_type = "fast"
            elif chat_id in source_groups_cache["normal"]:
                group_type = "normal"
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

            # [OGOHLANTIRISH] BLACKWORD TEKSHIRUVI - agar topilsa, xabarni o'tkazib yuborish
            blackwords = [bw.lower().strip() for bw in state.get("blackwords", [])]
            if blackwords:
                found_blackword = check_blackword(message.message, blackwords)
                if found_blackword:
                    print(f"[STOP] Blackword topildi: '{found_blackword}' - xabar o'tkazib yuborildi")
                    return

            print(f"[TARGET] Kalit so'z topildi: '{matched_keyword}' [{group_type.upper()}]")

            # Chat entitysini olish
            chat = await client.get_entity(chat_id)

            # [FAST] USERNAME yoki TELEFON ni tezkor topish
            user_identifier = None
            
            # 1. Telefon raqami (entities'dan - eng ishonchli)
            if hasattr(message, 'entities') and message.entities:
                from telethon.tl.types import MessageEntityPhone
                for entity in message.entities:
                    if isinstance(entity, MessageEntityPhone):
                        phone_start = entity.offset
                        phone_length = entity.length
                        user_identifier = message.message[phone_start:phone_start + phone_length]
                        break
            
            # 2. post_author (ba'zi guruhlar)
            if not user_identifier and hasattr(message, 'post_author') and message.post_author:
                user_identifier = message.post_author
            
            # 3. Cache'dan username olishga harakat (agar telefon yo'q bo'lsa)
            if not user_identifier:
                try:
                    # Telethon cache'da user bor bo'lsa, tez oladi
                    sender = client._entity_cache.get(message.sender_id)
                    if sender and hasattr(sender, 'username') and sender.username:
                        user_identifier = sender.username
                except:
                    pass  # Cache'da yo'q bo'lsa, o'tkazib yuborish

            # Guruh tipiga qarab ishlov berish
            if group_type == "fast":
                # [FAST] FAST: DARHOL buffer ga yuborish
                asyncio.create_task(handle_fast_message(message, chat, matched_keyword, user_identifier))
            else:
                # [MATN] NORMAL: oddiy jarayon
                asyncio.create_task(handle_normal_message(message, chat, matched_keyword))

        except Exception as e:
            print(f"[X] Raw handler xatolik: {e}")

    handler_registered = True
    print("[OK] Raw handler yoqildi (maksimal tezlik)")


async def run_userbot():
    """Userbotni ishga tushirish"""
    print("[START] UserBot ishga tushmoqda...")

    await client.start()
    print("[OK] UserBot ulandi")

    # Raw handler'ni sozlash
    await setup_raw_handler()

    # Har 30 daqiqada yangilash
    while True:
        await asyncio.sleep(1800)
        try:
            await update_source_groups()
        except Exception as e:
            print(f"[X] Yangilash xatolik: {e}")