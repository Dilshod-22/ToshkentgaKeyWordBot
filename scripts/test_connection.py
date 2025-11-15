#!/usr/bin/env python3
# test_connection.py - Telegram API ni tekshirish

from telethon import TelegramClient
from telethon.errors import ApiIdInvalidError, PhoneNumberInvalidError
import asyncio
import sys

# config.py dan import qilish
try:
    from config import api_id, api_hash
    print(f"✅ Config yuklandi")
    print(f"   api_id: {api_id}")
    print(f"   api_hash: {api_hash[:8]}...")
except ImportError:
    print("❌ config.py topilmadi!")
    sys.exit(1)

async def test_connection():
    """Telegram API ga ulanishni sinash"""
    
    print("\n" + "="*50)
    print("🧪 TELEGRAM API TESTI")
    print("="*50 + "\n")
    
    # Session nomi (test uchun)
    session_name = "test_session"
    
    try:
        # Client yaratish
        client = TelegramClient(session_name, api_id, api_hash)
        
        print("📡 Telegram serverga ulanmoqda...")
        
        # Ulanish
        await client.connect()
        
        if not await client.is_user_authorized():
            print("✅ Server bilan aloqa o'rnatildi")
            print("\n📞 Telefon raqamingizni kiriting:")
            print("   Format: +998XXXXXXXXX yoki 998XXXXXXXXX")
            
            phone = input("   > ").strip()
            
            # Telefon formatini tozalash
            if not phone.startswith('+'):
                if not phone.startswith('998'):
                    phone = '+998' + phone
                else:
                    phone = '+' + phone
            
            print(f"\n📨 Kod yuborilmoqda: {phone}")
            
            try:
                # Kod so'rash
                await client.send_code_request(phone)
                
                print("\n✅ KOD YUBORILDI!")
                print("   Telegram ilovasini tekshiring:")
                print("   1. Telegram Desktop/Mobile ni oching")
                print("   2. 'Telegram' nomli rasmiy chatni toping")
                print("   3. Login kodini ko'ring\n")
                
                code = input("🔑 Kodni kiriting: ").strip()
                
                # Kirish
                await client.sign_in(phone, code)
                
                print("\n🎉 MUVAFFAQIYATLI!")
                print("   API ma'lumotlar to'g'ri")
                print("   Endi main.py ni ishga tushirishingiz mumkin\n")
                
            except PhoneNumberInvalidError:
                print("\n❌ TELEFON RAQAM XATO!")
                print("   To'g'ri format: +998941234567")
                
            except Exception as e:
                print(f"\n❌ XATOLIK: {e}")
                print("   Mumkin sabablari:")
                print("   - api_id yoki api_hash noto'g'ri")
                print("   - Telefon raqam noto'g'ri")
                print("   - Internet aloqasi yo'q")
        
        else:
            me = await client.get_me()
            print(f"\n✅ Allaqachon tizimga kirgan!")
            print(f"   Foydalanuvchi: {me.first_name}")
            print(f"   Telefon: {me.phone}")
            print(f"   ID: {me.id}\n")
        
        await client.disconnect()
        
    except ApiIdInvalidError:
        print("\n❌ API_ID yoki API_HASH NOTO'G'RI!")
        print("   https://my.telegram.org ga o'ting va tekshiring")
        
    except ConnectionError:
        print("\n❌ INTERNETGA ULANIB BO'LMADI!")
        print("   Internet aloqangizni tekshiring")
        
    except Exception as e:
        print(f"\n❌ KUTILMAGAN XATOLIK: {e}")
    
    finally:
        # Test session faylini o'chirish
        import os
        try:
            if os.path.exists(f"{session_name}.session"):
                os.remove(f"{session_name}.session")
                print("🧹 Test fayl tozalandi")
        except:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(test_connection())
    except KeyboardInterrupt:
        print("\n\n⛔ Test to'xtatildi")