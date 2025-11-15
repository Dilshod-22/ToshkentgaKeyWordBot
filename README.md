# Toshkent Keyword Bot

Professional 3-bot Telegram tizimi - Kalit so'zlarni kuzatish, Admin panel, Mijozlar boshqaruvi

---

## 📋 Umumiy Ma'lumot

Ushbu loyiha 3 ta mustaqil bot orqali ishlaydi:
1. **UserBot** - Telegram guruhlaridagi kalit so'zlarni kuzatish
2. **Admin Bot** - Kalit so'zlar va guruhlarni boshqarish
3. **Customer Bot** - Mijozlar va to'lovlar bilan ishlash

---

## 🤖 3 Bot Tizimi

### 1️⃣ UserBot - Monitoring Bot
**Vazifasi:** Guruhlardan kerakli xabarlarni topish va yuborish

**Imkoniyatlari:**
- ⚡ FAST rejim - Tez o'chiriladigan xabarlar uchun (100-300ms)
- 📝 NORMAL rejim - Oddiy guruhlar uchun (500-1000ms)
- 🔄 Avtomatik yangilanish - Har 30 daqiqada
- 🎯 Kalit so'zlar bo'yicha filtrlash
- 🚫 Blackwords - Keraksiz so'zlarni filtrlash

**Ishga tushirish:**
```bash
python main.py  # Admin Bot bilan birga
```

---

### 2️⃣ Admin Bot - Boshqaruv Paneli
**Vazifasi:** Kalit so'zlar va guruhlarni sozlash

**Imkoniyatlari:**
- 🔑 Kalit so'zlar qo'shish/o'chirish
- 📥 Source guruhlar (FAST/NORMAL)
- 📤 Target guruhlar
- 🚫 Blackwords - Spam filtri
- 📊 Statistika

**Foydalanuvchilar:** Faqat `ADMIN_IDS` ro'yxatidagi adminlar

**Ishga tushirish:**
```bash
python main.py  # UserBot bilan birga
```

---

### 3️⃣ Customer Bot - Mijozlar va To'lovlar
**Vazifasi:** Mijozlar bilan ishlash va to'lovlarni qabul qilish

#### 👨‍💼 Admin Panel (ADMIN_IDS uchun):
- ✅ **So'rovlar** - To'lov screenshotlarini ko'rish va tasdiqlash
- 📊 **Statistika** - Foydalanuvchilar va to'lovlar statistikasi
- 💰 **Narxlar** - Obuna narxlarini ko'rish va o'zgartirish
- 👥 **Foydalanuvchilar** - Barcha userlar ro'yxati
- 📢 **Xabar yuborish** - Ommaviy xabar yuborish

#### 👤 Mijozlar uchun:
- 💳 **To'lov qilish** - Screenshot yuklash va to'lov qilish
- 📝 **Mening accountim** - Obuna holati va amal qilish muddati
- ℹ️ **Yo'riqnoma** - Tizimdan foydalanish qo'llanmasi
- 💬 **Yordam** - Support bilan bog'lanish

**Ishga tushirish:**
```bash
python -m bots.customer.main
```

---

## 🚀 Tezkor Boshlash

### 1. Talab qilinadigan kutubxonalar

```bash
pip install -r requirements.txt
```

Kerakli kutubxonalar:
- `telethon` - UserBot uchun
- `aiogram` - Admin va Customer botlar uchun
- `asyncio` - Asinxron ishlash uchun

### 2. Sozlash

`core/config.py` faylini tahrirlang:

```python
# Telegram API (my.telegram.org dan)
USERBOT_API_ID = 12345678
USERBOT_API_HASH = "your_api_hash"

# Bot Tokenlar (BotFather dan)
ADMIN_BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
CUSTOMER_BOT_TOKEN = "0987654321:ZYXwvuTSRqpONMlkjIHGfedCBA"

# Adminlar (@userinfobot dan ID oling)
ADMIN_IDS = [
    7106025530,
    5129045986,
]

# Test guruh
TEST_GROUP_LINK = "https://t.me/+A3DpeN93ohg3ODgy"
```

### 3. Ishga tushirish

**Barcha 3 ta botni birga ishga tushirish:**
```bash
python main.py
```

Ishga tushadi:
- ✅ UserBot (Keyword monitoring)
- ✅ Admin Bot (Configuration panel)
- ✅ Customer Bot (Payment & subscriptions)

**Alohida bot ishga tushirish (debugging uchun):**
```bash
# Faqat Customer Bot
python -m bots.customer.main
```

---

## 📁 Loyiha Tuzilishi

```
ToshkentgaKeyWordBot/
│
├── bots/                      # Barcha botlar
│   ├── userbot/               # UserBot - Monitoring
│   │   ├── __init__.py
│   │   └── main.py
│   ├── admin/                 # Admin Bot - Boshqaruv
│   │   ├── __init__.py
│   │   └── main.py
│   └── customer/              # Customer Bot - Mijozlar
│       ├── __init__.py
│       └── main.py
│
├── core/                      # Asosiy modullar
│   ├── __init__.py
│   ├── config.py              # Barcha sozlamalar
│   └── storage.py             # Ma'lumotlar bazasi
│
├── services/                  # Qo'shimcha servislar
│   ├── __init__.py
│   ├── subscription.py        # Obuna boshqaruvi
│   └── auto_kick.py           # Avtomatik kick
│
├── data/                      # Ma'lumotlar fayllari
│   ├── .gitkeep
│   ├── bot_state.json         # Keywords, groups, blackwords
│   ├── payment_requests.json  # To'lov so'rovlari
│   ├── approved_users.json    # Tasdiqlangan userlar
│   └── subscriptions.json     # Obuna narxlari
│
├── sessions/                  # Telegram sessiyalari
│   └── userbot_session.session
│
├── scripts/                   # Utility skriptlar
│   ├── check_ban.py           # Ban tekshirish
│   └── test_connection.py     # API test
│
├── main.py                    # Asosiy kirish nuqtasi
├── README.md                  # Bu fayl
├── CLAUDE.md                  # Texnik hujjatlar
└── requirements.txt           # Kutubxonalar ro'yxati
```

---

## 💾 Ma'lumotlar Fayllari

### `data/bot_state.json`
Kalit so'zlar, guruhlar va blackwords

```json
{
  "keywords": ["yetkazib beraman", "pochta"],
  "source_groups": [
    {"id": "toshkent_bozor", "type": "fast"},
    {"id": "-1001234567890", "type": "normal"}
  ],
  "target_groups": ["-1009876543210"],
  "buffer_group": "-1005555555555",
  "blackwords": ["spam", "reklama"]
}
```

### `data/payment_requests.json`
To'lov so'rovlari (screenshot bilan)

```json
[
  {
    "user_id": 123456789,
    "username": "user123",
    "screenshot_file_id": "AgACAgIAAx...",
    "period": "1_month",
    "status": "pending",
    "created_at": "2025-11-15T12:00:00"
  }
]
```

### `data/approved_users.json`
Tasdiqlangan foydalanuvchilar

```json
[
  {
    "user_id": 123456789,
    "username": "user123",
    "period": "1_month",
    "joined_at": "2025-11-15",
    "expiry_date": "2025-12-15",
    "status": "active"
  }
]
```

### `data/subscriptions.json`
Obuna narxlari

```json
{
  "1_month": {"price": "50000", "name": "1 oylik"},
  "3_months": {"price": "135000", "name": "3 oylik"},
  "1_year": {"price": "480000", "name": "1 yillik"}
}
```

---

## 🔧 Qo'shimcha Servislar

### Auto-kick Servisi
Muddati tugagan userlarni avtomatik o'chirish

```bash
python -m services.auto_kick
```

### Utility Skriptlar

**Ban tekshirish:**
```bash
python -m scripts.check_ban
```

**API ulanishni test qilish:**
```bash
python -m scripts.test_connection
```

---

## ⚙️ Sozlamalar

### Telegram API
1. https://my.telegram.org ga kiring
2. API credentials oling (`api_id` va `api_hash`)
3. `core/config.py` ga kiriting

### Bot Tokenlari
1. @BotFather botiga `/newbot` yuboring
2. Bot nomi va username kiriting
3. Token oling va `core/config.py` ga kiriting

### Admin ID
1. @userinfobot ga `/start` yuboring
2. O'z ID ingizni oling
3. `ADMIN_IDS` ga qo'shing

---

## 📱 Foydalanish

### Admin Bot

1. Botni ishga tushiring: `/start`
2. **Kalit so'zlar** - qo'shish/o'chirish/ko'rish
3. **Source guruhlar** - monitoring qilinadigan guruhlar (FAST/NORMAL)
4. **Target guruhlar** - topilgan xabarlar yuboriladigan guruhlar
5. **Blackwords** - spam so'zlarni filtrlash

### Customer Bot - Admin

1. Botni ishga tushiring: `/start`
2. **So'rovlar** - Yangi to'lovlarni ko'rish va tasdiqlash
3. **Statistika** - Umumiy ma'lumotlar
4. **Narxlar** - `/setprice 1_month 60000`
5. **Xabar yuborish** - Barcha userlarga xabar

### Customer Bot - Mijoz

1. Botni ishga tushiring: `/start`
2. **To'lov qilish** - Davr tanlash va screenshot yuklash
3. **Mening accountim** - Obuna holati
4. **Yordam** - Support bilan bog'lanish

---

## 🎯 Test Qilish

### Test Sozlamalari
```python
# core/config.py
CUSTOMER_BOT_TOKEN = "8383987517:AAGb68qvvOG04huoFOX6OmTteYOpkS7Clo0"
TEST_GROUP_LINK = "https://t.me/+A3DpeN93ohg3ODgy"
```

### Test Jarayoni
1. Customer Bot'ni ishga tushiring
2. Telegram'da botga `/start` yuboring
3. To'lov qilishni sinab ko'ring
4. Admin sifatida so'rovni tasdiqlang

---

## 🛠 Xatoliklarni Tuzatish

### UserBot ishlamayapti
```bash
# Session faylni tekshiring
ls sessions/

# API credentials to'g'riligini tekshiring
python -m scripts.test_connection
```

### Admin Bot ulanmayapti
```bash
# Token to'g'riligini tekshiring
# core/config.py da ADMIN_BOT_TOKEN
```

### Import xatolari
```bash
# Kutubxonalarni qayta o'rnating
pip install -r requirements.txt --force-reinstall
```

---

## 📚 Hujjatlar

- **[CLAUDE.md](CLAUDE.md)** - Texnik arxitektura va kod tuzilishi
- **[RESTRUCTURE_SUMMARY.md](RESTRUCTURE_SUMMARY.md)** - Loyihani qayta tuzish tarixi

---

## 🤝 Yordam

Savol yoki muammolar bo'lsa:
- Telegram: @support
- Issues: GitHub Issues

---

## 📝 Litsenziya

MIT

---

## ✨ Muhim Xususiyatlar

- ✅ 3 ta mustaqil bot tizimi
- ✅ Markazlashtirilgan config
- ✅ Professional kod tuzilishi
- ✅ To'liq o'zbek tilida interface
- ✅ Screenshot asosida to'lov
- ✅ Obuna tizimi (1/3/12 oy)
- ✅ Admin boshqaruv paneli
- ✅ Ommaviy xabar yuborish
- ✅ Real-time monitoring (FAST/NORMAL)
- ✅ Blackwords filtri

---

**Muallif:** Abdumajid
**Versiya:** 2.0
**Sana:** 2025-11-15
