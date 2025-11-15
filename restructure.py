"""
Automatic Project Restructure Script
Loyihani avtomatik professional arxitekturaga o'tkazish
"""

import os
import shutil
from pathlib import Path

# Current directory
ROOT = Path(__file__).parent

# File mapping: old_path -> new_path
FILE_MOVES = {
    # Bots
    "userbot.py": "bots/userbot/main.py",
    "admin_bot.py": "bots/admin/main.py",
    "payment_bot.py": "bots/payment/main.py",
    "payment_admin.py": "bots/payment/admin_panel.py",

    # Core
    # storage.py va config.py allaqachon ko'chirilgan

    # Services
    "subscription.py": "services/subscription.py",
    "auto_kick.py": "services/auto_kick.py",

    # Scripts
    "check_ban.py": "scripts/check_ban.py",
    "test_connection.py": "scripts/test_connection.py",

    # Data files
    "bot_state.json": "data/bot_state.json",
    "bot_data.json": "data/bot_data.json.backup",  # Backup sifatida
}

# Files to delete
DELETE_FILES = [
    "ADMINS_QOSHISH.md",
    "FORMAT_TEST.md",
    "PAYMENT_SETUP.md",
    "QUICK_START.md",
    "TEST_CHECKLIST.txt",
    "TEST_QILISH.md",
    "SETUP_UZ.md",
    "RESTRUCTURE_PLAN.md",
]

# Folders to delete
DELETE_FOLDERS = [
    "nulkll",
]

def move_file(src, dst):
    """Faylni ko'chirish"""
    src_path = ROOT / src
    dst_path = ROOT / dst

    if not src_path.exists():
        print(f"SKIP: {src} topilmadi")
        return False

    # Ensure destination folder exists
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        shutil.copy2(src_path, dst_path)
        print(f"OK: {src} -> {dst}")
        return True
    except Exception as e:
        print(f"ERROR: {src} - {e}")
        return False

def delete_file(file_path):
    """Faylni o'chirish"""
    full_path = ROOT / file_path

    if not full_path.exists():
        return

    try:
        full_path.unlink()
        print(f"DELETE: {file_path}")
    except Exception as e:
        print(f"ERROR: {file_path} - {e}")

def delete_folder(folder_path):
    """Folderni o'chirish"""
    full_path = ROOT / folder_path

    if not full_path.exists():
        return

    try:
        shutil.rmtree(full_path)
        print(f"DELETE: {folder_path}/")
    except Exception as e:
        print(f"ERROR: {folder_path}/ - {e}")

def create_gitignore():
    """Create .gitignore"""
    content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
dist/
build/

# Telegram sessions
*.session
*.session-journal

# Data files
data/*.json
!data/.gitkeep

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Environment
.env
venv/
env/
"""

    gitignore_path = ROOT / ".gitignore"

    with open(gitignore_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print("OK: .gitignore yaratildi")

def create_data_gitkeep():
    """Create data/.gitkeep"""
    gitkeep_path = ROOT / "data" / ".gitkeep"
    gitkeep_path.touch()
    print("OK: data/.gitkeep yaratildi")

def main():
    """Main restructure function"""
    print("="*60)
    print("PROJECT RESTRUCTURE")
    print("="*60)
    print()

    # Step 1: Move files
    print("[1] Fayllarni ko'chirish...")
    moved_count = 0
    for src, dst in FILE_MOVES.items():
        if move_file(src, dst):
            moved_count += 1
    print(f"   OK: {moved_count}/{len(FILE_MOVES)} fayl ko'chirildi\n")

    # Step 2: Create .gitignore
    print("[2] .gitignore yaratish...")
    create_gitignore()
    create_data_gitkeep()
    print()

    # Step 3: Delete unnecessary files
    print("[3] Keraksiz fayllarni o'chirish...")
    for file_path in DELETE_FILES:
        delete_file(file_path)
    print()

    # Step 4: Delete unnecessary folders
    print("[4] Keraksiz folderlarni o'chirish...")
    for folder_path in DELETE_FOLDERS:
        delete_folder(folder_path)
    print()

    # Step 5: Move sessions
    print("[5] Session fayllarni ko'chirish...")
    sessions_dir = ROOT / "sessions"
    sessions_dir.mkdir(exist_ok=True)

    for file in ROOT.glob("*.session*"):
        dst = sessions_dir / file.name
        try:
            shutil.move(str(file), str(dst))
            print(f"OK: {file.name} -> sessions/")
        except Exception as e:
            print(f"ERROR: {file.name}: {e}")
    print()

    print("="*60)
    print("TAYYOR!")
    print("="*60)
    print()
    print("Keyingi qadamlar:")
    print("1. main.py ni yangilang (import pathlarni)")
    print("2. Barcha botlarni tekshiring")
    print("3. python main.py - ishga tushiring")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⛔ To'xtatildi")
    except Exception as e:
        print(f"\n❌ Xatolik: {e}")
        import traceback
        traceback.print_exc()
