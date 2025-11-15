# ⚡ High-Performance Telegram Keyword Monitor Bot

A lightning-fast Telegram bot that monitors groups for keywords and forwards matching messages. Optimized for catching messages before they're deleted by other admin bots.

## 🚀 Features

- **⚡ FAST Mode** - Raw event handling + buffer forwarding (100-300ms response time)
- **📝 NORMAL Mode** - Standard processing for regular groups
- **💾 In-Memory Cache** - O(1) group lookups
- **🔥 uvloop Support** - 3-5x performance boost on Linux/macOS
- **🤖 Admin Panel** - Easy configuration via Telegram bot
- **🔄 Auto-Update** - Source groups refresh every 30 minutes

## 📋 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure
# Edit config.py with your API credentials

# Run
python main.py
```

## 📖 Documentation

- [SETUP_UZ.md](SETUP_UZ.md) - Detailed setup guide (Uzbek)
- [CLAUDE.md](CLAUDE.md) - Architecture documentation

## 🎯 How It Works

### FAST Mode (for admin bot groups)
```
Message arrives → Forward to buffer (0.1-0.3s) → Format in background → Send to target
```

### NORMAL Mode (for regular groups)
```
Message arrives → Check keyword → Format → Send to target
```

## ⚙️ Architecture

- **UserBot** (Telethon) - Monitors groups using raw events
- **Admin Bot** (Aiogram) - Configuration interface
- **Storage** - JSON-based persistence with type support

## 🔧 Requirements

- Python 3.8+
- Telegram API credentials (my.telegram.org)
- Bot token (@BotFather)

## 📊 Performance

- **Raw events**: 50-100ms faster than standard handlers
- **Buffer forwarding**: Catches messages before deletion
- **Async tasks**: Non-blocking background processing
- **uvloop**: Up to 5x faster event loop (Linux/macOS)

## 🆘 Troubleshooting

```bash
# Test API connection
python test_connection.py

# Check for flood ban
python check_ban.py
```

## 📝 License

MIT
