#!/usr/bin/env python3
# check_ban.py - Telegram flood ban tekshirish

import asyncio
import time
from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError, 
    PhoneNumberBannedError,
    PhoneNumberInvalidError,
    ApiIdInvalidError
)
from config import api_id, api_hash

async def check_flood_status():
    """Bloklanganlikni tekshirish"""
    
    print("\n" + "="*70)
    print("🔍 TELEGRAM FLOOD BAN TEKSHIRUVI")
    print("="*70 + "\n")
    
    print(f"📋 API ma'lumotlar:")
    print(f"   api_id: {api_id}")
    print(f"   api_hash: {api_hash[:8]}...\n")
    
    # Telefon raqamni so'rash
    print("📞 Tekshirmoqchi bo'lgan telefon raqamingizni kiriting:")
    print("   Format: +998XXXXXXXXX")
    phone = input("   > ").strip()
    
    # Format tuzatish
    if not phone.startswith('+'):
        if not phone.startswith('998'):
            phone = '+998' + phone
        else:
            phone = '+' + phone
    
    print(f"\n{'='*70}")
    print(f"🧪 Tekshirilmoqda: {phone}")
    print(f"{'='*70}\n")
    
    client = TelegramClient("check_ban_test", api_id, api_hash)
    
    try:
        print("1️⃣ Serverga ulanish...")
        await client.connect()
        print("   ✅ Server bilan aloqa o'rnatildi\n")
        
        print("2️⃣ Kod so'rash...")
        start_time = time.time()
        
        try:
            await client.send_code_request(phone)
            end_time = time.time()
            
            print(f"   ✅ KOD YUBORILDI! (Vaqt: {end_time - start_time:.2f}s)")
            print(f"\n{'='*70}")
            print("🎉 SIZ BLOKLANMAGAN!")
            print("="*70)
            print("\n💡 Natija:")
            print("   ✅ Telegram sizni bloklamagan")
            print("   ✅ Kod yuborish ishlayapti")
            print("   ℹ️  Agar kod kelmasa, boshqa sabab bor:\n")
            print("   🔸 Telefon raqam API bilan mos kelmayotgan bo'lishi mumkin")
            print("   🔸 my.telegram.org da boshqa raqam ishlatgan bo'lsangiz kerak")
            print("\n🔧 Qanday tekshirish:")
            print("   1. https://my.telegram.org ga kiring")
            print("   2. Qaysi raqam bilan kirganingizni eslab qoling")
            print("   3. Aynan o'sha raqamni ishlatishga harakat qiling")
            print("="*70 + "\n")
            
            # Kodni kiritish imkoniyati
            choice = input("📝 Kodni kiritib, to'liq login qilasizmi? (ha/yo'q): ").strip().lower()
            
            if choice in ['ha', 'h', 'yes', 'y']:
                code = input("\n🔑 Kodni kiriting: ").strip()
                
                try:
                    await client.sign_in(phone, code)
                    me = await client.get_me()
                    
                    print(f"\n🎉 LOGIN MUVAFFAQIYATLI!")
                    print(f"   👤 Ism: {me.first_name}")
                    print(f"   📞 Telefon: {me.phone}")
                    print(f"   🆔 ID: {me.id}")
                    print(f"\n✅ Bu raqam to'g'ri: {phone}")
                    print(f"✅ Endi main.py ni ishga tushirishingiz mumkin!\n")
                    
                except Exception as e:
                    print(f"\n❌ Login xatolik: {e}")
        
        except FloodWaitError as e:
            wait_seconds = e.seconds
            wait_minutes = wait_seconds // 60
            wait_hours = wait_minutes // 60
            
            print(f"   ⏳ FLOOD WAIT!\n")
            print(f"{'='*70}")
            print("🚫 SIZ VAQTINCHA BLOKLANGANSIZ!")
            print("="*70)
            print(f"\n⏰ Kutish vaqti:")
            
            if wait_hours > 0:
                print(f"   🕐 {wait_hours} soat {wait_minutes % 60} daqiqa")
            elif wait_minutes > 0:
                print(f"   ⏱️  {wait_minutes} daqiqa")
            else:
                print(f"   ⏱️  {wait_seconds} soniya")
            
            print(f"\n💡 Sababi:")
            print(f"   ⚠️  Siz juda ko'p login urinish qildingiz")
            print(f"   🔒 Telegram vaqtincha bloklab qo'ydi")
            
            print(f"\n✅ Yechim:")
            print(f"   1. {wait_minutes} daqiqa (yoki {wait_hours} soat) kuting")
            print(f"   2. Hech narsa qilmang bu vaqtda")
            print(f"   3. Keyin qayta urinib ko'ring")
            
            print(f"\n🔄 Yoki:")
            print(f"   • VPN ishlatib, IP manzilni o'zgartiring")
            print(f"   • Boshqa qurilmadan urinib ko'ring")
            print(f"   • Mobil internetga o'ting (Wi-Fi o'rniga)")
            print("="*70 + "\n")
        
        except PhoneNumberBannedError:
            print(f"   ❌ RAQAM BLOKLANGAN!\n")
            print(f"{'='*70}")
            print("🚫 BU TELEFON RAQAM BUTUNLAY BLOKLANGAN!")
            print("="*70)
            print(f"\n⚠️  Bu raqam Telegram tomonidan:")
            print(f"   • Spam uchun bloklangan")
            print(f"   • Qoidalarni buzganlik uchun ban qilingan")
            print(f"   • Bu raqamdan foydalanib bo'lmaydi")
            
            print(f"\n✅ Yechim:")
            print(f"   • Boshqa telefon raqamdan foydalaning")
            print(f"   • Telegram support ga murojaat qiling (agar xato deb hisoblasangiz)")
            print("="*70 + "\n")
        
        except PhoneNumberInvalidError:
            print(f"   ❌ RAQAM NOTO'G'RI!\n")
            print(f"{'='*70}")
            print("🚫 TELEFON RAQAM API BILAN MOS KELMAYDI!")
            print("="*70)
            print(f"\n💡 Sababi:")
            print(f"   • Bu raqam my.telegram.org da ishlatilmagan")
            print(f"   • API boshqa raqam bilan yaratilgan")
            
            print(f"\n✅ Yechim:")
            print(f"   1. https://my.telegram.org ga kiring")
            print(f"   2. Qaysi raqam bilan API yaratganingizni aniqlang")
            print(f"   3. O'sha raqamni ishlating")
            print(f"\n   YOKI:")
            print(f"   1. my.telegram.org ga {phone} bilan kiring")
            print(f"   2. Yangi API yarating")
            print(f"   3. config.py ni yangilang")
            print("="*70 + "\n")
        
        except ApiIdInvalidError:
            print(f"   ❌ API MA'LUMOTLAR XATO!\n")
            print(f"{'='*70}")
            print("🚫 API_ID YOKI API_HASH NOTO'G'RI!")
            print("="*70)
            print(f"\n✅ Yechim:")
            print(f"   1. https://my.telegram.org ga o'ting")
            print(f"   2. API ma'lumotlarni to'g'ri ko'chiring")
            print(f"   3. config.py ni tekshiring")
            print("="*70 + "\n")
        
        except Exception as e:
            print(f"   ❌ KUTILMAGAN XATOLIK!\n")
            print(f"{'='*70}")
            print(f"Xatolik: {type(e).__name__}")
            print(f"Tavsif: {e}")
            print("="*70 + "\n")
        
        await client.disconnect()
    
    except Exception as e:
        print(f"\n❌ Ulanish xatoligi: {e}\n")
    
    finally:
        # Test faylni tozalash
        import os
        try:
            if os.path.exists("check_ban_test.session"):
                os.remove("check_ban_test.session")
                print("🧹 Test fayl tozalandi")
        except:
            pass

async def quick_check():
    """Tezkor tekshirish - kod yubormasdan"""
    print("\n" + "="*70)
    print("⚡ TEZKOR TEKSHIRUV (kod yuborilmaydi)")
    print("="*70 + "\n")
    
    client = TelegramClient("quick_check", api_id, api_hash)
    
    try:
        await client.connect()
        
        if await client.is_user_authorized():
            me = await client.get_me()
            print("✅ Allaqachon tizimga kirilgan!")
            print(f"   👤 {me.first_name}")
            print(f"   📞 {me.phone}")
            print(f"   🆔 {me.id}")
            print("\n💡 Bloklanmagan, session mavjud!")
            print("   main.py ni ishga tushirishingiz mumkin\n")
        else:
            print("ℹ️  Tizimga kirilmagan, to'liq tekshiruv kerak")
        
        await client.disconnect()
        
    except Exception as e:
        print(f"❌ Xatolik: {e}")
    
    finally:
        import os
        try:
            if os.path.exists("quick_check.session"):
                os.remove("quick_check.session")
        except:
            pass

if __name__ == "__main__":
    print("\n🔍 TELEGRAM BAN CHECKER")
    print("\n1. To'liq tekshiruv (kod yuboriladi)")
    print("2. Tezkor tekshiruv (faqat session tekshirish)")
    
    choice = input("\nTanlang (1/2): ").strip()
    
    try:
        if choice == "2":
            asyncio.run(quick_check())
        else:
            asyncio.run(check_flood_status())
    except KeyboardInterrupt:
        print("\n\n⛔ To'xtatildi")