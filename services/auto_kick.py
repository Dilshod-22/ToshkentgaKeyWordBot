"""
Auto Kick System - Avtomatik guruhdan chiqarish
3 kundan keyin owner va adminlardan boshqa barchasini chiqaradi

Ishlatish:
1. Bir marta ishga tushirish: python auto_kick.py
2. Har kuni avtomatik: cron yoki task scheduler bilan sozlash
"""

import asyncio
from telethon import TelegramClient
from telethon.tl.functions.channels import GetParticipantsRequest, EditBannedRequest
from telethon.tl.types import ChannelParticipantsSearch, ChatBannedRights
from datetime import datetime, timedelta
import json
from pathlib import Path

# API credentials (userbot.py dan)
api_id = 35590072
api_hash = "48e5dad8bef68a54aac5b2ce0702b82c"
session_path = "userbot_session"

# Sozlamalar
TARGET_GROUP_ID = "YOUR_TARGET_GROUP_ID"  # -100 bilan
ADMIN_IDS = [7106025530, 5129045986]  # Saqlanishi kerak bo'lgan adminlar
FREE_TRIAL_DAYS = 3  # Bepul sinov kunlari

# Ma'lumotlar fayllari
APPROVED_USERS_FILE = "approved_users.json"
KICK_LOG_FILE = "kick_log.json"


def load_json(file_path: str) -> dict:
    """JSON fayldan yuklash"""
    if not Path(file_path).exists():
        return {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}


def save_json(file_path: str, data: dict):
    """JSON faylga saqlash"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def kick_expired_users():
    """
    Muddati tugagan foydalanuvchilarni guruhdan chiqarish
    """
    client = TelegramClient(session_path, api_id, api_hash)

    try:
        await client.start()
        print("✅ Client ulandi")

        # Guruhni olish
        try:
            group = await client.get_entity(TARGET_GROUP_ID)
            print(f"📍 Guruh: {group.title}")
        except Exception as e:
            print(f"❌ Guruhni topib bo'lmadi: {e}")
            return

        # Tasdiqlangan foydalanuvchilarni yuklash
        approved_users = load_json(APPROVED_USERS_FILE)
        approved_user_ids = set(int(uid) for uid in approved_users.keys())

        # Guruh a'zolarini olish
        all_participants = []
        offset = 0
        limit = 100

        print("📥 Guruh a'zolarini olish...")

        while True:
            participants = await client(GetParticipantsRequest(
                channel=group,
                filter=ChannelParticipantsSearch(''),
                offset=offset,
                limit=limit,
                hash=0
            ))

            if not participants.users:
                break

            all_participants.extend(participants.users)
            offset += len(participants.users)

            if len(participants.users) < limit:
                break

        print(f"👥 Jami a'zolar: {len(all_participants)} ta")

        # Chiqarish uchun ro'yxat
        kicked_users = []
        skipped_users = []

        now = datetime.now()
        trial_cutoff = now - timedelta(days=FREE_TRIAL_DAYS)

        for user in all_participants:
            user_id = user.id

            # Adminlar va botlarni o'tkazib yuborish
            if user_id in ADMIN_IDS or user.bot:
                skipped_users.append({
                    "user_id": user_id,
                    "username": getattr(user, 'username', None),
                    "reason": "admin" if user_id in ADMIN_IDS else "bot"
                })
                continue

            # To'lovli foydalanuvchilarni tekshirish
            if user_id in approved_user_ids:
                user_data = approved_users[str(user_id)]

                # Agar obuna muddati belgilangan bo'lsa
                if user_data.get('expires_at'):
                    expires_at = datetime.fromisoformat(user_data['expires_at'])

                    if expires_at > now:
                        # Hali muddati tugamagan
                        skipped_users.append({
                            "user_id": user_id,
                            "username": user_data.get('username'),
                            "reason": "active_subscription",
                            "expires_at": user_data['expires_at']
                        })
                        continue

                # Muddati tugagan yoki muddatsiz (eski foydalanuvchi)
                else:
                    # Bepul sinov muddatini tekshirish
                    approved_at = datetime.fromisoformat(user_data['approved_at'])
                    if approved_at > trial_cutoff:
                        # Hali 3 kun o'tmagan
                        skipped_users.append({
                            "user_id": user_id,
                            "username": user_data.get('username'),
                            "reason": "trial_active",
                            "approved_at": user_data['approved_at']
                        })
                        continue

            # Guruhdan chiqarish
            try:
                # Ban rights (kick qilish uchun)
                await client(EditBannedRequest(
                    channel=group,
                    participant=user,
                    banned_rights=ChatBannedRights(
                        until_date=None,
                        view_messages=True  # Guruhni ko'ra olmaydi
                    )
                ))

                kicked_users.append({
                    "user_id": user_id,
                    "username": getattr(user, 'username', None),
                    "full_name": getattr(user, 'first_name', '') + ' ' + getattr(user, 'last_name', ''),
                    "kicked_at": now.isoformat(),
                    "reason": "trial_expired" if user_id not in approved_user_ids else "subscription_expired"
                })

                print(f"❌ Chiqarildi: {user.first_name} (@{getattr(user, 'username', 'None')})")

                # Rate limiting oldini olish
                await asyncio.sleep(1)

            except Exception as e:
                print(f"⚠️ {user.first_name} ni chiqarishda xatolik: {e}")

        # Natijalarni saqlash
        kick_log = load_json(KICK_LOG_FILE)

        log_entry = {
            "timestamp": now.isoformat(),
            "total_members": len(all_participants),
            "kicked_count": len(kicked_users),
            "skipped_count": len(skipped_users),
            "kicked_users": kicked_users,
            "skipped_users": skipped_users
        }

        # Log ID
        log_id = f"kick_{int(now.timestamp())}"
        kick_log[log_id] = log_entry
        save_json(KICK_LOG_FILE, kick_log)

        # Natija
        print("\n" + "="*50)
        print("📊 NATIJA:")
        print(f"👥 Jami a'zolar: {len(all_participants)}")
        print(f"❌ Chiqarildi: {len(kicked_users)}")
        print(f"✅ Qoldirildi: {len(skipped_users)}")
        print(f"📄 Log saqlandi: {log_id}")
        print("="*50)

    except Exception as e:
        print(f"❌ Xatolik: {e}")

    finally:
        await client.disconnect()


async def get_group_stats():
    """
    Guruh statistikasini olish (chiqarmasdan faqat ko'rish)
    """
    client = TelegramClient(session_path, api_id, api_hash)

    try:
        await client.start()
        print("✅ Client ulandi")

        group = await client.get_entity(TARGET_GROUP_ID)
        print(f"📍 Guruh: {group.title}")

        # Tasdiqlangan foydalanuvchilar
        approved_users = load_json(APPROVED_USERS_FILE)
        approved_user_ids = set(int(uid) for uid in approved_users.keys())

        # Guruh a'zolari
        all_participants = []
        offset = 0

        while True:
            participants = await client(GetParticipantsRequest(
                channel=group,
                filter=ChannelParticipantsSearch(''),
                offset=offset,
                limit=100,
                hash=0
            ))

            if not participants.users:
                break

            all_participants.extend(participants.users)
            offset += len(participants.users)

            if len(participants.users) < 100:
                break

        # Statistika
        now = datetime.now()
        trial_cutoff = now - timedelta(days=FREE_TRIAL_DAYS)

        stats = {
            "total": len(all_participants),
            "admins": 0,
            "bots": 0,
            "trial_active": 0,
            "trial_expired": 0,
            "subscription_active": 0,
            "subscription_expired": 0,
            "not_registered": 0
        }

        for user in all_participants:
            user_id = user.id

            if user_id in ADMIN_IDS:
                stats["admins"] += 1
            elif user.bot:
                stats["bots"] += 1
            elif user_id in approved_user_ids:
                user_data = approved_users[str(user_id)]

                if user_data.get('expires_at'):
                    expires_at = datetime.fromisoformat(user_data['expires_at'])
                    if expires_at > now:
                        stats["subscription_active"] += 1
                    else:
                        stats["subscription_expired"] += 1
                else:
                    approved_at = datetime.fromisoformat(user_data['approved_at'])
                    if approved_at > trial_cutoff:
                        stats["trial_active"] += 1
                    else:
                        stats["trial_expired"] += 1
            else:
                stats["not_registered"] += 1

        # Natija
        print("\n" + "="*50)
        print("📊 GURUH STATISTIKASI")
        print("="*50)
        print(f"👥 Jami a'zolar: {stats['total']}")
        print(f"👨‍💼 Adminlar: {stats['admins']}")
        print(f"🤖 Botlar: {stats['bots']}")
        print(f"✅ Faol trial: {stats['trial_active']}")
        print(f"⏰ Tugagan trial: {stats['trial_expired']}")
        print(f"💎 Faol obuna: {stats['subscription_active']}")
        print(f"❌ Tugagan obuna: {stats['subscription_expired']}")
        print(f"❓ Ro'yxatdan o'tmagan: {stats['not_registered']}")
        print("="*50)

        # Chiqarilishi keraklar
        to_kick = stats['trial_expired'] + stats['subscription_expired'] + stats['not_registered']
        print(f"\n⚠️ Chiqarilishi kerak: {to_kick} ta foydalanuvchi")

    except Exception as e:
        print(f"❌ Xatolik: {e}")

    finally:
        await client.disconnect()


if __name__ == "__main__":
    print("🔧 Auto Kick System\n")
    print("1. Statistikani ko'rish (chiqarmasdan)")
    print("2. Muddati tugaganlarni chiqarish")
    print()

    choice = input("Tanlang (1/2): ").strip()

    if choice == "1":
        print("\n📊 Statistika olinmoqda...\n")
        asyncio.run(get_group_stats())
    elif choice == "2":
        confirm = input("\n⚠️ Rostdan ham chiqarishni xohlaysizmi? (ha/yo'q): ").strip().lower()

        if confirm in ['ha', 'h', 'yes', 'y']:
            print("\n❌ Chiqarish boshlanmoqda...\n")
            asyncio.run(kick_expired_users())
        else:
            print("❌ Bekor qilindi")
    else:
        print("❌ Noto'g'ri tanlov")
