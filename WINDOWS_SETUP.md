# Windows'da Pyrogram Bot'ni ishga tushirish

## ⚠️ Muammolar va yechimlar

### 1. TgCrypto o'rnatish

**Muammo:**
```
TgCrypto is missing! Pyrogram will work the same, but at a much slower speed.
```

**Yechim:**
```powershell
pip install tgcrypto
```

**Agar Visual Studio Build Tools kerak bo'lsa:**
1. https://visualstudio.microsoft.com/downloads/ ga o'ting
2. "Build Tools for Visual Studio" yuklab oling
3. "Desktop development with C++" komponentini o'rnating
4. Qayta urinib ko'ring:
   ```powershell
   pip install tgcrypto
   ```

### 2. Bot conflict xatoligi

**Muammo:**
```
Conflict: terminated by other getUpdates request
```

**Sabab:** Eski bot instance ishlab turibdi

**Yechim 1 - Task Manager:**
1. `Ctrl + Shift + Esc` bosing
2. "Details" tab'ga o'ting
3. Barcha `python.exe` jarayonlarini toping
4. Right-click → "End Task"

**Yechim 2 - PowerShell:**
```powershell
# Barcha Python jarayonlarini to'xtatish
Get-Process python | Stop-Process -Force

# Yoki aniqroq:
Get-Process | Where-Object {$_.ProcessName -like "*python*"} | Stop-Process -Force
```

**Yechim 3 - Port tekshirish:**
```powershell
# Bot qaysi portda ishlab turganini topish
netstat -ano | findstr :443
netstat -ano | findstr :8080

# Process ID orqali to'xtatish
taskkill /PID <process_id> /F
```

### 3. uvloop ishlamaydi (normal)

**Muammo:**
```
ℹ️  uvloop topilmadi, standart asyncio ishlatilmoqda
```

**Izoh:** Windows'da uvloop ishlamaydi. Bu **normal** holat.
Bot standart asyncio bilan yaxshi ishlaydi.

---

## 🚀 To'g'ri ishga tushirish tartibi

### 1. Dependencies o'rnatish
```powershell
pip install -r requirements.txt
```

### 2. Eski session tozalash (ixtiyoriy)
```powershell
# Agar Telethon'dan Pyrogram'ga o'tgan bo'lsangiz
Remove-Item userbot_session.session -ErrorAction SilentlyContinue
Remove-Item -Recurse pyrogram_session -ErrorAction SilentlyContinue
```

### 3. Eski bot instance'larni to'xtatish
```powershell
Get-Process python | Stop-Process -Force
```

### 4. Botni ishga tushirish
```powershell
python main.py
```

### 5. Birinchi marta ishga tushirish
Bot telefon raqamingizni so'raydi:
```
Enter phone number or bot token: +998901234567
```

Keyin Telegram'dan kod keladi, uni kiriting:
```
Enter phone code: 12345
```

---

## 🔍 Muammolarni aniqlash

### Bot ishlamayapti
```powershell
# Loglarni tekshirish
python main.py

# Hatoliklarni ko'rish
```

### Port band
```powershell
# 443 portni tekshirish (Telegram API)
netstat -ano | findstr :443

# Bandlikni to'xtatish
taskkill /PID <PID> /F
```

### Session muammosi
```powershell
# Session'ni qayta yaratish
Remove-Item -Recurse pyrogram_session -Force
python main.py
```

---

## ✅ Muvaffaqiyatli ishga tushirish

Agar hammasi to'g'ri bo'lsa, siz quyidagi xabarlarni ko'rasiz:

```
⚡ uvloop yoqildi (maksimal tezlik)  # yoki standart asyncio (Windows)
🚀 UserBot ishga tushmoqda (Pyrogram)...
✅ UserBot ulandi (Pyrogram)
⚡ Raw handler sozlanmoqda...
🔄 Source guruhlar yangilanmoqda...
✅ 25 ta guruh yangilandi
📦 Cache: 3 ta fast, 22 ta normal guruh
✅ Raw handler yoqildi (Pyrogram - maksimal tezlik)
INFO:aiogram:Application started
```

---

## 🆘 Qo'shimcha yordam

Agar muammo davom etsa:

1. **Dependencies tekshirish:**
   ```powershell
   pip list | findstr "pyrogram aiogram tgcrypto"
   ```

2. **Python versiyasi:**
   ```powershell
   python --version  # 3.8+ bo'lishi kerak
   ```

3. **Loglarni saqlash:**
   ```powershell
   python main.py > bot_log.txt 2>&1
   ```

4. **Session'ni tozalash:**
   ```powershell
   Remove-Item -Recurse pyrogram_session -Force
   Remove-Item userbot_session.session -ErrorAction SilentlyContinue
   ```
