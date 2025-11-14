import re
import asyncio
from datetime import datetime
from pyrogram import Client, filters
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

    print(f"🔧 Rebuild cache: {len(source_groups)} ta configured guruh")

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
            print(f"   💾 Yuklanmoqda: {group_id} ({group_type})...")

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
            print(f"   ✅ Yuklandi: {group_id} → chat_id={chat_id}")

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


async def handle_fast_message_v2(message, chat_id, chat_username, matched_keyword, user_identifier=None):
    """
    ⚡ FAST guruhlar uchun - Pyrogram Message obyekti
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
            message_text = message.text or message.caption or "[Media/Sticker/File]"

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
            send_to_targets_fast_v2(message, chat_id, chat_username, matched_keyword, target_groups, user_identifier)
        )


async def send_to_targets_fast_v2(message, chat_id, chat_username, matched_keyword, target_groups, user_identifier=None):
    """
    Target guruhlarga yuborish - FAST mode uchun (Pyrogram Message)
    """
    try:
        # Ma'lumotlar
        user_id = message.from_user.id if message.from_user else None
        message_text = message.text or message.caption or "[Media/Sticker/File]"
        timestamp = message.date.strftime('%d.%m.%Y %H:%M')

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
        print(f"❌ send_to_targets_fast_v2 xatolik: {e}")


async def handle_normal_message_v2(message, chat_id, chat_username, matched_keyword):
    """
    📝 NORMAL guruhlar uchun - to'liq ma'lumot bilan (Pyrogram Message)
    """
    state = load_state()
    target_groups = state.get("target_groups", [])

    await format_and_send_to_targets_v2(message, chat_id, chat_username, matched_keyword, target_groups, is_fast=False)


async def format_and_send_to_targets_v2(message, chat_id, chat_username, matched_keyword, target_groups, is_fast=False):
    """Xabarni formatlab target guruhlarga yuborish (Pyrogram Message)"""
    try:
        # User ID ni darhol olish (message dan)
        user_id = message.from_user.id if message.from_user else None

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

        timestamp = message.date.strftime('%d.%m.%Y %H:%M')

        # Link yaratish
        if chat_username:
            message_link = f"https://t.me/{chat_username}/{message.id}"
        else:
            pure_id = str(chat_id).removeprefix("-100")
            message_link = f"https://t.me/c/{pure_id}/{message.id}"

        # Xabar matni
        message_text = message.text or message.caption or "[Media/Sticker/File]"

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


# ⚡⚡⚡ MUHIM: Message handler MODULE DARAJASIDA e'lon qilingan
# Pyrogram oddiy message handler'larni raw'dan ko'ra yaxshiroq qo'llab-quvvatlaydi
@app.on_message()
async def message_handler(client, message):
    """
    ⚡ Barcha xabarlarni ushlash - PYROGRAM
    Bu handler module darajasida, shuning uchun app.start() avtomatik registratsiya qiladi
    """
    try:
        # DEBUG: Xabar keldi
        print(f"🔵 Xabar keldi!")

        # Xabar matni yo'q bo'lsa, o'tkazib yuborish
        if not message.text:
            print(f"⚠️ Xabar matni yo'q (media/sticker/etc)")
            return

        print(f"📝 Xabar matni: {message.text[:50]}...")

        # Chat ID ni olish
        chat_id = message.chat.id
        print(f"📍 Chat ID: {chat_id}")

        # Cache'dan tekshirish - JUDA TEZ
        group_type = None

        # Cache'da pozitiv ID va negativ ID ikkalasini ham tekshirish
        positive_id = abs(chat_id)
        negative_id = -abs(chat_id)

        print(f"🔍 Cache tekshiruv: positive={positive_id}, negative={negative_id}")
        print(f"   FAST cache: {list(source_groups_cache['fast'].keys())}")
        print(f"   NORMAL cache: {list(source_groups_cache['normal'].keys())}")

        if positive_id in source_groups_cache["fast"] or negative_id in source_groups_cache["fast"]:
            group_type = "fast"
            chat_id = positive_id if positive_id in source_groups_cache["fast"] else negative_id
            print(f"✅ FAST guruh topildi! chat_id={chat_id}")
        elif positive_id in source_groups_cache["normal"] or negative_id in source_groups_cache["normal"]:
            group_type = "normal"
            chat_id = positive_id if positive_id in source_groups_cache["normal"] else negative_id
            print(f"✅ NORMAL guruh topildi! chat_id={chat_id}")
        else:
            print(f"❌ Guruh cache'da yo'q. Skip.")
            return  # Bu guruh bizning ro'yxatimizda yo'q

        # Kalit so'zni tekshirish
        state = load_state()
        keywords = [kw.lower().strip() for kw in state.get("keywords", [])]

        print(f"🔑 Keywords soni: {len(keywords)}")

        if not keywords:
            print(f"⚠️ Keywords yo'q, skip")
            return

        matched_keyword = check_keyword_match(message.text, keywords)
        if not matched_keyword:
            print(f"❌ Keyword match yo'q")
            return

        print(f"🎯 Keyword match: '{matched_keyword}'")

        # ⚠️ BLACKWORD TEKSHIRUVI
        blackwords = [bw.lower().strip() for bw in state.get("blackwords", [])]
        if blackwords:
            print(f"🚫 Blackwords tekshirilmoqda ({len(blackwords)} ta)...")
            found_blackword = check_blackword(message.text, blackwords)
            if found_blackword:
                print(f"🚫 Blackword topildi: '{found_blackword}' - xabar o'tkazib yuborildi")
                return

        print(f"✅ YUBORISH: '{matched_keyword}' [{group_type.upper()}]")

        # Chat username ni olish
        chat_username = source_groups_cache[group_type][chat_id].get("username")
        print(f"📢 Chat: {chat_username or chat_id}")

        # ⚡ USERNAME yoki TELEFON ni tezkor topish
        user_identifier = None

        # 1. Telefon raqami (entities'dan - eng ishonchli)
        if message.entities:
            for entity in message.entities:
                if entity.type.value == "phone_number":
                    phone_start = entity.offset
                    phone_length = entity.length
                    user_identifier = message.text[phone_start:phone_start + phone_length]
                    print(f"📞 Telefon topildi: {user_identifier}")
                    break

        # 2. post_author (ba'zi guruhlar)
        if not user_identifier and hasattr(message, 'author_signature') and message.author_signature:
            user_identifier = message.author_signature
            print(f"✍️ Author signature: {user_identifier}")

        # 3. from_user dan username olish
        if not user_identifier and message.from_user:
            if message.from_user.username:
                user_identifier = f"@{message.from_user.username}"
                print(f"👤 Username topildi: {user_identifier}")
            elif message.from_user.phone_number:
                user_identifier = message.from_user.phone_number
                print(f"📞 Phone topildi: {user_identifier}")

        if not user_identifier:
            print(f"⚠️ User identifier topilmadi")

        # Guruh tipiga qarab ishlov berish
        if group_type == "fast":
            # ⚡ FAST: DARHOL buffer ga yuborish
            print(f"🚀 FAST mode: buffer'ga yuborish...")
            await handle_fast_message_v2(message, chat_id, chat_username, matched_keyword, user_identifier)
        else:
            # 📝 NORMAL: oddiy jarayon
            print(f"📝 NORMAL mode: formatlab yuborish...")
            await handle_normal_message_v2(message, chat_id, chat_username, matched_keyword)

    except Exception as e:
        print(f"❌ Message handler xatolik: {e}")
        import traceback
        traceback.print_exc()


async def setup_cache():
    """
    Cache'ni yuklab, handler tayyor holatga keltirish
    Handler o'zi module darajasida e'lon qilingan (@app.on_raw_update decorator bilan)
    """
    print("⚡ Cache sozlanmoqda...")
    await update_source_groups()
    print("✅ Handler tayyor (Pyrogram - maksimal tezlik)")


async def run_userbot():
    """Userbotni ishga tushirish - PYROGRAM"""
    print("🚀 UserBot ishga tushmoqda (Pyrogram)...")

    # MUHIM: app.start() dan OLDIN cache'ni yuklash
    await app.start()
    print("✅ UserBot ulandi (Pyrogram)")

    # Cache'ni yuklash
    await setup_cache()

    # Har 30 daqiqada yangilash
    while True:
        await asyncio.sleep(1800)  # 30 daqiqa
        try:
            await update_source_groups()
        except Exception as e:
            print(f"❌ Yangilash xatolik: {e}")
