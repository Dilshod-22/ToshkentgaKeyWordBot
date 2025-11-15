import json
from pathlib import Path
import os

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

STATE_FILE = str(DATA_DIR / "bot_state.json")

def get_default_state():
    return {
        "keywords": [],
        "source_groups": [],
        "target_groups": [],
        "buffer_group": "",
        "blackwords": []  # Yangi: qora ro'yxat so'zlari
    }

def load_state():
    if not Path(STATE_FILE).exists():
        return get_default_state()
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Blackwords qo'shish (eski state'lar uchun)
            if "blackwords" not in data:
                data["blackwords"] = []
            return data
    except:
        return get_default_state()

def save_state(state):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def get_items(key):
    state = load_state()
    items = state.get(key, [])
    
    # Source groups uchun maxsus format
    if key == "source_groups":
        result = []
        for item in items:
            if isinstance(item, dict):
                result.append(f"{item['id']} ({item.get('type', 'normal')})")
            else:
                result.append(f"{item} (normal)")
        return result
    
    return items

def add_item(key, value, item_type=None):
    state = load_state()
    items = state.get(key, [])
    
    # Source groups uchun maxsus qo'shish
    if key == "source_groups":
        # Mavjudligini tekshirish
        for item in items:
            if isinstance(item, dict) and item.get("id") == value:
                return False
            elif item == value:
                return False
        
        # Yangi item qo'shish
        items.append({
            "id": value,
            "type": item_type or "normal"
        })
    else:
        # Oddiy qo'shish
        if value in items:
            return False
        items.append(value)
    
    state[key] = items
    save_state(state)
    return True

def remove_item(key, value):
    state = load_state()
    items = state.get(key, [])
    
    # Source groups uchun maxsus o'chirish
    if key == "source_groups":
        new_items = []
        found = False
        for item in items:
            if isinstance(item, dict):
                if item.get("id") != value:
                    new_items.append(item)
                else:
                    found = True
            elif item != value:
                new_items.append(item)
            else:
                found = True
        
        state[key] = new_items
        save_state(state)
        return found
    else:
        # Oddiy o'chirish
        if value in items:
            items.remove(value)
            state[key] = items
            save_state(state)
            return True
        return False