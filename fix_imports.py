"""
Fix imports in all bot files
"""

from pathlib import Path
import re

ROOT = Path(__file__).parent

# Files to fix and their import replacements
FIXES = {
    "bots/payment/main.py": [
        ("from payment_bot import", "from .main import"),
    ],
    "bots/payment/admin_panel.py": [
        ("from payment_bot import", "from .main import"),
    ],
    "services/subscription.py": [],  # No imports to fix
    "services/auto_kick.py": [],  # Uses direct paths
}

def fix_file_imports(file_path):
    """Fix imports in a file"""
    full_path = ROOT / file_path

    if not full_path.exists():
        print(f"SKIP: {file_path} not found")
        return

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content

        # Common replacements
        content = re.sub(r'^from storage import', 'from core.storage import', content, flags=re.MULTILINE)
        content = re.sub(r'^from config import', 'from core.config import', content, flags=re.MULTILINE)
        content = re.sub(r'^import storage', 'import core.storage as storage', content, flags=re.MULTILINE)
        content = re.sub(r'^import config', 'import core.config as config', content, flags=re.MULTILINE)

        if content != original:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"OK: {file_path}")
        else:
            print(f"SKIP: {file_path} - no changes needed")

    except Exception as e:
        print(f"ERROR: {file_path} - {e}")

def main():
    print("="*60)
    print("FIX IMPORTS")
    print("="*60)
    print()

    # Auto-discover Python files in bots/services
    python_files = []
    python_files.extend(ROOT.glob("bots/**/*.py"))
    python_files.extend(ROOT.glob("services/**/*.py"))

    for file_path in python_files:
        if file_path.name == "__init__.py":
            continue
        rel_path = file_path.relative_to(ROOT)
        fix_file_imports(str(rel_path))

    print()
    print("="*60)
    print("DONE!")
    print("="*60)

if __name__ == "__main__":
    main()
