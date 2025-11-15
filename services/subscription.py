"""
Subscription Management System
Obuna boshqaruv tizimi - Professional implementation

Xususiyatlar:
- Foydalanuvchi obuna holati
- Bepul sinov muddati (3 kun)
- Premium obuna
- To'lov integratsiyasi uchun tayyor struktura
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

# Subscription fayllar
SUBSCRIPTIONS_FILE = "subscriptions.json"
SUBSCRIPTION_SETTINGS_FILE = "subscription_settings.json"


class SubscriptionStatus:
    """Obuna statuslari"""
    FREE_TRIAL = "free_trial"      # Bepul sinov
    ACTIVE = "active"               # Faol obuna
    EXPIRED = "expired"             # Obuna tugagan
    BLOCKED = "blocked"             # Bloklangan


class SubscriptionManager:
    """
    Professional obuna boshqaruv tizimi
    """

    def __init__(self):
        self.subscriptions = self._load_subscriptions()
        self.settings = self._load_settings()

    def _load_subscriptions(self) -> Dict:
        """Obuna ma'lumotlarini yuklash"""
        if not Path(SUBSCRIPTIONS_FILE).exists():
            return {}

        try:
            with open(SUBSCRIPTIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}

    def _save_subscriptions(self):
        """Obuna ma'lumotlarini saqlash"""
        with open(SUBSCRIPTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.subscriptions, f, ensure_ascii=False, indent=2)

    def _load_settings(self) -> Dict:
        """Obuna sozlamalarini yuklash"""
        default_settings = {
            "free_trial_days": 3,           # Bepul sinov kunlari
            "monthly_price": 50000,         # Oylik narx (so'm)
            "premium_features_enabled": True,
            "auto_block_on_expire": True,   # Obuna tugaganda avtomatik bloklash
            "grace_period_hours": 24,       # Qo'shimcha vaqt (soat)
            "payment_methods": {
                "click": {"enabled": False, "merchant_id": ""},
                "payme": {"enabled": False, "merchant_id": ""},
                "stripe": {"enabled": False, "api_key": ""}
            }
        }

        if not Path(SUBSCRIPTION_SETTINGS_FILE).exists():
            with open(SUBSCRIPTION_SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_settings, f, ensure_ascii=False, indent=2)
            return default_settings

        try:
            with open(SUBSCRIPTION_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return default_settings

    def register_user(self, user_id: int, username: str = None, full_name: str = None) -> Dict[str, Any]:
        """
        Yangi foydalanuvchini ro'yxatdan o'tkazish
        3 kunlik bepul sinov berish

        Returns:
            user_data: Foydalanuvchi ma'lumotlari
        """
        user_id = str(user_id)

        # Agar foydalanuvchi allaqachon ro'yxatdan o'tgan bo'lsa
        if user_id in self.subscriptions:
            return self.get_user_subscription(user_id)

        # Bepul sinov muddati
        trial_days = self.settings.get("free_trial_days", 3)
        now = datetime.now()
        trial_end = now + timedelta(days=trial_days)

        user_data = {
            "user_id": user_id,
            "username": username,
            "full_name": full_name,
            "status": SubscriptionStatus.FREE_TRIAL,
            "registered_at": now.isoformat(),
            "trial_start": now.isoformat(),
            "trial_end": trial_end.isoformat(),
            "subscription_start": None,
            "subscription_end": None,
            "payments": [],
            "total_paid": 0
        }

        self.subscriptions[user_id] = user_data
        self._save_subscriptions()

        return user_data

    def check_access(self, user_id: int) -> Dict[str, Any]:
        """
        Foydalanuvchi kirish huquqini tekshirish

        Returns:
            {
                "has_access": bool,
                "status": str,
                "expires_in_days": int,
                "message": str
            }
        """
        user_id = str(user_id)

        # Yangi foydalanuvchi - avtomatik ro'yxatdan o'tkazish
        if user_id not in self.subscriptions:
            user_data = self.register_user(user_id)
            return {
                "has_access": True,
                "status": user_data["status"],
                "expires_in_days": self.settings["free_trial_days"],
                "message": f"🎉 Sizga {self.settings['free_trial_days']} kunlik bepul sinov berildi!"
            }

        user_data = self.subscriptions[user_id]
        now = datetime.now()

        # BEPUL SINOV
        if user_data["status"] == SubscriptionStatus.FREE_TRIAL:
            trial_end = datetime.fromisoformat(user_data["trial_end"])

            if now < trial_end:
                days_left = (trial_end - now).days
                return {
                    "has_access": True,
                    "status": SubscriptionStatus.FREE_TRIAL,
                    "expires_in_days": days_left,
                    "message": f"🆓 Bepul sinov: {days_left} kun qoldi"
                }
            else:
                # Sinov muddati tugagan
                user_data["status"] = SubscriptionStatus.EXPIRED
                self._save_subscriptions()

                return {
                    "has_access": False,
                    "status": SubscriptionStatus.EXPIRED,
                    "expires_in_days": 0,
                    "message": "⏰ Bepul sinov muddati tugadi. Premium obunaga o'ting!"
                }

        # PREMIUM OBUNA
        elif user_data["status"] == SubscriptionStatus.ACTIVE:
            sub_end = datetime.fromisoformat(user_data["subscription_end"])

            if now < sub_end:
                days_left = (sub_end - now).days
                return {
                    "has_access": True,
                    "status": SubscriptionStatus.ACTIVE,
                    "expires_in_days": days_left,
                    "message": f"✅ Premium obuna: {days_left} kun qoldi"
                }
            else:
                # Obuna tugagan
                user_data["status"] = SubscriptionStatus.EXPIRED
                self._save_subscriptions()

                return {
                    "has_access": False,
                    "status": SubscriptionStatus.EXPIRED,
                    "expires_in_days": 0,
                    "message": "⏰ Obunangiz tugadi. Yana yangilang!"
                }

        # BLOKLANGAN
        elif user_data["status"] == SubscriptionStatus.BLOCKED:
            return {
                "has_access": False,
                "status": SubscriptionStatus.BLOCKED,
                "expires_in_days": 0,
                "message": "🚫 Sizning akkauntingiz bloklangan. Administratorga murojaat qiling."
            }

        # MUDDATI TUGAGAN
        else:
            return {
                "has_access": False,
                "status": SubscriptionStatus.EXPIRED,
                "expires_in_days": 0,
                "message": "⏰ Obunangiz tugagan. Yangilang!"
            }

    def activate_subscription(
        self,
        user_id: int,
        months: int = 1,
        payment_method: str = "manual",
        payment_id: str = None,
        amount: float = None
    ) -> Dict[str, Any]:
        """
        Obunani faollashtirish (to'lov qabul qilingandan keyin)

        Args:
            user_id: Foydalanuvchi ID
            months: Necha oylik obuna (default: 1)
            payment_method: To'lov usuli (click/payme/stripe/manual)
            payment_id: To'lov ID
            amount: To'lov miqdori

        Returns:
            user_data: Yangilangan foydalanuvchi ma'lumotlari
        """
        user_id = str(user_id)

        if user_id not in self.subscriptions:
            self.register_user(user_id)

        user_data = self.subscriptions[user_id]
        now = datetime.now()

        # Agar hozirda faol obuna bo'lsa, unga qo'shish
        if user_data["status"] == SubscriptionStatus.ACTIVE and user_data["subscription_end"]:
            current_end = datetime.fromisoformat(user_data["subscription_end"])
            if current_end > now:
                new_end = current_end + timedelta(days=30 * months)
            else:
                new_end = now + timedelta(days=30 * months)
        else:
            new_end = now + timedelta(days=30 * months)

        # Obunani yangilash
        user_data["status"] = SubscriptionStatus.ACTIVE
        user_data["subscription_start"] = now.isoformat()
        user_data["subscription_end"] = new_end.isoformat()

        # To'lov ma'lumotini qo'shish
        payment_record = {
            "payment_id": payment_id or f"manual_{int(now.timestamp())}",
            "method": payment_method,
            "amount": amount or self.settings["monthly_price"] * months,
            "months": months,
            "paid_at": now.isoformat(),
            "status": "completed"
        }
        user_data["payments"].append(payment_record)
        user_data["total_paid"] = user_data.get("total_paid", 0) + payment_record["amount"]

        self._save_subscriptions()

        return user_data

    def get_user_subscription(self, user_id: int) -> Optional[Dict]:
        """Foydalanuvchi obuna ma'lumotlarini olish"""
        user_id = str(user_id)
        return self.subscriptions.get(user_id)

    def block_user(self, user_id: int, reason: str = None):
        """Foydalanuvchini bloklash"""
        user_id = str(user_id)

        if user_id in self.subscriptions:
            self.subscriptions[user_id]["status"] = SubscriptionStatus.BLOCKED
            self.subscriptions[user_id]["block_reason"] = reason
            self.subscriptions[user_id]["blocked_at"] = datetime.now().isoformat()
            self._save_subscriptions()

    def unblock_user(self, user_id: int):
        """Foydalanuvchini blokdan chiqarish"""
        user_id = str(user_id)

        if user_id in self.subscriptions:
            # Avvalgi statusni tiklash
            now = datetime.now()
            user_data = self.subscriptions[user_id]

            if user_data.get("subscription_end"):
                sub_end = datetime.fromisoformat(user_data["subscription_end"])
                if now < sub_end:
                    user_data["status"] = SubscriptionStatus.ACTIVE
                else:
                    user_data["status"] = SubscriptionStatus.EXPIRED
            else:
                user_data["status"] = SubscriptionStatus.EXPIRED

            self._save_subscriptions()

    def get_all_active_users(self) -> list:
        """Barcha faol foydalanuvchilarni olish"""
        active_users = []

        for user_id, user_data in self.subscriptions.items():
            access = self.check_access(int(user_id))
            if access["has_access"]:
                active_users.append(user_data)

        return active_users

    def get_statistics(self) -> Dict[str, Any]:
        """Obuna statistikasi"""
        stats = {
            "total_users": len(self.subscriptions),
            "free_trial": 0,
            "active_premium": 0,
            "expired": 0,
            "blocked": 0,
            "total_revenue": 0,
            "monthly_revenue": 0
        }

        now = datetime.now()
        month_ago = now - timedelta(days=30)

        for user_data in self.subscriptions.values():
            # Status bo'yicha hisoblash
            status = user_data["status"]
            if status == SubscriptionStatus.FREE_TRIAL:
                stats["free_trial"] += 1
            elif status == SubscriptionStatus.ACTIVE:
                stats["active_premium"] += 1
            elif status == SubscriptionStatus.EXPIRED:
                stats["expired"] += 1
            elif status == SubscriptionStatus.BLOCKED:
                stats["blocked"] += 1

            # Daromad hisoblash
            stats["total_revenue"] += user_data.get("total_paid", 0)

            # Oylik daromad
            for payment in user_data.get("payments", []):
                paid_at = datetime.fromisoformat(payment["paid_at"])
                if paid_at >= month_ago:
                    stats["monthly_revenue"] += payment["amount"]

        return stats


# Singleton instance
subscription_manager = SubscriptionManager()


def check_user_access(user_id: int) -> bool:
    """
    Quick access check - target guruhga xabar yuborishdan oldin chaqirish

    Usage:
        if check_user_access(user_id):
            # Xabar yuborish
        else:
            # Ruxsat yo'q
    """
    result = subscription_manager.check_access(user_id)
    return result["has_access"]


def get_subscription_message(user_id: int) -> str:
    """
    Obuna haqida xabar olish

    Usage:
        message = get_subscription_message(user_id)
        await bot.send_message(user_id, message)
    """
    result = subscription_manager.check_access(user_id)

    if result["has_access"]:
        return (
            f"✅ <b>Sizning obunangiz faol</b>\n\n"
            f"📊 Status: {result['message']}\n"
            f"📅 Qolgan kunlar: {result['expires_in_days']}\n\n"
            f"💡 Barcha xizmatlardan foydalanishingiz mumkin!"
        )
    else:
        monthly_price = subscription_manager.settings["monthly_price"]

        return (
            f"⏰ <b>Obunangiz tugagan</b>\n\n"
            f"💰 Oylik narx: {monthly_price:,} so'm\n\n"
            f"📝 Obunani yangilash uchun to'lov qiling:\n"
            f"• Click\n"
            f"• Payme\n"
            f"• Stripe\n\n"
            f"📞 Yordam uchun: @admin"
        )
