# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A professional 3-bot Telegram system for keyword monitoring with payment subscription management. Designed for high-performance message capture (100-300ms response time) before admin bot deletions.

**Three-bot architecture:**
1. **UserBot** ([bots/userbot/main.py](bots/userbot/main.py)): Telethon-based keyword monitor with FAST/NORMAL modes
2. **Admin Bot** ([bots/admin/main.py](bots/admin/main.py)): Aiogram-based configuration panel for keywords, groups, and blackwords
3. **Customer Bot** ([bots/customer/main.py](bots/customer/main.py)): Aiogram-based payment processing and user subscription management

**Operational modes:**
- **FAST mode**: Groups with immediate message deletion (100-300ms via raw events + buffer forwarding)
- **NORMAL mode**: Regular groups (500-1000ms standard event handling)

## Project Structure

```
ToshkentgaKeyWordBot/
├── bots/                      # Barcha bot modullari
│   ├── userbot/              # Keyword monitoring (Telethon)
│   │   ├── __init__.py
│   │   └── main.py           # UserBot asosiy fayl
│   ├── admin/                # Configuration panel (Aiogram)
│   │   ├── __init__.py
│   │   └── main.py           # Admin Bot asosiy fayl
│   └── customer/             # Payment & subscriptions (Aiogram)
│       ├── __init__.py
│       └── main.py           # Customer Bot asosiy fayl
├── core/                      # Asosiy funksionallik
│   ├── __init__.py
│   ├── config.py             # Konfiguratsiya
│   └── storage.py            # Ma'lumotlar bazasi
├── services/                  # Orqa fon servislari
│   ├── __init__.py
│   ├── subscription.py       # Obuna boshqaruvi
│   └── auto_kick.py          # Avtomatik kick
├── data/                      # Ma'lumotlar fayllari (avtomatik yaratiladi)
│   ├── .gitkeep
│   ├── bot_state.json         # Keywords, source/target groups, blackwords
│   ├── payment_requests.json  # To'lov so'rovlari (screenshot + status)
│   ├── approved_users.json    # Tasdiqlangan foydalanuvchilar
│   └── subscriptions.json     # Obuna narxlari
├── sessions/                  # Telegram sessiyalari
│   └── userbot_session.session
├── scripts/                   # Utility skriptlar
│   ├── check_ban.py
│   └── test_connection.py
├── main.py                    # Kirish nuqtasi
├── .gitignore
└── README.md
```

## Development Commands

### Running Bots

**All 3 bots together (recommended):**
```bash
python main.py
```
Ishga tushiradi: UserBot + Admin Bot + Customer Bot

**Individual bots (debugging):**
```bash
# Faqat Customer Bot
python -m bots.customer.main
```

### Background Services
```bash
# Auto-kick expired users
python -m services.auto_kick
```

### Testing & Diagnostics
```bash
# API credentials va telefon raqamini tekshirish
python -m scripts.test_connection

# Telegram flood ban yoki rate limiting tekshirish
python -m scripts.check_ban

# Dependencies o'rnatish (Telethon 1.34.0, Aiogram 3.3.0, uvloop 0.19.0)
pip install -r requirements.txt
```

## Architecture

### Three-Bot System

**[main.py](main.py)** - Entry point for all 3 bots:
- Launches UserBot + Admin Bot + Customer Bot concurrently with `asyncio.gather()`
- All bots share the same asyncio event loop

**Bot 1: [bots/userbot/main.py](bots/userbot/main.py)** - Telethon keyword monitor:
- **Raw Events Handler**: Processes `UpdateNewMessage`/`UpdateNewChannelMessage` directly (bypasses Telethon wrappers, saves 50-100ms)
- **In-Memory Cache**: `source_groups_cache = {"fast": {}, "normal": {}}` for O(1) group type lookups
- **uvloop Support**: Auto-enables if available (3-5x faster on Linux/macOS, graceful fallback on Windows)
- **Dual Processing Modes**:
  - FAST: Immediately forwards to buffer group → spawns async task for formatted target delivery
  - NORMAL: Async task for user lookup + formatted target delivery
- **Auto-Update**: Refreshes source groups every 30 minutes with cache rebuild
- **CRITICAL**: Uses `USERBOT_API_ID`/`USERBOT_API_HASH` from [core/config.py](core/config.py)

**Bot 2: [bots/admin/main.py](bots/admin/main.py)** - Aiogram configuration panel:
- **Keyboard-based UI**: ReplyKeyboardMarkup for main navigation
- **FSM States**: `AdminForm.input_value`, `AdminForm.context`, `AdminForm.group_type_selection`
- **Manages**: Keywords, blackwords, source groups (FAST/NORMAL type), target groups, buffer group
- **Features**: Paginated lists (20 items/page), add/delete operations, statistics dashboard
- **Access Control**: Multiple admins via `ADMIN_IDS` list in [core/config.py](core/config.py)
- **Token**: Uses `ADMIN_BOT_TOKEN` from [core/config.py](core/config.py)

**Bot 3: [bots/customer/main.py](bots/customer/main.py)** - Aiogram payment & subscription system:
- **Dual Interface**:
  - Admin panel: Review payment requests, manage users, broadcast messages, update pricing
  - Customer interface: Submit payments (screenshot upload), check subscription status, help/support
- **Payment Flow**: User uploads screenshot → Admin reviews → Admin approves/rejects → User added to approved_users.json
- **Subscription Periods**: 1 month, 3 months, 1 year (configurable prices in subscriptions.json)
- **Access Control**: Same `ADMIN_IDS` from [core/config.py](core/config.py)
- **Token**: Uses `CUSTOMER_BOT_TOKEN` from [core/config.py](core/config.py)
- **Data Files**: payment_requests.json, approved_users.json, subscriptions.json
- **Test Group Integration**: `TEST_GROUP_ID` and `TEST_GROUP_LINK` for approved user group management

### Data Management

**[core/storage.py](core/storage.py)** - JSON persistence layer:
- CRUD operations: `add_item()`, `remove_item()`, `get_items()`, `load_state()`, `save_state()`
- `add_item(key, value, item_type=None)`: For source_groups, `item_type` can be "fast" or "normal"
- `get_items(key)`: Returns display-friendly format (e.g., "group_id (fast)")
- Thread-safe file operations with UTF-8 encoding

**[data/bot_state.json](data/bot_state.json)** - Main configuration (UserBot + Admin Bot):
```json
{
  "keywords": ["yetkazib beraman", "pochta"],
  "source_groups": [
    {"id": "group_username", "type": "fast"},
    {"id": "1234567890", "type": "normal"}
  ],
  "target_groups": ["-1001234567890"],
  "buffer_group": "-1009876543210",
  "blackwords": ["spam", "reklama"]
}
```

**Payment data files (Customer Bot)**:
- `payment_requests.json`: Pending/approved/rejected payment requests with screenshot file_id
- `approved_users.json`: User records with subscription expiry dates
- `subscriptions.json`: Pricing for 1_month, 3_months, 1_year periods

### Services & Utilities

**[services/subscription.py](services/subscription.py)** - Subscription management system:
- `SubscriptionManager`: Handles user registration, subscription activation, access checks
- `SubscriptionStatus`: FREE_TRIAL, ACTIVE, EXPIRED, BLOCKED states
- `check_user_access(user_id)`: Quick boolean access check
- Free trial: 3 days default (configurable in settings)
- Integrates with Click/Payme/Stripe payment methods (structure ready, implementation TBD)

**[services/auto_kick.py](services/auto_kick.py)** - Auto-kick expired users:
- Removes users from target groups after subscription expiry
- Preserves owners and admins (via `ADMIN_IDS`)
- Logs kicked users to `kick_log.json`
- Designed to run via cron/task scheduler

**[scripts/check_ban.py](scripts/check_ban.py)** - Telegram ban diagnostics:
- Detects FloodWaitError, PhoneNumberBannedError, ApiIdInvalidError
- Two modes: full check (sends code) or quick check (session only)
- Auto-cleans test session files

**[scripts/test_connection.py](scripts/test_connection.py)** - API validation:
- Tests Telegram API credentials
- Handles phone authorization flow
- Auto-cleans test sessions

## Configuration

**[core/config.py](core/config.py)** - Centralized configuration:
```python
# Telegram API (from my.telegram.org)
api_id = 21318254
api_hash = "bd01206ecf54279803192f5a1b33e3ae"

# UserBot credentials (separate from main API)
USERBOT_API_ID = 35590072
USERBOT_API_HASH = "48e5dad8bef68a54aac5b2ce0702b82c"

# Bot tokens (from @BotFather)
ADMIN_BOT_TOKEN = "8250455047:AAH..."
CUSTOMER_BOT_TOKEN = "8383987517:AAG..."

# Admin access (get IDs from @userinfobot)
ADMIN_IDS = [7106025530, 5129045986]

# Test group for customer bot
TEST_GROUP_LINK = "https://t.me/+A3DpeN93ohg3ODgy"
TEST_GROUP_ID = -5002847429
```

**Session management:**
- UserBot: `sessions/userbot_session.session` (persistent, don't delete during operation)
- Test scripts: Auto-create and auto-delete temporary sessions

## Key Implementation Details

### UserBot Performance Optimizations

**1. Raw Event Handler** (`setup_raw_handler()` in [bots/userbot/main.py](bots/userbot/main.py)):
```python
@client.on(events.Raw(types=[UpdateNewMessage, UpdateNewChannelMessage]))
async def raw_message_handler(update):
    message = update.message  # Direct access, no wrapper overhead
    # Process in 100-300ms
```
- Bypasses Telethon's event wrapper layer (saves 50-100ms)
- Direct `Message` object extraction from raw updates

**2. In-Memory Cache** (`source_groups_cache` in [bots/userbot/main.py](bots/userbot/main.py)):
```python
source_groups_cache = {
    "fast": {chat_id: group_info},
    "normal": {chat_id: group_info}
}
```
- O(1) lookup for group type during message processing
- `rebuild_cache()`: Syncs with bot_state.json every 30 minutes
- FAST groups: Pre-caches last 100 messages to load user entities

**3. Async Task Spawning** (non-blocking execution):
```python
asyncio.create_task(handle_fast_message(...))  # Fire-and-forget
```
- FAST mode: Immediate buffer forwarding, async target delivery
- Prevents event loop blocking during formatting/API calls

**4. uvloop Integration** (3-5x speed boost):
```python
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
except ImportError:
    pass  # Windows fallback
```

**5. Fast User Extraction** (no async calls):
- Priority 1: Extract phone from `MessageEntityPhone` entities
- Priority 2: Use `post_author` field (channel posts)
- Priority 3: Check Telethon's `_entity_cache` for username
- Avoids slow `await message.get_sender()` API call

### Keyword & Blackword Logic

**`check_keyword_match(text, keywords)`** in [bots/userbot/main.py](bots/userbot/main.py):
```python
def check_keyword_match(text, keywords):
    text_lower = text.lower()

    # Multi-word phrases (substring match)
    for kw in keywords:
        if ' ' in kw and kw in text_lower:
            return kw

    # Single-word (set lookup O(1))
    words = set(re.findall(r'\b\w+\b', text_lower))
    for kw in keywords:
        if ' ' not in kw and kw in words:
            return kw
    return None
```

**`check_blackword(text, blackwords)`** - Same logic, checked AFTER keywords:
- If blackword found, message is dropped even if keyword matches
- Prevents spam/ads from being forwarded

### Message Processing Flows

**FAST Mode** (in [bots/userbot/main.py](bots/userbot/main.py)):
```
Raw Update → Extract Message → Get chat_id from PeerChannel
    ↓
O(1) cache lookup: is this a FAST group?
    ↓
Keyword match check → Blackword filter
    ↓
Extract user identifier (phone/username) from entities (no async!)
    ↓
IMMEDIATELY forward to buffer_group (100-300ms total)
    ↓
Spawn async task: format_and_send_to_targets() [runs in background]
```

**NORMAL Mode** (in [bots/userbot/main.py](bots/userbot/main.py)):
```
Raw Update → Extract Message → Get chat_id
    ↓
O(1) cache lookup: is this a NORMAL group?
    ↓
Keyword match check → Blackword filter
    ↓
Spawn async task: handle_normal_message()
    ↓
await get_sender_details() → Full user info
    ↓
Format and send to target groups (500-1000ms total)
```

### Source Group Auto-Update

**Schedule**: Every 30 minutes (in [bots/userbot/main.py](bots/userbot/main.py) `run_userbot()`)

**`update_source_groups()`** process:
1. Fetch all dialogs via `client.get_dialogs()`
2. Filter groups only (exclude channels with `broadcast=True`)
3. Exclude groups already in target_groups
4. Preserve existing type ("fast"/"normal") from bot_state.json
5. Save as objects: `{"id": "group_key", "type": "fast|normal"}`
6. Call `rebuild_cache()` to sync in-memory cache

**`rebuild_cache()`** process:
1. Clear `source_groups_cache` dict
2. Load from bot_state.json
3. Resolve each group (username/ID → entity)
4. For FAST groups: Pre-cache users by iterating last 100 messages

### Admin Bot FSM States

**Three states** in [bots/admin/main.py](bots/admin/main.py):
- `AdminForm.input_value`: Captures user input (group ID, keyword, etc.)
- `AdminForm.context`: Tracks operation type (add/delete + section)
- `AdminForm.group_type_selection`: For FAST/NORMAL type selection

**Source group addition flow**:
```
User clicks "Qo'shish" → Type selection menu (FAST/NORMAL buttons)
    ↓
User selects type → Store in FSM data as `selected_type`
    ↓
User sends group ID → Extract from t.me link if present
    ↓
Call add_item(key, value, item_type=selected_type)
    ↓
Save to bot_state.json → UserBot auto-updates within 30 min
```

### Customer Bot Payment Flow

**Payment submission** in [bots/customer/main.py](bots/customer/main.py):
```
User selects subscription period (1/3/12 months)
    ↓
User uploads screenshot
    ↓
Save to payment_requests.json with status="pending"
    ↓
Admin receives notification in admin panel
    ↓
Admin reviews screenshot → Approve/Reject
    ↓
If approved: User added to approved_users.json with expiry_date
    ↓
User gets access to target groups
```

### Data Flow Patterns

**Configuration updates**:
```
Admin Bot (user input) → core/storage.py → data/bot_state.json
    ↓
UserBot loads on each message (or from cache every 30 min)
```

**Message forwarding**:
```
Source group message → Keyword match → Blackword filter
    ↓
Extract user info → Format message
    ↓
Send to buffer_group (FAST only) + target_groups
```

**Error handling**:
- All async operations wrapped in try-except
- Console output in Uzbek for operators
- Diagnostic scripts provide detailed error explanations

## Important Notes

### Credentials & Configuration
- All credentials are in [core/config.py](core/config.py)
- To add admins: Add Telegram IDs to `ADMIN_IDS` list (get IDs from @userinfobot)
- UserBot uses separate API credentials: `USERBOT_API_ID` and `USERBOT_API_HASH`

### Buffer Group
- Only required for FAST mode source groups
- If no FAST groups configured, buffer_group can be empty
- Used for immediate forwarding (100-300ms) before admin bot deletes message

### Auto-Update Behavior
- Source groups refresh every 30 minutes automatically
- Manual trigger: Restart UserBot
- Changes via Admin Bot appear immediately in bot_state.json but UserBot loads from cache

### Platform Compatibility
- **uvloop**: Linux/macOS only (3-5x speed boost), Windows uses standard asyncio
- All bots tested on Windows/Linux

### Session Management
- `sessions/userbot_session.session`: Persistent, don't delete during operation
- Test scripts auto-create and auto-delete temporary sessions
- If session corrupted, delete and re-authenticate

### Handler Architecture
- UserBot uses **single raw event handler** for all messages
- Branches based on cached group type (O(1) lookup)
- Don't add additional message handlers - will impact 100-300ms FAST mode performance

### File Operations
- All JSON files use UTF-8 encoding
- Thread-safe file operations in storage.py
- Data files auto-created in `data/` directory on first run

### Message Link Format
- Public groups: `https://t.me/{username}/{message_id}`
- Private groups: `https://t.me/c/{chat_id_without_-100}/{message_id}`

### Customer Bot Considerations
- Runs together with other bots via `python main.py`
- Shares ADMIN_IDS with Admin Bot for access control
- Payment approval is manual (screenshot review by admin)
- No auto-kick during operation (run services/auto_kick.py separately via cron)
