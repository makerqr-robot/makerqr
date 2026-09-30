#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
شرطینو - ربات شرط‌بندی فارسی
نسخه نهایی با بهینه‌سازی سرعت
"""

import os
import json
import random
import string
import gc
import asyncio
import threading
from datetime import datetime
from threading import Thread
from flask import Flask, jsonify

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ======================== SETTINGS ========================
TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_IDS = [int(id.strip()) for id in os.environ.get("ADMIN_IDS", "123456789").split(",") if id.strip()]
SUPPORT = "@shartinosup"
TRX_WALLET = os.environ.get("TRX_WALLET", "TEv9t55am7zcCi2Z7dUXtFfKQmofeN7e1r")
USDT_WALLET = os.environ.get("USDT_WALLET", "TEVuvWZ68UbDUdzpd6EqxncsqDVjwyY7cj")

BOT_USERNAME = "shartino_robot"
CHANNELS_ENV = os.environ.get("CHANNELS", "@shartino,@rezayat_shartino")

MIN_BET = 10000
GIFT_AMOUNT = 100000
REFERRAL_GIFT = 250000
MIN_WITHDRAW = 500000
MIN_DEPOSIT = 500000
COMMISSION_PERCENT = 30
BET_COMMISSION_PERCENT = 10
INITIAL_BALANCE = 0
INACTIVE_BONUS = 50000
INACTIVE_HOURS = 24

BOT_NAME = "شرطینو"
CURRENCY = "تومان"

# ======================== WEB SERVER ========================
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return jsonify({"status": "running", "bot": "shartino"})

@flask_app.route("/health")
def health():
    return jsonify({"status": "ok"})

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# ======================== DATABASE ========================
DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

DATA_FILE = os.path.join(DATA_DIR, "users.json")
ADMIN_CONFIG_FILE = os.path.join(DATA_DIR, "admin_config.json")

def load_json(file_path, default=None):
    if default is None:
        default = {}
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return default
    return default

def save_json(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# ✅ کش کردن دیتابیس در حافظه
users = load_json(DATA_FILE)
admin_config = load_json(ADMIN_CONFIG_FILE, {})

# ✅ تنظیمات پیش‌فرض
if "channels" not in admin_config or not admin_config["channels"]:
    admin_config["channels"] = [{"link": ch.strip(), "enabled": True} for ch in CHANNELS_ENV.split(",") if ch.strip()]
if "trx_wallet" not in admin_config:
    admin_config["trx_wallet"] = TRX_WALLET
if "usdt_wallet" not in admin_config:
    admin_config["usdt_wallet"] = USDT_WALLET
if "support" not in admin_config:
    admin_config["support"] = SUPPORT
if "min_bet" not in admin_config:
    admin_config["min_bet"] = MIN_BET
if "min_deposit" not in admin_config:
    admin_config["min_deposit"] = MIN_DEPOSIT
if "min_withdraw" not in admin_config:
    admin_config["min_withdraw"] = MIN_WITHDRAW
if "gift_amount" not in admin_config:
    admin_config["gift_amount"] = GIFT_AMOUNT
if "referral_gift" not in admin_config:
    admin_config["referral_gift"] = REFERRAL_GIFT
if "commission_percent" not in admin_config:
    admin_config["commission_percent"] = COMMISSION_PERCENT
if "bet_commission_percent" not in admin_config:
    admin_config["bet_commission_percent"] = BET_COMMISSION_PERCENT
if "bot_enabled" not in admin_config:
    admin_config["bot_enabled"] = True
if "games" not in admin_config:
    admin_config["games"] = {"dice": True, "coin": True, "slot": True, "football": True}
if "slot_coeffs" not in admin_config:
    admin_config["slot_coeffs"] = {
        "💎💎💎": 100, "⭐⭐⭐": 50, "777": 20,
        "🍇🍇🍇": 15, "🍋🍋🍋": 10, "🍒🍒🍒": 5, "two_same": 2
    }
if "cards" not in admin_config:
    admin_config["cards"] = []

# ======================== HELPER FUNCTIONS ========================
def format_number(num):
    return f"{num:,}"

def normalize_channel_link(link):
    if not link:
        return link
    link = link.strip()
    if link.startswith("https://t.me/"):
        link = link.replace("https://t.me/", "")
        return "@" + link
    if link.startswith("t.me/"):
        link = link.replace("t.me/", "")
        return "@" + link
    if link.startswith("@"):
        return link
    if link.startswith("-"):
        return link
    return "@" + link

def get_user(user_id):
    uid = str(user_id)
    if uid not in users:
        users[uid] = {
            "balance": INITIAL_BALANCE,
            "username": None,
            "free_gift_used": False,
            "intro_seen": False,
            "referral_code": generate_referral_code(),
            "referred_by": None,
            "referrer_id": None,
            "referrer_username": None,
            "joined_via_link": False,
            "referral_count": 0,
            "referral_gift": 0,
            "referral_commission": 0,
            "commission_percent": COMMISSION_PERCENT,
            "banned": False,
            "total_bets": 0,
            "total_wins": 0,
            "total_losses": 0,
            "total_bet_amount": 0,
            "total_win_amount": 0,
            "best_streak": 0,
            "current_streak": 0,
            "has_deposited": False,
            "total_deposit": 0,
            "total_withdraw": 0,
            "transactions": [],
            "created_at": str(datetime.now()),
            "last_activity": str(datetime.now()),
            "inactive_warning_sent": False
        }
    return users[uid]

def save_user(user_id, data):
    users[str(user_id)] = data

def generate_referral_code():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=8))

def add_transaction(user_id, amount, trans_type, description=""):
    user = get_user(user_id)
    user["transactions"].append({
        "date": datetime.now().strftime("%Y/%m/%d - %H:%M"),
        "type": trans_type,
        "amount": amount,
        "balance_after": user["balance"],
        "description": description
    })
    if len(user["transactions"]) > 50:
        user["transactions"] = user["transactions"][-50:]

def update_last_activity(user_id):
    user = get_user(user_id)
    user["last_activity"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user["inactive_warning_sent"] = False

def update_streak(user_id, is_win):
    user = get_user(user_id)
    if is_win:
        user["current_streak"] = user.get("current_streak", 0) + 1
        if user["current_streak"] > user.get("best_streak", 0):
            user["best_streak"] = user["current_streak"]
    else:
        user["current_streak"] = 0

def add_bet_commission_to_referrer(user_id, win_amount):
    user = get_user(user_id)
    referrer_id = user.get("referrer_id")
    if not referrer_id:
        return 0
    commission_percent = admin_config.get("bet_commission_percent", BET_COMMISSION_PERCENT)
    commission = int(win_amount * (commission_percent / 100))
    if commission <= 0:
        return 0
    referrer = get_user(referrer_id)
    referrer["balance"] += commission
    referrer["referral_commission"] = referrer.get("referral_commission", 0) + commission
    add_transaction(referrer_id, commission, "bet_commission", f"پورسانت {commission_percent}٪ از برد زیرمجموعه")
    save_user(referrer_id, referrer)
    return commission

# ======================== PERIODIC SAVE ========================
def periodic_save():
    try:
        save_json(DATA_FILE, users)
        save_json(ADMIN_CONFIG_FILE, admin_config)
    except:
        pass
    finally:
        threading.Timer(300, periodic_save).start()

# ======================== INTRO PAGE ========================
async def intro_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پیام معرفی ربات برای کاربر جدید"""
    user_id = update.effective_user.id
    user = get_user(user_id)
    support = admin_config.get("support", SUPPORT)
    
    keyboard = [
        [InlineKeyboardButton("✅ متوجه شدم، ادامه", callback_data="intro_done")]
    ]
    
    text = f"""🎰 <b>به شرطینو خوش آمدید!</b>


🎮 شرطینو یک ربات شرط‌بندی و سرگرمی آنلاین است.

<b>💡 چطور کار می‌کند؟</b>

• با انواع بازی مختلف شرط می‌بندید
• برنده می‌شوید و موجودی‌تان افزایش می‌یابد
• موجودی را به ریال برداشت می‌کنید

━━━━━━━━━━━━━
<b>🎁 هدایای شما:</b>
• هدیه عضویت: ۱۰۰,۰۰۰ تومان
• هدیه دعوت از هر دوست: ۲۵۰,۰۰۰ تومان
• پورسانت ۱۰٪ از برد زیرمجموعه

━━━━━━━━━━━━━
🆘 پشتیبانی: {support}

👇 برای شروع، روی دکمه زیر کلیک کنید:"""
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def intro_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بعد از کلیک روی متوجه شدم"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)
    user["intro_seen"] = True
    save_user(user_id, user)
    await show_channels_page(update, context, user_id)

# ======================== CHANNELS PAGE ========================
async def show_channels_page(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """صفحه عضویت در کانال‌ها"""
    user = get_user(user_id)
    channels = admin_config.get("channels", [])
    enabled_channels = [c for c in channels if c.get("enabled", True)]
    channel_count = len(enabled_channels)
    support = admin_config.get("support", SUPPORT)
    gift_amount = admin_config.get("gift_amount", GIFT_AMOUNT)
    
    keyboard = []
    for i, channel in enumerate(enabled_channels, 1):
        link = channel["link"]
        if not link.startswith("http"):
            link = f"https://t.me/{link[1:]}"
        label = f"📢 عضویت در کانال {i}" if channel_count > 1 else "📢 عضویت در کانال"
        keyboard.append([InlineKeyboardButton(label, url=link)])
    keyboard.append([InlineKeyboardButton("✅ عضو شدم", callback_data="check_gift")])
    
    channels_text = "\n".join([f"{i+1}️⃣ {c['link']}" for i, c in enumerate(enabled_channels)])
    
    text = f"""🎁 برای دریافت {format_number(gift_amount)} {CURRENCY} شارژ هدیه، ابتدا در کانال‌های زیر عضو شوید:

━━━━━━━━━━━━━━━━━━━━━━
📌 <b>کانال‌های مورد نیاز:</b>

{channels_text}

━━━━━━━━━━━━━━━━━━━━━━
پس از عضویت در همه کانال‌ها، روی دکمه «✅ عضو شدم» کلیک کنید.

🆘 پشتیبانی: {support}"""
    
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        except:
            await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

# ======================== CHECK MEMBERSHIP ========================
async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    channels = admin_config.get("channels", [])
    enabled_channels = [c for c in channels if c.get("enabled", True)]
    if not enabled_channels:
        return True
    
    not_joined = []
    for channel in enabled_channels:
        channel_id = normalize_channel_link(channel["link"])
        try:
            member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                not_joined.append(channel)
        except:
            not_joined.append(channel)
    
    if not not_joined:
        return True
    
    keyboard = []
    for i, ch in enumerate(not_joined, 1):
        link = ch["link"]
        if not link.startswith("http"):
            link = f"https://t.me/{link[1:]}"
        label = f"📢 عضویت در کانال {i}" if len(not_joined) > 1 else "📢 عضویت در کانال"
        keyboard.append([InlineKeyboardButton(label, url=link)])
    keyboard.append([InlineKeyboardButton("✅ عضو شدم", callback_data="check_join")])
    
    channels_text = "\n".join([f"{i+1}️⃣ {ch['link']}" for i, ch in enumerate(not_joined)])
    text = f"""⚠️ <b>شما از کانال(های) زیر خارج شده‌اید!</b>

برای ادامه استفاده از ربات، لطفاً در کانال(های) زیر عضو شوید:

{channels_text}

پس از عضویت، روی دکمه «✅ عضو شدم» کلیک کنید."""
    
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        except:
            await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    return False

async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    channels = admin_config.get("channels", [])
    enabled_channels = [c for c in channels if c.get("enabled", True)]
    not_joined = []
    for channel in enabled_channels:
        channel_id = normalize_channel_link(channel["link"])
        try:
            member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                not_joined.append(channel)
        except:
            not_joined.append(channel)
    
    if not_joined:
        keyboard = []
        for i, ch in enumerate(not_joined, 1):
            link = ch["link"]
            if not link.startswith("http"):
                link = f"https://t.me/{link[1:]}"
            label = f"📢 عضویت در کانال {i}" if len(not_joined) > 1 else "📢 عضویت در کانال"
            keyboard.append([InlineKeyboardButton(label, url=link)])
        keyboard.append([InlineKeyboardButton("✅ عضو شدم", callback_data="check_join")])
        channels_text = "\n".join([f"{i+1}️⃣ {ch['link']}" for i, ch in enumerate(not_joined)])
        await query.edit_message_text(
            f"""❌ <b>هنوز در همه کانال‌ها عضو نشده‌اید!</b>

لطفاً در کانال(های) زیر عضو شوید:

{channels_text}

پس از عضویت، دوباره روی «✅ عضو شدم» کلیک کنید.""",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return
    
    await show_main_menu(update, context, user_id)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    user = get_user(user_id)
    support = admin_config.get("support", SUPPORT)
    referral_gift = admin_config.get("referral_gift", REFERRAL_GIFT)
    bet_commission = admin_config.get("bet_commission_percent", BET_COMMISSION_PERCENT)
    
    keyboard = [
        [InlineKeyboardButton("🎲 شروع بازی", callback_data="game_menu")],
        [InlineKeyboardButton("👤 حساب من", callback_data="my_account")],
        [InlineKeyboardButton("💰 کسب درآمد", callback_data="earnings")],
        [InlineKeyboardButton("❓ چطور اعتماد کنم", callback_data="trust")]
    ]
    
    text = f"""🎰 <b>شرطینو</b>

👤 کاربر: @{user['username'] or 'کاربر'}
💰 موجودی: {format_number(user['balance'])} {CURRENCY}

✅ با ریال می‌تونی برداشت کنی
👥 با دعوت هر دوست {format_number(referral_gift)} {CURRENCY} هدیه
🎰 از هر برد زیرمجموعه {bet_commission}٪ پورسانت

🆘 پشتیبانی: {support}

از منوی زیر انتخاب کنید:"""
    
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        except:
            await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

# ======================== MAIN MENU ========================
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    update_last_activity(user_id)
    if not await check_membership(update, context, user_id):
        return
    await show_main_menu(update, context, user_id)

# ======================== START ========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    user = get_user(user_id)
    user["username"] = username
    update_last_activity(user_id)
    save_user(user_id, user)
    
    if context.args and context.args[0].startswith("ref_"):
        ref_code = context.args[0][4:]
        for uid, data in users.items():
            if data.get("referral_code") == ref_code and int(uid) != user_id:
                user["referred_by"] = ref_code
                user["referrer_id"] = int(uid)
                user["referrer_username"] = data.get("username", "کاربر")
                user["joined_via_link"] = True
                save_user(user_id, user)
                break
    
    # ✅ اگر کاربر جدید است، پیام معرفی را نشان بده
    if not user.get("intro_seen", False):
        await intro_page(update, context)
        return
    
    # اگر قبلاً هدیه گرفته، منوی اصلی
    if user.get("free_gift_used", False):
        await show_main_menu(update, context, user_id)
        return
    
    # اگر تازه وارد شده، صفحه عضویت
    await show_channels_page(update, context, user_id)

async def check_gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)
    update_last_activity(user_id)
    
    channels = admin_config.get("channels", [])
    enabled_channels = [c for c in channels if c.get("enabled", True)]
    all_member = True
    for channel in enabled_channels:
        channel_id = normalize_channel_link(channel["link"])
        try:
            member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                all_member = False
                break
        except:
            all_member = False
            break
    
    if all_member:
        gift_amount = admin_config.get("gift_amount", GIFT_AMOUNT)
        user["free_gift_used"] = True
        user["balance"] += gift_amount
        add_transaction(user_id, gift_amount, "gift", f"شارژ هدیه عضویت در کانال {format_number(gift_amount)} {CURRENCY}")
        save_user(user_id, user)
        save_json(DATA_FILE, users)
        
        referrer_id = user.get("referrer_id")
        if referrer_id:
            referrer = get_user(referrer_id)
            referral_gift = admin_config.get("referral_gift", REFERRAL_GIFT)
            referrer["balance"] += referral_gift
            referrer["referral_count"] = referrer.get("referral_count", 0) + 1
            referrer["referral_gift"] = referrer.get("referral_gift", 0) + referral_gift
            add_transaction(referrer_id, referral_gift, "referral_gift", f"هدیه دعوت {format_number(referral_gift)} {CURRENCY}")
            save_user(referrer_id, referrer)
        
        text = f"""✅ <b>تبریک! عضویت شما تأیید شد.</b>

🎁 {format_number(gift_amount)} {CURRENCY} شارژ هدیه به حساب شما اضافه شد.
💰 موجودی جدید: {format_number(user['balance'])} {CURRENCY}

━━━━━━━━━━━━━━━━━━━━━━
🎰 <b>قابلیت جدید: پورسانت از برد زیرمجموعه!</b>

از این به بعد، هر دوستی که دعوت کنی و برنده بشه،
<b>۱۰٪ از جایزه‌اش</b> به حساب تو اضافه می‌شه! 💰

👥 لینک دعوت اختصاصی خودت رو از بخش
«💰 کسب درآمد» بگیر."""
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 شروع بازی", callback_data="game_menu")],
            [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
        ]), parse_mode="HTML")
    else:
        keyboard = []
        for i, channel in enumerate(enabled_channels, 1):
            link = channel["link"]
            if not link.startswith("http"):
                link = f"https://t.me/{link[1:]}"
            label = f"📢 عضویت در کانال {i}" if len(enabled_channels) > 1 else "📢 عضویت در کانال"
            keyboard.append([InlineKeyboardButton(label, url=link)])
        keyboard.append([InlineKeyboardButton("✅ عضو شدم", callback_data="check_gift")])
        
        await query.edit_message_text(
            "❌ شما هنوز در همه کانال‌ها عضو نشده‌اید!\n\nلطفاً ابتدا در همه کانال‌های بالا عضو شوید، سپس دوباره روی «عضو شدم» کلیک کنید.",
            reply_markup=InlineKeyboardMarkup(keyboard))

# ======================== EARNINGS ========================
async def earnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    update_last_activity(user_id)
    if not await check_membership(update, context, user_id):
        return
    
    user = get_user(user_id)
    support = admin_config.get("support", SUPPORT)
    referral_gift = admin_config.get("referral_gift", REFERRAL_GIFT)
    bet_commission = admin_config.get("bet_commission_percent", BET_COMMISSION_PERCENT)
    link = f"https://t.me/{BOT_USERNAME}?start=ref_{user['referral_code']}"
    
    text = f"""💰 <b>کسب درآمد</b>

━━━━━━━━━━━━━━━━━━━━━━
🔗 <b>لینک دعوت اختصاصی شما:</b>

<code>{link}</code>

📋 روی لینک بالا کلیک کنید تا کپی شود.

━━━━━━━━━━━━━━━━━━━━━━
🎁 <b>دعوت از دوستان و دریافت جایزه:</b>

👤 به ازای هر دوست = {format_number(referral_gift)} {CURRENCY} هدیه

━━━━━━━━━━━━━━━━━━━━━━
🎰 <b>پورسانت از برد زیرمجموعه:</b>

از هر برد زیرمجموعه شما، {bet_commission}٪ پورسانت به حساب شما اضافه می‌شود.

━━━━━━━━━━━━━━━━━━━━━━
📊 <b>آمار شما:</b>

👥 تعداد دعوت‌ها: {user.get('referral_count', 0)}
💰 هدیه دعوت: {format_number(user.get('referral_gift', 0))} {CURRENCY}
💸 کمیسیون: {format_number(user.get('referral_commission', 0))} {CURRENCY}

🆘 پشتیبانی: {support}"""
    
    keyboard = [
        [InlineKeyboardButton("🔗 کپی لینک دعوت", url=f"https://t.me/share/url?url={link}")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

# ======================== GAMES MENU ========================
async def game_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    update_last_activity(user_id)
    if not await check_membership(update, context, user_id):
        return
    
    games = admin_config.get("games", {})
    keyboard = []
    if games.get("dice", True):
        keyboard.append([InlineKeyboardButton("🎲 تاس", callback_data="dice_game")])
    if games.get("coin", True):
        keyboard.append([InlineKeyboardButton("🪙 شیر یا خط", callback_data="coin_game")])
    if games.get("slot", True):
        keyboard.append([InlineKeyboardButton("🎰 اسلات", callback_data="slot_game")])
    if games.get("football", True):
        keyboard.append([InlineKeyboardButton("⚽ فوتبال", callback_data="football_game")])
    keyboard.append([InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")])
    
    await query.edit_message_text("<b>🎮 بازی‌های شرطینو</b>\n\nلطفاً یک بازی را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

# ======================== DICE GAME ========================
async def dice_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)
    update_last_activity(user_id)
    if not await check_membership(update, context, user_id):
        return
    
    keyboard = [
        [InlineKeyboardButton("۱۰,۰۰۰", callback_data="dice_bet_10000"), InlineKeyboardButton("۲۰,۰۰۰", callback_data="dice_bet_20000")],
        [InlineKeyboardButton("۵۰,۰۰۰", callback_data="dice_bet_50000"), InlineKeyboardButton("۱۰۰,۰۰۰", callback_data="dice_bet_100000")],
        [InlineKeyboardButton("۲۰۰,۰۰۰", callback_data="dice_bet_200000"), InlineKeyboardButton("۵۰۰,۰۰۰", callback_data="dice_bet_500000")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
    ]
    text = f"""<b>🎲 بازی تاس</b>

💰 موجودی شما: {format_number(user['balance'])} {CURRENCY}
📌 مبلغ شرط را انتخاب کنید:"""
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def dice_bet_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)
    update_last_activity(user_id)
    if not await check_membership(update, context, user_id):
        return
    
    amount = int(query.data.split("_")[2])
    if amount > user["balance"]:
        await query.edit_message_text(
            f"""❌ موجودی شما کافی نیست!

💰 موجودی شما: {format_number(user['balance'])} {CURRENCY}
🎯 مبلغ شرط: {format_number(amount)} {CURRENCY}""",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 انتخاب مبلغ", callback_data="dice_game")],
                [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
            ]), parse_mode="HTML")
        return
    
    context.user_data["dice_amount"] = amount
    keyboard = [
        [InlineKeyboardButton("🎯 زوج | ضریب ۲", callback_data="dice_coef_even")],
        [InlineKeyboardButton("🎯 فرد | ضریب ۲", callback_data="dice_coef_odd")],
        [InlineKeyboardButton("🎯 مجموع ۱۰ یا بیشتر | ضریب ۳", callback_data="dice_coef_high")],
        [InlineKeyboardButton("🎯 هر ۲ تاس یکسان | ضریب ۵", callback_data="dice_coef_same")],
        [InlineKeyboardButton("🔙 انصراف", callback_data="main_menu")]
    ]
    text = f"""<b>🎲 انتخاب ضریب</b>

💰 مبلغ شرط: {format_number(amount)} {CURRENCY}

<b>📌 یکی از ضرایب زیر را انتخاب کنید:</b>

• زوج: مجموع ۲ تاس زوج باشد (ضریب ۲)
• فرد: مجموع ۲ تاس فرد باشد (ضریب ۲)
• مجموع ۱۰ یا بیشتر: مجموع ۲ تاس ۱۰ یا بیشتر باشد (ضریب ۳)
• هر ۲ تاس یکسان: هر ۲ تاس یک عدد باشند (ضریب ۵)"""
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def dice_coef_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)
    update_last_activity(user_id)
    if not await check_membership(update, context, user_id):
        return
    
    bet_amount = context.user_data.get("dice_amount", 0)
    if bet_amount == 0:
        await query.edit_message_text("❌ خطا! لطفاً دوباره از ابتدا شروع کنید.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازی تاس", callback_data="dice_game")],
            [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
        ]))
        return
    
    choice = query.data.split("_")[2]
    context.user_data["dice_choice"] = choice
    text = f"""<b>🎲 در حال انداختن تاس...</b>

💰 مبلغ شرط: {format_number(bet_amount)} {CURRENCY}
🎯 انتخاب شما: {choice}

⏳ لطفاً صبر کنید..."""
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 انداختن تاس‌ها", callback_data="dice_roll")]
    ]), parse_mode="HTML")

async def dice_roll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)
    update_last_activity(user_id)
    if not await check_membership(update, context, user_id):
        return
    
    bet_amount = context.user_data.get("dice_amount", 0)
    choice = context.user_data.get("dice_choice", "")
    if bet_amount == 0 or choice == "":
        await query.edit_message_text("❌ خطا! لطفاً دوباره از ابتدا شروع کنید.")
        return
    
    await query.edit_message_text("🎲 در حال انداختن تاس...")
    dice1 = await query.message.reply_dice(emoji="🎲")
    dice2 = await query.message.reply_dice(emoji="🎲")
    value1 = dice1.dice.value
    value2 = dice2.dice.value
    total = value1 + value2
    
    is_win = False
    coefficient = 0
    win_description = ""
    if choice == "even":
        coefficient = 2
        is_win = (total % 2 == 0)
        win_description = f"مجموع {total} زوج است"
    elif choice == "odd":
        coefficient = 2
        is_win = (total % 2 == 1)
        win_description = f"مجموع {total} فرد است"
    elif choice == "high":
        coefficient = 3
        is_win = (total >= 10)
        win_description = f"مجموع {total} (۱۰ یا بیشتر)"
    elif choice == "same":
        coefficient = 5
        is_win = (value1 == value2)
        win_description = f"هر ۲ تاس یکسان! ({value1} و {value2})"
    else:
        coefficient = 0
        is_win = False
    
    choice_names = {"even": "زوج", "odd": "فرد", "high": "مجموع ۱۰ یا بیشتر", "same": "هر ۲ تاس یکسان"}
    choice_name = choice_names.get(choice, choice)
    
    if is_win:
        win_amount = bet_amount * coefficient
        user["balance"] += win_amount
        user["total_wins"] = user.get("total_wins", 0) + 1
        user["total_win_amount"] = user.get("total_win_amount", 0) + win_amount
        update_streak(user_id, True)
        add_bet_commission_to_referrer(user_id, win_amount)
        result_text = f"""<b>🎉 تبریک! شما برنده شدید!</b>

<b>🎲 نتایج تاس‌ها:</b>
تاس ۱: {value1} | تاس ۲: {value2}
📊 مجموع: {total}
🎯 انتخاب شما: {choice_name}
✅ نتیجه: {win_description}
📊 ضریب: {coefficient}×
💰 مبلغ شرط: {format_number(bet_amount)} {CURRENCY}
🏆 جایزه: {format_number(win_amount)} {CURRENCY}

💰 موجودی جدید: {format_number(user['balance'])} {CURRENCY}"""
        add_transaction(user_id, win_amount, "win", f"برد در تاس - {choice_name}")
    else:
        user["balance"] -= bet_amount
        user["total_losses"] = user.get("total_losses", 0) + 1
        user["total_bet_amount"] = user.get("total_bet_amount", 0) + bet_amount
        update_streak(user_id, False)
        result_text = f"""<b>😔 متاسفم... شما باختید.</b>

<b>🎲 نتایج تاس‌ها:</b>
تاس ۱: {value1} | تاس ۲: {value2}
📊 مجموع: {total}
🎯 انتخاب شما: {choice_name}
💰 مبلغ شرط: {format_number(bet_amount)} {CURRENCY}

💰 موجودی جدید: {format_number(user['balance'])} {CURRENCY}"""
        add_transaction(user_id, -bet_amount, "bet", f"باخت در تاس - {choice_name}")
    
    user["total_bets"] = user.get("total_bets", 0) + 1
    save_user(user_id, user)
    save_json(DATA_FILE, users)
    context.user_data["dice_amount"] = 0
    context.user_data["dice_choice"] = ""
    
    await query.message.reply_text(result_text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 دوباره", callback_data="dice_game")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
    ]), parse_mode="HTML")

# ======================== COIN GAME ========================
async def coin_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)
    update_last_activity(user_id)
    if not await check_membership(update, context, user_id):
        return
    
    keyboard = [
        [InlineKeyboardButton("۱۰,۰۰۰", callback_data="coin_bet_10000"), InlineKeyboardButton("۲۰,۰۰۰", callback_data="coin_bet_20000")],
        [InlineKeyboardButton("۵۰,۰۰۰", callback_data="coin_bet_50000"), InlineKeyboardButton("۱۰۰,۰۰۰", callback_data="coin_bet_100000")],
        [InlineKeyboardButton("۲۰۰,۰۰۰", callback_data="coin_bet_200000"), InlineKeyboardButton("۵۰۰,۰۰۰", callback_data="coin_bet_500000")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
    ]
    text = f"""<b>🪙 شیر یا خط</b>

💰 موجودی شما: {format_number(user['balance'])} {CURRENCY}
📊 ضریب: ۲.۵

📌 مبلغ شرط را انتخاب کنید:"""
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def coin_bet_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)
    update_last_activity(user_id)
    if not await check_membership(update, context, user_id):
        return
    
    amount = int(query.data.split("_")[2])
    if amount > user["balance"]:
        await query.edit_message_text(
            f"""❌ موجودی شما کافی نیست!

💰 موجودی شما: {format_number(user['balance'])} {CURRENCY}
🎯 مبلغ شرط: {format_number(amount)} {CURRENCY}""",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 انتخاب مبلغ", callback_data="coin_game")],
                [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
            ]), parse_mode="HTML")
        return
    
    context.user_data["coin_amount"] = amount
    keyboard = [
        [InlineKeyboardButton("🦁 شیر", callback_data="coin_predict_heads")],
        [InlineKeyboardButton("📍 خط", callback_data="coin_predict_tails")],
        [InlineKeyboardButton("🔙 انصراف", callback_data="main_menu")]
    ]
    text = f"""<b>🪙 انتخاب شیر یا خط</b>

💰 مبلغ شرط: {format_number(amount)} {CURRENCY}
📊 ضریب: ۲.۵

📌 عدد زوج = شیر 🦁 | عدد فرد = خط 📍

لطفاً انتخاب کنید:"""
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def coin_predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)
    update_last_activity(user_id)
    if not await check_membership(update, context, user_id):
        return
    
    bet_amount = context.user_data.get("coin_amount", 0)
    if bet_amount == 0:
        await query.edit_message_text("❌ خطا! لطفاً دوباره از ابتدا شروع کنید.")
        return
    
    choice = query.data.split("_")[2]
    await query.edit_message_text("🪙 در حال پرتاب سکه...")
    dice_message = await query.message.reply_dice(emoji="🎲")
    dice_value = dice_message.dice.value
    is_heads = dice_value in [2, 4, 6]
    result_name = "شیر 🦁" if is_heads else "خط 📍"
    is_win = (choice == "heads" and is_heads) or (choice == "tails" and not is_heads)
    
    if is_win:
        win_amount = int(bet_amount * 2.5)
        user["balance"] += win_amount
        user["total_wins"] = user.get("total_wins", 0) + 1
        user["total_win_amount"] = user.get("total_win_amount", 0) + win_amount
        update_streak(user_id, True)
        add_bet_commission_to_referrer(user_id, win_amount)
        result_text = f"""<b>🎉 تبریک! شما برنده شدید!</b>

🪙 نتیجه سکه: {result_name}
🎲 عدد تاس: {dice_value} ({'زوج' if is_heads else 'فرد'})
💰 مبلغ شرط: {format_number(bet_amount)} {CURRENCY}
📊 ضریب: ۲.۵
🏆 جایزه: {format_number(win_amount)} {CURRENCY}

💰 موجودی جدید: {format_number(user['balance'])} {CURRENCY}"""
        add_transaction(user_id, win_amount, "win", "برد در شیر یا خط")
    else:
        user["balance"] -= bet_amount
        user["total_losses"] = user.get("total_losses", 0) + 1
        user["total_bet_amount"] = user.get("total_bet_amount", 0) + bet_amount
        update_streak(user_id, False)
        result_text = f"""<b>😔 متاسفم... شما باختید.</b>

🪙 نتیجه سکه: {result_name}
🎲 عدد تاس: {dice_value} ({'زوج' if is_heads else 'فرد'})
💰 مبلغ شرط: {format_number(bet_amount)} {CURRENCY}

💰 موجودی جدید: {format_number(user['balance'])} {CURRENCY}"""
        add_transaction(user_id, -bet_amount, "bet", "باخت در شیر یا خط")
    
    user["total_bets"] = user.get("total_bets", 0) + 1
    save_user(user_id, user)
    save_json(DATA_FILE, users)
    context.user_data["coin_amount"] = 0
    
    await query.message.reply_text(result_text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🪙 دوباره", callback_data="coin_game")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
    ]), parse_mode="HTML")

# ======================== SLOT GAME ========================
async def slot_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)
    update_last_activity(user_id)
    if not await check_membership(update, context, user_id):
        return
    
    keyboard = [
        [InlineKeyboardButton("۱۰,۰۰۰", callback_data="slot_bet_10000"), InlineKeyboardButton("۲۰,۰۰۰", callback_data="slot_bet_20000")],
        [InlineKeyboardButton("۵۰,۰۰۰", callback_data="slot_bet_50000"), InlineKeyboardButton("۱۰۰,۰۰۰", callback_data="slot_bet_100000")],
        [InlineKeyboardButton("۲۰۰,۰۰۰", callback_data="slot_bet_200000"), InlineKeyboardButton("۵۰۰,۰۰۰", callback_data="slot_bet_500000")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
    ]
    slot_coeffs = admin_config.get("slot_coeffs", {})
    text = f"""<b>🎰 بازی اسلات</b>

💰 موجودی شما: {format_number(user['balance'])} {CURRENCY}
<b>📊 ضرایب:</b>
💎💎💎 = {slot_coeffs.get('💎💎💎', 100)}× | ⭐⭐⭐ = {slot_coeffs.get('⭐⭐⭐', 50)}×
۷۷۷ = {slot_coeffs.get('777', 20)}× | 🍇🍇🍇 = {slot_coeffs.get('🍇🍇🍇', 15)}×
🍋🍋🍋 = {slot_coeffs.get('🍋🍋🍋', 10)}× | 🍒🍒🍒 = {slot_coeffs.get('🍒🍒🍒', 5)}×
۲ تا یکسان = {slot_coeffs.get('two_same', 2)}×

📌 مبلغ شرط را انتخاب کنید:"""
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def slot_bet_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)
    update_last_activity(user_id)
    if not await check_membership(update, context, user_id):
        return
    
    amount = int(query.data.split("_")[2])
    if amount > user["balance"]:
        await query.edit_message_text(
            f"""❌ موجودی شما کافی نیست!

💰 موجودی شما: {format_number(user['balance'])} {CURRENCY}
🎯 مبلغ شرط: {format_number(amount)} {CURRENCY}""",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 انتخاب مبلغ", callback_data="slot_game")],
                [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
            ]), parse_mode="HTML")
        return
    
    context.user_data["slot_amount"] = amount
    text = f"""<b>🎰 اسلات</b>

💰 مبلغ شرط: {format_number(amount)} {CURRENCY}

دکمه زیر را بزنید تا دستگاه اسلات بچرخد:"""
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🎰 چرخش اسلات", callback_data="slot_spin")],
        [InlineKeyboardButton("🔙 انصراف", callback_data="main_menu")]
    ]), parse_mode="HTML")

async def slot_spin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)
    update_last_activity(user_id)
    if not await check_membership(update, context, user_id):
        return
    
    bet_amount = context.user_data.get("slot_amount", 0)
    if bet_amount == 0:
        await query.edit_message_text("❌ خطا! لطفاً دوباره از ابتدا شروع کنید.")
        return
    
    await query.edit_message_text("🎰 در حال چرخش اسلات...")
    dice_message = await query.message.reply_dice(emoji="🎰")
    dice_value = dice_message.dice.value
    slot_emojis = ["🍇", "🍋", "۷", "BAR"]
    result = [
        slot_emojis[(dice_value - 1) // 16 % 4],
        slot_emojis[(dice_value - 1) // 4 % 4],
        slot_emojis[(dice_value - 1) % 4]
    ]
    combo = "".join(result)
    slot_coeffs = admin_config.get("slot_coeffs", {})
    coefficient = slot_coeffs.get(combo, 0)
    if coefficient == 0 and (result[0] == result[1] or result[1] == result[2] or result[0] == result[2]):
        coefficient = slot_coeffs.get("two_same", 2)
    
    if coefficient > 0:
        win_amount = bet_amount * coefficient
        user["balance"] += win_amount
        user["total_wins"] = user.get("total_wins", 0) + 1
        user["total_win_amount"] = user.get("total_win_amount", 0) + win_amount
        update_streak(user_id, True)
        add_bet_commission_to_referrer(user_id, win_amount)
        result_text = f"""<b>🎉 تبریک! شما برنده شدید!</b>

🎰 نتیجه اسلات:
[ {result[0]} ] [ {result[1]} ] [ {result[2]} ]

📊 ترکیب: {combo}
🎯 ضریب: {coefficient}×
💰 مبلغ شرط: {format_number(bet_amount)} {CURRENCY}
🏆 جایزه: {format_number(win_amount)} {CURRENCY}

💰 موجودی جدید: {format_number(user['balance'])} {CURRENCY}"""
        add_transaction(user_id, win_amount, "win", f"برد در اسلات - {combo}")
    else:
        user["balance"] -= bet_amount
        user["total_losses"] = user.get("total_losses", 0) + 1
        user["total_bet_amount"] = user.get("total_bet_amount", 0) + bet_amount
        update_streak(user_id, False)
        result_text = f"""<b>😔 متاسفم... شما باختید.</b>

🎰 نتیجه اسلات:
[ {result[0]} ] [ {result[1]} ] [ {result[2]} ]

📊 ترکیب: {combo}
🎯 ضریب: ۰
💰 مبلغ شرط: {format_number(bet_amount)} {CURRENCY}

💰 موجودی جدید: {format_number(user['balance'])} {CURRENCY}"""
        add_transaction(user_id, -bet_amount, "bet", "باخت در اسلات")
    
    user["total_bets"] = user.get("total_bets", 0) + 1
    save_user(user_id, user)
    save_json(DATA_FILE, users)
    context.user_data["slot_amount"] = 0
    
    await query.message.reply_text(result_text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🎰 دوباره", callback_data="slot_game")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
    ]), parse_mode="HTML")

# ======================== FOOTBALL GAME ========================
async def football_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)
    update_last_activity(user_id)
    if not await check_membership(update, context, user_id):
        return
    
    keyboard = [
        [InlineKeyboardButton("۱۰,۰۰۰", callback_data="football_bet_10000"), InlineKeyboardButton("۲۰,۰۰۰", callback_data="football_bet_20000")],
        [InlineKeyboardButton("۵۰,۰۰۰", callback_data="football_bet_50000"), InlineKeyboardButton("۱۰۰,۰۰۰", callback_data="football_bet_100000")],
        [InlineKeyboardButton("۲۰۰,۰۰۰", callback_data="football_bet_200000"), InlineKeyboardButton("۵۰۰,۰۰۰", callback_data="football_bet_500000")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
    ]
    text = f"""<b>⚽ بازی فوتبال</b>

💰 موجودی شما: {format_number(user['balance'])} {CURRENCY}
📊 ضریب: ۲.۵

📌 مبلغ شرط را انتخاب کنید:"""
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def football_bet_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)
    update_last_activity(user_id)
    if not await check_membership(update, context, user_id):
        return
    
    amount = int(query.data.split("_")[2])
    if amount > user["balance"]:
        await query.edit_message_text(
            f"""❌ موجودی شما کافی نیست!

💰 موجودی شما: {format_number(user['balance'])} {CURRENCY}
🎯 مبلغ شرط: {format_number(amount)} {CURRENCY}""",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 انتخاب مبلغ", callback_data="football_game")],
                [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
            ]), parse_mode="HTML")
        return
    
    context.user_data["football_amount"] = amount
    keyboard = [
        [InlineKeyboardButton("⚽️ گل می‌شود (ضریب ۲.۵)", callback_data="football_predict_goal")],
        [InlineKeyboardButton("❌ گل نمی‌شود (ضریب ۲.۵)", callback_data="football_predict_miss")],
        [InlineKeyboardButton("🔙 انصراف", callback_data="main_menu")]
    ]
    text = f"""<b>⚽ پیش‌بینی فوتبال</b>

💰 مبلغ شرط: {format_number(amount)} {CURRENCY}
📊 ضریب: ۲.۵

توپ به سمت دروازه شوت می‌شود!"""
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def football_predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)
    update_last_activity(user_id)
    if not await check_membership(update, context, user_id):
        return
    
    bet_amount = context.user_data.get("football_amount", 0)
    prediction = query.data.split("_")[2]
    if bet_amount == 0:
        await query.edit_message_text("❌ خطا! لطفاً دوباره از ابتدا شروع کنید.")
        return
    
    await query.edit_message_text("⚽ در حال شوت...")
    dice_message = await query.message.reply_dice(emoji="⚽")
    dice_value = dice_message.dice.value
    is_goal = dice_value >= 4
    result_text = "گل شد ✅" if is_goal else "گل نشد ❌"
    is_win = (prediction == "goal" and is_goal) or (prediction == "miss" and not is_goal)
    
    if is_win:
        win_amount = int(bet_amount * 2.5)
        user["balance"] += win_amount
        user["total_wins"] = user.get("total_wins", 0) + 1
        user["total_win_amount"] = user.get("total_win_amount", 0) + win_amount
        update_streak(user_id, True)
        add_bet_commission_to_referrer(user_id, win_amount)
        result_msg = f"""<b>🎉 تبریک! شما برنده شدید!</b>

⚽ نتیجه شوت: {result_text}
🎯 پیش‌بینی شما: {'گل می‌شود' if prediction == 'goal' else 'گل نمی‌شود'} (درست)
💰 مبلغ شرط: {format_number(bet_amount)} {CURRENCY}
📊 ضریب: ۲.۵
🏆 جایزه: {format_number(win_amount)} {CURRENCY}

💰 موجودی جدید: {format_number(user['balance'])} {CURRENCY}"""
        add_transaction(user_id, win_amount, "win", "برد در فوتبال")
    else:
        user["balance"] -= bet_amount
        user["total_losses"] = user.get("total_losses", 0) + 1
        user["total_bet_amount"] = user.get("total_bet_amount", 0) + bet_amount
        update_streak(user_id, False)
        result_msg = f"""<b>😔 متاسفم... شما باختید.</b>

⚽ نتیجه شوت: {result_text}
🎯 پیش‌بینی شما: {'گل می‌شود' if prediction == 'goal' else 'گل نمی‌شود'}
💰 مبلغ شرط: {format_number(bet_amount)} {CURRENCY}

💰 موجودی جدید: {format_number(user['balance'])} {CURRENCY}"""
        add_transaction(user_id, -bet_amount, "bet", "باخت در فوتبال")
    
    user["total_bets"] = user.get("total_bets", 0) + 1
    save_user(user_id, user)
    save_json(DATA_FILE, users)
    context.user_data["football_amount"] = 0
    
    await query.message.reply_text(result_msg, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("⚽ دوباره", callback_data="football_game")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
    ]), parse_mode="HTML")

# ======================== MY ACCOUNT ========================
async def my_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    update_last_activity(user_id)
    if not await check_membership(update, context, user_id):
        return
    
    user = get_user(user_id)
    total_bets = user.get("total_bets", 0)
    wins = user.get("total_wins", 0)
    losses = user.get("total_losses", 0)
    win_rate = round((wins / total_bets * 100) if total_bets > 0 else 0, 1)
    total_bet_amount = user.get("total_bet_amount", 0)
    total_win_amount = user.get("total_win_amount", 0)
    profit = total_win_amount - total_bet_amount
    
    text = f"""<b>👤 حساب من</b>

🆔 کاربر شماره: {user_id}
👥 دعوت‌های موفق: {user.get('referral_count', 0)}
📊 تعداد پیش‌بینی‌ها: {total_bets} | برد: {wins} | باخت: {losses}
📈 نرخ برد: {win_rate}%
💰 موجودی: {format_number(user['balance'])} {CURRENCY}

<b>📊 آمار پیشرفته</b>
💸 کل مبلغ شرط‌ها: {format_number(total_bet_amount)} {CURRENCY}
💰 کل مبلغ بردها: {format_number(total_win_amount)} {CURRENCY}
📈 سود خالص: {format_number(profit)} {CURRENCY}
🔥 بهترین رکورد متوالی: {user.get('best_streak', 0)} برد
📅 رکورد فعلی: {user.get('current_streak', 0)} برد
💳 کل واریز: {format_number(user.get('total_deposit', 0))} {CURRENCY}
🏦 کل برداشت: {format_number(user.get('total_withdraw', 0))} {CURRENCY}"""
    
    keyboard = [
        [InlineKeyboardButton("💳 واریز وجه", callback_data="deposit")],
        [InlineKeyboardButton("🏦 برداشت موجودی", callback_data="withdraw")],
        [InlineKeyboardButton("📜 تاریخچه تراکنش‌ها", callback_data="transactions")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

# ======================== DEPOSIT ========================
async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)
    update_last_activity(user_id)
    if not await check_membership(update, context, user_id):
        return
    
    trx_wallet = admin_config.get("trx_wallet", TRX_WALLET)
    usdt_wallet = admin_config.get("usdt_wallet", USDT_WALLET)
    support = admin_config.get("support", SUPPORT)
    min_deposit = admin_config.get("min_deposit", MIN_DEPOSIT)
    cards = admin_config.get("cards", [])
    enabled_cards = [c for c in cards if c.get("enabled", True)]
    
    bonus_text = ""
    if not user.get("has_deposited", False):
        bonus_text = "<b>🎁 هدیه واریز اول: ۵۰٪ (تا سقف ۵ میلیون تومان)</b>\n\n"
    
    # بخش کارت‌ها
    if enabled_cards:
        cards_text = ""
        for i, card in enumerate(enabled_cards, 1):
            cards_text += f"""💳 <b>کارت {i}:</b>
شماره کارت: <code>{card['number']}</code>
به نام: {card.get('holder', 'نامشخص')}

"""
    else:
        cards_text = "❌ تا اطلاع ثانوی غیرفعال می‌باشد.\n\n"
    
    text = f"""<b>💳 واریز وجه</b>

💰 حداقل مبلغ واریز: {format_number(min_deposit)} {CURRENCY}

{bonus_text}
━━━━━━━━━━━━━━━━━━━━━━
<b>📌 شماره کارت جهت واریز ریالی:</b>

{cards_text}━━━━━━━━━━━━━━━━━━━━━━
<b>🟣 آدرس ولت ترون (TRX-TRC20):</b>
<code>{trx_wallet}</code>

📋 متن بالا را لمس کنید تا کپی شود

━━━━━━━━━━━━━━━━━━━━━━
<b>🟢 آدرس ولت تتر (USDT-TRC20):</b>
<code>{usdt_wallet}</code>

📋 متن بالا را لمس کنید تا کپی شود

━━━━━━━━━━━━━━━━━━━━━━
<b>📌 نکات مهم:</b>
• حداقل مبلغ واریز: {format_number(min_deposit)} {CURRENCY}
• حتماً از شبکه TRC20 استفاده کنید
• پس از واریز، حتماً اسکرین‌شات را برای ادمین ارسال کنید
• واریزها به صورت دستی تأیید می‌شوند

━━━━━━━━━━━━━━━━━━━━━━
<b>📌 آیدی ادمین برای ارسال اسکرین‌شات:</b>

🆔 {support}

📋 روی آیدی کلیک کنید و اسکرین‌شات را ارسال کنید

🆘 پشتیبانی: {support}"""
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
    ]), parse_mode="HTML")

# ======================== WITHDRAW ========================
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)
    update_last_activity(user_id)
    if not await check_membership(update, context, user_id):
        return
    
    if not user.get("has_deposited", False):
        text = """<b>❌ برداشت غیرمجاز!</b>

شما تاکنون هیچ واریزی به ربات نداشته‌اید.

📌 برداشت تنها پس از اولین واریز امکان‌پذیر است.

برای واریز، از بخش «💳 واریز وجه» اقدام کنید."""
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 واریز وجه", callback_data="deposit")],
            [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
        ]), parse_mode="HTML")
        return
    
    balance = user["balance"]
    min_withdraw = admin_config.get("min_withdraw", MIN_WITHDRAW)
    keyboard = []
    amounts = [500000, 1000000, 2000000, 5000000, 10000000]
    row = []
    for amount in amounts:
        if amount >= min_withdraw and amount <= balance:
            row.append(InlineKeyboardButton(f"{format_number(amount)}", callback_data=f"withdraw_{amount}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
    if row:
        keyboard.append(row)
    
    if not keyboard:
        keyboard.append([InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")])
        text = f"""<b>🏦 برداشت موجودی</b>

💰 موجودی قابل برداشت: {format_number(balance)} {CURRENCY}
📌 حداقل مبلغ برداشت: {format_number(min_withdraw)} {CURRENCY}

❌ موجودی شما برای برداشت کافی نیست!"""
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return
    
    keyboard.append([InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")])
    text = f"""<b>🏦 برداشت موجودی</b>

💰 موجودی قابل برداشت: {format_number(balance)} {CURRENCY}
📌 حداقل مبلغ برداشت: {format_number(min_withdraw)} {CURRENCY}

📌 مبلغ مورد نظر را انتخاب کنید:"""
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def withdraw_amount_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    update_last_activity(user_id)
    if not await check_membership(update, context, user_id):
        return
    
    amount = int(query.data.split("_")[1])
    context.user_data["withdraw_amount"] = amount
    keyboard = [
        [InlineKeyboardButton("💳 شماره کارت", callback_data="withdraw_card")],
        [InlineKeyboardButton("🟣 آدرس ولت (TRX)", callback_data="withdraw_wallet")],
        [InlineKeyboardButton("🔙 انصراف", callback_data="main_menu")]
    ]
    text = f"""✅ مبلغ {format_number(amount)} {CURRENCY} برای برداشت ثبت شد.

لطفاً یکی از روش‌های زیر را انتخاب کنید:"""
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def withdraw_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["withdraw_method"] = "card"
    await query.edit_message_text(
        "<b>💳 برداشت با شماره کارت</b>\n\nلطفاً شماره کارت ۱۶ رقمی خود را وارد کنید:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 انصراف", callback_data="main_menu")]]),
        parse_mode="HTML")

async def withdraw_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["withdraw_method"] = "wallet"
    await query.edit_message_text(
        "<b>🟣 برداشت با آدرس ولت (TRX)</b>\n\nلطفاً آدرس ولت ترون خود را وارد کنید:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 انصراف", callback_data="main_menu")]]),
        parse_mode="HTML")

async def handle_withdraw_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    update_last_activity(user_id)
    info = update.message.text.strip()
    amount = context.user_data.get("withdraw_amount", 0)
    method = context.user_data.get("withdraw_method", "unknown")
    support = admin_config.get("support", SUPPORT)
    
    user["balance"] -= amount
    user["total_withdraw"] = user.get("total_withdraw", 0) + amount
    add_transaction(user_id, -amount, "withdraw", f"برداشت - {method}")
    save_user(user_id, user)
    save_json(DATA_FILE, users)
    
    method_name = "شماره کارت" if method == "card" else "آدرس ولت"
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id,
                f"""<b>🏦 درخواست برداشت جدید</b>

👤 کاربر: @{user['username'] or user_id}
💰 مبلغ: {format_number(amount)} {CURRENCY}
📌 روش: {method_name}
📋 اطلاعات: {info}""", parse_mode="HTML")
        except:
            pass
    
    await update.message.reply_text(
        f"""<b>✅ درخواست برداشت شما ثبت شد!</b>

💰 مبلغ: {format_number(amount)} {CURRENCY}
🕒 درخواست شما در صف پردازش قرار گرفت.
در صورت نیاز به پشتیبانی: {support}""",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]]),
        parse_mode="HTML")

# ======================== TRANSACTIONS ========================
async def transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)
    update_last_activity(user_id)
    if not await check_membership(update, context, user_id):
        return
    
    trans = user.get("transactions", [])[-10:]
    if not trans:
        text = "<b>📜 تاریخچه تراکنش‌ها</b>\n\nهیچ تراکنشی ثبت نشده است."
    else:
        text = "<b>📜 تاریخچه تراکنش‌ها</b>\n\n"
        for t in trans[-10:]:
            emoji = "💰" if t["amount"] > 0 else "💸"
            text += f"{t['date']} | {emoji} {format_number(t['amount'])} {CURRENCY} | موجودی: {format_number(t['balance_after'])}\n"
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 حساب من", callback_data="my_account")]
    ]), parse_mode="HTML")

# ======================== TRUST ========================
async def trust(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    update_last_activity(user_id)
    if not await check_membership(update, context, user_id):
        return
    
    support = admin_config.get("support", SUPPORT)
    gift_amount = admin_config.get("gift_amount", GIFT_AMOUNT)
    referral_gift = admin_config.get("referral_gift", REFERRAL_GIFT)
    
    text = f"""<b>❓ چطور اعتماد کنم</b>

ما درک می‌کنیم که اعتماد کردن به یک سرویس آنلاین ممکن است برای شما چالش‌برانگیز باشد.

به منظور اینکه شما با خیال آسوده شروع به فعالیت کنید، <b>{format_number(gift_amount)} {CURRENCY}</b> موجودی رایگان هنگام عضویت در کانال به شما اهدا می‌کنیم.

همچنین با دعوت از دوستان خود، به ازای هر دوست <b>{format_number(referral_gift)} {CURRENCY}</b> هدیه دریافت می‌کنید.

<b>💳 شفافیت در تراکنش‌ها</b>
تمام تراکنش‌های مالی شما به صورت شفاف و قابل مشاهده است.

<b>⚡ پردازش سریع</b>
درخواست‌های شما در سریع‌ترین زمان ممکن بررسی و پردازش می‌شوند.

<b>🎧 پشتیبانی واقعی</b>
تیم پشتیبانی ما آماده کمک به شما در هر زمان است.

<b>🤝 شفافیت و اعتماد</b>
ما تلاش می‌کنیم همه چیز را واضح، شفاف و قابل درک نگه داریم.

ما متعهد به ارائه تجربه‌ای لذت‌بخش و عادلانه برای تمام کاربران هستیم. ❤️

🆘 پشتیبانی: {support}"""
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
    ]), parse_mode="HTML")

# ======================== ADMIN PANEL ========================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ این دستور فقط برای ادمین است.")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 آمار کل", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 مدیریت کاربران", callback_data="admin_users")],
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings")],
        [InlineKeyboardButton("🔙 بستن", callback_data="admin_close")]
    ]
    await update.message.reply_text("<b>👑 پنل مدیریت شرطینو</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    total = len(users)
    total_balance = sum(u["balance"] for u in users.values())
    banned = sum(1 for u in users.values() if u.get("banned", False))
    text = f"""<b>📊 آمار کل ربات</b>

👥 کل کاربران: {total}
🚫 کاربران مسدود: {banned}
💰 کل موجودی: {format_number(total_balance)} {CURRENCY}"""
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]
    ]), parse_mode="HTML")

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🔍 جستجوی کاربر", callback_data="admin_search")],
        [InlineKeyboardButton("💸 مدیریت موجودی", callback_data="admin_balance")],
        [InlineKeyboardButton("🚫 مسدود کردن کاربر", callback_data="admin_ban")],
        [InlineKeyboardButton("📨 ارسال همگانی", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🎁 شارژ همگانی", callback_data="admin_global_gift")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]
    ]
    await query.edit_message_text("<b>👥 مدیریت کاربران</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def admin_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("📅 تغییر تاریخ واریز ریالی", callback_data="admin_set_date")],
        [InlineKeyboardButton("🔄 تغییر آدرس ولت‌ها", callback_data="admin_set_wallets")],
        [InlineKeyboardButton("🎯 تغییر حداقل مبالغ", callback_data="admin_change_limits")],
        [InlineKeyboardButton("🎲 مدیریت بازی‌ها", callback_data="admin_manage_games")],
        [InlineKeyboardButton("🔌 وضعیت ربات", callback_data="admin_toggle_bot")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]
    ]
    await query.edit_message_text("<b>⚙️ تنظیمات ربات</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def admin_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await admin_panel(update, context)

async def admin_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔐 پنل ادمین بسته شد.")

async def admin_toggle_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    current = admin_config.get("bot_enabled", True)
    admin_config["bot_enabled"] = not current
    save_json(ADMIN_CONFIG_FILE, admin_config)
    status_text = "✅ فعال" if admin_config["bot_enabled"] else "❌ غیرفعال"
    await query.edit_message_text(
        f"""<b>🔌 وضعیت ربات تغییر کرد!</b>

📌 وضعیت جدید: {status_text}""",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 تغییر وضعیت", callback_data="admin_toggle_bot")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]
        ]), parse_mode="HTML")

async def admin_set_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["admin_action"] = "set_date"
    await query.edit_message_text(
        f"""<b>📅 تغییر تاریخ فعال‌سازی واریز ریالی</b>

📌 تاریخ فعلی: {admin_config.get('deposit_enable_date', '30 August')}

تاریخ جدید را وارد کنید:""",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]]),
        parse_mode="HTML")

async def admin_set_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        f"""<b>🔄 تغییر آدرس ولت‌ها</b>

🟣 ولت ترون فعلی:
<code>{admin_config.get('trx_wallet', TRX_WALLET)}</code>

🟢 ولت تتر فعلی:
<code>{admin_config.get('usdt_wallet', USDT_WALLET)}</code>

برای تغییر، یکی از گزینه‌ها را انتخاب کنید:""",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ تغییر ولت ترون", callback_data="admin_edit_trx")],
            [InlineKeyboardButton("✏️ تغییر ولت تتر", callback_data="admin_edit_usdt")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]
        ]), parse_mode="HTML")

async def admin_edit_trx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["admin_action"] = "edit_trx"
    await query.edit_message_text(
        f"""<b>✏️ تغییر آدرس ولت ترون (TRX)</b>

📌 آدرس فعلی:
<code>{admin_config.get('trx_wallet', TRX_WALLET)}</code>

آدرس جدید را وارد کنید:""",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]]),
        parse_mode="HTML")

async def admin_edit_usdt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["admin_action"] = "edit_usdt"
    await query.edit_message_text(
        f"""<b>✏️ تغییر آدرس ولت تتر (USDT-TRC20)</b>

📌 آدرس فعلی:
<code>{admin_config.get('usdt_wallet', USDT_WALLET)}</code>

آدرس جدید را وارد کنید:""",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]]),
        parse_mode="HTML")

async def admin_change_limits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        f"""<b>🎯 تغییر حداقل مبالغ</b>

💰 حداقل شرط: {format_number(admin_config.get('min_bet', MIN_BET))} {CURRENCY}
💰 حداقل واریز: {format_number(admin_config.get('min_deposit', MIN_DEPOSIT))} {CURRENCY}
💰 حداقل برداشت: {format_number(admin_config.get('min_withdraw', MIN_WITHDRAW))} {CURRENCY}

کدام مبلغ را تغییر می‌دهید؟""",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ حداقل شرط", callback_data="admin_edit_min_bet")],
            [InlineKeyboardButton("✏️ حداقل واریز", callback_data="admin_edit_min_deposit")],
            [InlineKeyboardButton("✏️ حداقل برداشت", callback_data="admin_edit_min_withdraw")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]
        ]), parse_mode="HTML")

async def admin_edit_min_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["admin_action"] = "edit_min_bet"
    await query.edit_message_text(
        f"""<b>✏️ تغییر حداقل شرط</b>

📌 حداقل شرط فعلی: {format_number(admin_config.get('min_bet', MIN_BET))} {CURRENCY}

مبلغ جدید را وارد کنید:""",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]]),
        parse_mode="HTML")

async def admin_edit_min_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["admin_action"] = "edit_min_deposit"
    await query.edit_message_text(
        f"""<b>✏️ تغییر حداقل واریز</b>

📌 حداقل واریز فعلی: {format_number(admin_config.get('min_deposit', MIN_DEPOSIT))} {CURRENCY}

مبلغ جدید را وارد کنید:""",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]]),
        parse_mode="HTML")

async def admin_edit_min_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["admin_action"] = "edit_min_withdraw"
    await query.edit_message_text(
        f"""<b>✏️ تغییر حداقل برداشت</b>

📌 حداقل برداشت فعلی: {format_number(admin_config.get('min_withdraw', MIN_WITHDRAW))} {CURRENCY}

مبلغ جدید را وارد کنید:""",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]]),
        parse_mode="HTML")

async def admin_manage_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    games = admin_config.get("games", {})
    text = "<b>🎲 مدیریت بازی‌ها</b>\n\nوضعیت فعلی:\n"
    for game, status in games.items():
        text += f"✅ {game}: {'فعال' if status else 'غیرفعال'}\n"
    keyboard = []
    for game in games.keys():
        keyboard.append([InlineKeyboardButton(f"🔄 تغییر وضعیت {game}", callback_data=f"admin_toggle_game_{game}")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def admin_toggle_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    game = query.data.split("_")[3]
    games = admin_config.get("games", {})
    games[game] = not games.get(game, True)
    admin_config["games"] = games
    save_json(ADMIN_CONFIG_FILE, admin_config)
    await query.edit_message_text(
        f"""✅ وضعیت بازی {game} با موفقیت تغییر کرد.
📌 وضعیت جدید: {'فعال' if games[game] else 'غیرفعال'}""",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 مدیریت بازی‌ها", callback_data="admin_manage_games")]]),
        parse_mode="HTML")

async def admin_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["admin_action"] = "ban"
    await query.edit_message_text(
        "<b>🚫 مسدود کردن کاربر</b>\n\n🆔 آیدی عددی کاربر را وارد کنید:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]]),
        parse_mode="HTML")

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["admin_action"] = "broadcast"
    await query.edit_message_text(
        "<b>📨 ارسال پیام همگانی</b>\n\nمتن پیام را وارد کنید:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]]),
        parse_mode="HTML")

async def admin_global_gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["admin_action"] = "gift"
    await query.edit_message_text(
        "<b>🎁 شارژ همگانی</b>\n\n💰 مبلغ جایزه را وارد کنید:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]]),
        parse_mode="HTML")

async def admin_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["admin_action"] = "balance"
    await query.edit_message_text(
        "<b>💸 مدیریت موجودی کاربر</b>\n\n🆔 آیدی عددی کاربر را وارد کنید:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]]),
        parse_mode="HTML")

async def admin_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["admin_action"] = "search"
    await query.edit_message_text(
        "<b>🔍 جستجوی کاربر</b>\n\n🆔 آیدی عددی کاربر را وارد کنید:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]]),
        parse_mode="HTML")

# ======================== ADMIN MESSAGE HANDLER ========================
async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return
    
    text = update.message.text.strip()
    action = context.user_data.get("admin_action")
    
    if action == "ban":
        try:
            target = int(text)
            user = get_user(target)
            if target in ADMIN_IDS:
                await update.message.reply_text("❌ نمی‌توانید ادمین را مسدود کنید.")
                return
            user["banned"] = not user.get("banned", False)
            save_user(target, user)
            save_json(DATA_FILE, users)
            status = "مسدود" if user["banned"] else "آزاد"
            await update.message.reply_text(f"✅ کاربر با موفقیت {status} شد.")
        except:
            await update.message.reply_text("❌ آیدی نامعتبر است.")
    
    elif action == "broadcast":
        success = 0
        fail = 0
        for uid, data in users.items():
            if data.get("banned", False):
                continue
            try:
                await context.bot.send_message(int(uid), f"{text}", parse_mode="HTML")
                success += 1
            except:
                fail += 1
        await update.message.reply_text(
            f"""<b>✅ پیام همگانی ارسال شد!</b>

👥 ارسال موفق: {success} نفر
❌ ناموفق: {fail} نفر""", parse_mode="HTML")
    
    elif action == "gift":
        try:
            amount = int(text)
            if amount < 0:
                await update.message.reply_text("❌ مبلغ نمی‌تواند منفی باشد.")
                return
            success = 0
            fail = 0
            for uid, data in users.items():
                if data.get("banned", False):
                    continue
                user = get_user(uid)
                user["balance"] += amount
                add_transaction(uid, amount, "gift", f"جایزه همگانی {format_number(amount)} {CURRENCY}")
                save_user(uid, user)
                try:
                    await context.bot.send_message(uid,
                        f"""<b>🎁 جایزه ویژه شرطینو</b>

💰 مبلغ {format_number(amount)} {CURRENCY} به حساب شما اضافه شد.
💰 موجودی جدید: {format_number(user['balance'])} {CURRENCY}""", parse_mode="HTML")
                    success += 1
                except:
                    fail += 1
            save_json(DATA_FILE, users)
            await update.message.reply_text(
                f"""<b>✅ شارژ همگانی با موفقیت انجام شد!</b>

💰 مبلغ شارژ: {format_number(amount)} {CURRENCY}
👥 ارسال موفق: {success} نفر
❌ ناموفق: {fail} نفر""", parse_mode="HTML")
        except:
            await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
    
    elif action == "balance":
        try:
            target = int(text)
            user = get_user(target)
            await update.message.reply_text(
                f"""<b>👤 اطلاعات کاربر</b>

🆔 آیدی: {target}
👤 یوزرنیم: @{user['username'] or 'کاربر'}
💰 موجودی: {format_number(user['balance'])} {CURRENCY}
📊 وضعیت: {'🚫 مسدود' if user.get('banned', False) else '✅ فعال'}
💳 واریز کرده: {'✅ بله' if user.get('has_deposited', False) else '❌ خیر'}""",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ افزایش موجودی", callback_data=f"admin_add_{target}")],
                    [InlineKeyboardButton("➖ کاهش موجودی", callback_data=f"admin_remove_{target}")],
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")]
                ]), parse_mode="HTML")
        except:
            await update.message.reply_text("❌ آیدی نامعتبر است.")
    
    elif action == "search":
        try:
            target = int(text)
            user = get_user(target)
            await update.message.reply_text(
                f"""<b>👤 اطلاعات کاربر</b>

🆔 آیدی: {target}
👤 یوزرنیم: @{user['username'] or 'کاربر'}
💰 موجودی: {format_number(user['balance'])} {CURRENCY}
📊 وضعیت: {'🚫 مسدود' if user.get('banned', False) else '✅ فعال'}
💳 واریز کرده: {'✅ بله' if user.get('has_deposited', False) else '❌ خیر'}
📅 تاریخ عضویت: {user.get('created_at', 'نامشخص')}""", parse_mode="HTML")
        except:
            await update.message.reply_text("❌ آیدی نامعتبر است.")
    
    elif action == "edit_min_bet":
        try:
            new = int(text)
            admin_config["min_bet"] = new
            save_json(ADMIN_CONFIG_FILE, admin_config)
            await update.message.reply_text(f"✅ حداقل شرط تغییر کرد.\n💰 حداقل شرط جدید: {format_number(new)} {CURRENCY}")
        except:
            await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
    
    elif action == "edit_min_deposit":
        try:
            new = int(text)
            admin_config["min_deposit"] = new
            save_json(ADMIN_CONFIG_FILE, admin_config)
            await update.message.reply_text(f"✅ حداقل واریز تغییر کرد.\n💰 حداقل واریز جدید: {format_number(new)} {CURRENCY}")
        except:
            await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
    
    elif action == "edit_min_withdraw":
        try:
            new = int(text)
            admin_config["min_withdraw"] = new
            save_json(ADMIN_CONFIG_FILE, admin_config)
            await update.message.reply_text(f"✅ حداقل برداشت تغییر کرد.\n💰 حداقل برداشت جدید: {format_number(new)} {CURRENCY}")
        except:
            await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
    
    elif action == "edit_trx":
        admin_config["trx_wallet"] = text
        save_json(ADMIN_CONFIG_FILE, admin_config)
        await update.message.reply_text(f"✅ آدرس ولت ترون با موفقیت تغییر کرد.\n🟣 آدرس جدید: <code>{text}</code>", parse_mode="HTML")
    
    elif action == "edit_usdt":
        admin_config["usdt_wallet"] = text
        save_json(ADMIN_CONFIG_FILE, admin_config)
        await update.message.reply_text(f"✅ آدرس ولت تتر با موفقیت تغییر کرد.\n🟢 آدرس جدید: <code>{text}</code>", parse_mode="HTML")
    
    elif action == "set_date":
        admin_config["deposit_enable_date"] = text
        save_json(ADMIN_CONFIG_FILE, admin_config)
        await update.message.reply_text(f"✅ تاریخ با موفقیت تغییر کرد.\n📅 تاریخ جدید: {text}")
    
    context.user_data["admin_action"] = None

async def admin_add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    target = int(query.data.split("_")[2])
    context.user_data["admin_add_user"] = target
    context.user_data["admin_action"] = "admin_add"
    await query.edit_message_text(
        f"""<b>➕ افزایش موجودی کاربر</b>

👤 کاربر: @{get_user(target)['username'] or target}
💰 موجودی فعلی: {format_number(get_user(target)['balance'])} {CURRENCY}

مبلغ مورد نظر را وارد کنید:""",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 انصراف", callback_data="admin_back")]]),
        parse_mode="HTML")

async def admin_remove_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    target = int(query.data.split("_")[2])
    context.user_data["admin_remove_user"] = target
    context.user_data["admin_action"] = "admin_remove"
    await query.edit_message_text(
        f"""<b>➖ کاهش موجودی کاربر</b>

👤 کاربر: @{get_user(target)['username'] or target}
💰 موجودی فعلی: {format_number(get_user(target)['balance'])} {CURRENCY}

مبلغ مورد نظر را وارد کنید:""",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 انصراف", callback_data="admin_back")]]),
        parse_mode="HTML")

async def handle_admin_balance_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return
    action = context.user_data.get("admin_action")
    try:
        amount = int(update.message.text.strip())
        if amount < 0:
            await update.message.reply_text("❌ مبلغ نمی‌تواند منفی باشد.")
            return
    except:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
        return
    
    if action == "admin_add":
        target = context.user_data.get("admin_add_user")
        user = get_user(target)
        user["balance"] += amount
        user["total_deposit"] = user.get("total_deposit", 0) + amount
        add_transaction(target, amount, "deposit", f"واریز توسط ادمین {format_number(amount)} {CURRENCY}")
        user["has_deposited"] = True
        save_user(target, user)
        save_json(DATA_FILE, users)
        await update.message.reply_text(
            f"""<b>✅ موجودی کاربر افزایش یافت.</b>

👤 کاربر: @{user['username'] or target}
💰 مبلغ: {format_number(amount)} {CURRENCY}
💰 موجودی جدید: {format_number(user['balance'])} {CURRENCY}""", parse_mode="HTML")
        try:
            await context.bot.send_message(target,
                f"""<b>✅ موجودی شما افزایش یافت!</b>

💰 مبلغ: {format_number(amount)} {CURRENCY}
💰 موجودی جدید: {format_number(user['balance'])} {CURRENCY}""", parse_mode="HTML")
        except:
            pass
    
    elif action == "admin_remove":
        target = context.user_data.get("admin_remove_user")
        user = get_user(target)
        if user["balance"] < amount:
            await update.message.reply_text(f"❌ موجودی کاربر کافی نیست!\n💰 موجودی: {format_number(user['balance'])} {CURRENCY}")
            return
        user["balance"] -= amount
        add_transaction(target, -amount, "admin_remove", f"کاهش موجودی توسط ادمین {format_number(amount)} {CURRENCY}")
        save_user(target, user)
        save_json(DATA_FILE, users)
        await update.message.reply_text(
            f"""<b>✅ موجودی کاربر کاهش یافت.</b>

👤 کاربر: @{user['username'] or target}
💰 مبلغ: {format_number(amount)} {CURRENCY}
💰 موجودی جدید: {format_number(user['balance'])} {CURRENCY}""", parse_mode="HTML")
        try:
            await context.bot.send_message(target,
                f"""<b>⚠️ موجودی شما کاهش یافت!</b>

💰 مبلغ: {format_number(amount)} {CURRENCY}
💰 موجودی جدید: {format_number(user['balance'])} {CURRENCY}""", parse_mode="HTML")
        except:
            pass
    
    context.user_data["admin_action"] = None
    context.user_data["admin_add_user"] = None
    context.user_data["admin_remove_user"] = None

# ======================== COMMAND MOJODI ========================
async def mojodi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ این دستور فقط برای ادمین است.")
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            """<b>❌ نحوه استفاده:</b>
/mojodi آیدی_عددی مبلغ

<b>مثال:</b>
<code>/mojodi 123456789 500000</code>""", parse_mode="HTML")
        return
    
    try:
        target_id = int(args[0])
        amount = int(args[1])
        if amount <= 0:
            await update.message.reply_text("❌ مبلغ باید بزرگتر از صفر باشد.")
            return
        
        target_key = None
        for uid in users.keys():
            if str(uid).strip() == str(target_id).strip():
                target_key = uid
                break
        
        if not target_key:
            await update.message.reply_text(f"❌ کاربری با آیدی {target_id} یافت نشد.")
            return
        
        target_user = users[target_key]
        old_balance = target_user.get("balance", 0)
        target_user["balance"] = old_balance + amount
        target_user["total_deposit"] = target_user.get("total_deposit", 0) + amount
        target_user["has_deposited"] = True
        if "transactions" not in target_user:
            target_user["transactions"] = []
        target_user["transactions"].append({
            "date": datetime.now().strftime("%Y/%m/%d - %H:%M"),
            "type": "deposit",
            "amount": amount,
            "balance_after": target_user["balance"],
            "description": f"واریز توسط ادمین {format_number(amount)} {CURRENCY}"
        })
        save_user(target_key, target_user)
        save_json(DATA_FILE, users)
        
        username = target_user.get("username", "کاربر")
        await update.message.reply_text(
            f"""<b>✅ موجودی کاربر افزایش یافت.</b>

👤 کاربر: @{username or target_key}
🆔 آیدی: <code>{target_key}</code>
💰 مبلغ اضافه شده: {format_number(amount)} {CURRENCY}
💰 موجودی قبلی: {format_number(old_balance)} {CURRENCY}
💰 موجودی جدید: {format_number(target_user['balance'])} {CURRENCY}""", parse_mode="HTML")
        
        try:
            await context.bot.send_message(int(target_key),
                f"""<b>✅ موجودی شما افزایش یافت!</b>

💰 مبلغ: {format_number(amount)} {CURRENCY}
💰 موجودی جدید: {format_number(target_user['balance'])} {CURRENCY}""", parse_mode="HTML")
        except:
            pass
    except ValueError:
        await update.message.reply_text("❌ لطفاً آیدی و مبلغ را به عدد وارد کنید.")

# ======================== COMMAND WALLET ========================
async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ این دستور فقط برای ادمین است.")
        return
    
    args = context.args
    if len(args) < 2:
        trx_wallet = admin_config.get("trx_wallet", TRX_WALLET)
        usdt_wallet = admin_config.get("usdt_wallet", USDT_WALLET)
        await update.message.reply_text(
            f"""<b>🔄 مدیریت آدرس ولت‌ها</b>

🟣 <b>ولت ترون فعلی:</b>
<code>{trx_wallet}</code>

🟢 <b>ولت تتر فعلی:</b>
<code>{usdt_wallet}</code>

<b>📌 نحوه استفاده:</b>
/wallet trx آدرس_جدید
/wallet usdt آدرس_جدید""", parse_mode="HTML")
        return
    
    wallet_type = args[0].lower()
    new_address = args[1].strip()
    
    if wallet_type == "trx":
        admin_config["trx_wallet"] = new_address
        save_json(ADMIN_CONFIG_FILE, admin_config)
        await update.message.reply_text(
            f"✅ <b>آدرس ولت ترون با موفقیت تغییر کرد.</b>\n\n🟣 آدرس جدید:\n<code>{new_address}</code>",
            parse_mode="HTML")
    elif wallet_type == "usdt":
        admin_config["usdt_wallet"] = new_address
        save_json(ADMIN_CONFIG_FILE, admin_config)
        await update.message.reply_text(
            f"✅ <b>آدرس ولت تتر با موفقیت تغییر کرد.</b>\n\n🟢 آدرس جدید:\n<code>{new_address}</code>",
            parse_mode="HTML")
    else:
        await update.message.reply_text("❌ نوع ولت نامعتبر است.\n\nنحوه استفاده:\n/wallet trx آدرس\n/wallet usdt آدرس")

# ======================== COMMAND CHANNEL ========================
async def channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ این دستور فقط برای ادمین است.")
        return
    
    args = context.args
    channels = admin_config.get("channels", [])
    
    if not args:
        if not channels:
            await update.message.reply_text(
                "<b>📢 مدیریت کانال‌ها</b>\n\n❌ هیچ کانالی ثبت نشده است.\n\n<b>📌 برای اضافه کردن:</b>\n/channel add @link",
                parse_mode="HTML")
            return
        text = "<b>📢 مدیریت کانال‌های عضویت اجباری</b>\n\n<b>📌 کانال‌های فعلی:</b>\n\n"
        active_count = 0
        for i, ch in enumerate(channels, 1):
            status = "✅ فعال" if ch.get("enabled", True) else "❌ غیرفعال"
            if ch.get("enabled", True):
                active_count += 1
            text += f"{i}️⃣ {ch['link']}\n   وضعیت: {status}\n\n"
        text += f"━━━━━━━━━━━━━━━━━━━━━━\n📊 تعداد کل: {len(channels)} کانال\n✅ فعال: {active_count} | ❌ غیرفعال: {len(channels) - active_count}\n\n"
        text += "<b>📌 دستورات:</b>\n/channel add @link\n/channel remove @link\n/channel on @link\n/channel off @link\n/channel off all"
        await update.message.reply_text(text, parse_mode="HTML")
        return
    
    action = args[0].lower()
    
    if action == "add":
        if len(args) < 2:
            await update.message.reply_text("❌ لینک کانال را وارد کنید.\nمثال: /channel add @new_channel")
            return
        new_link = args[1].strip()
        for ch in channels:
            if ch["link"] == new_link:
                await update.message.reply_text("❌ این کانال قبلاً ثبت شده است.")
                return
        channels.append({"link": new_link, "enabled": True})
        admin_config["channels"] = channels
        save_json(ADMIN_CONFIG_FILE, admin_config)
        await update.message.reply_text(f"✅ کانال جدید اضافه شد.\n\n📢 لینک: {new_link}\n📊 وضعیت: ✅ فعال\n\n📌 تعداد کل: {len(channels)}", parse_mode="HTML")
    
    elif action == "remove":
        if len(args) < 2:
            await update.message.reply_text("❌ لینک کانال را وارد کنید.")
            return
        target_link = args[1].strip()
        new_channels = [ch for ch in channels if ch["link"] != target_link]
        if len(new_channels) == len(channels):
            await update.message.reply_text("❌ کانال مورد نظر یافت نشد.")
            return
        admin_config["channels"] = new_channels
        save_json(ADMIN_CONFIG_FILE, admin_config)
        await update.message.reply_text(f"✅ کانال حذف شد.\n\n📢 لینک: {target_link}\n\n📌 تعداد کل: {len(new_channels)}", parse_mode="HTML")
    
    elif action == "on":
        if len(args) < 2:
            await update.message.reply_text("❌ لینک کانال را وارد کنید.")
            return
        target_link = args[1].strip()
        found = False
        for ch in channels:
            if ch["link"] == target_link:
                ch["enabled"] = True
                found = True
                break
        if not found:
            await update.message.reply_text("❌ کانال مورد نظر یافت نشد.")
            return
        admin_config["channels"] = channels
        save_json(ADMIN_CONFIG_FILE, admin_config)
        await update.message.reply_text(f"✅ کانال فعال شد.\n\n📢 لینک: {target_link}\n📊 وضعیت: ✅ فعال", parse_mode="HTML")
    
    elif action == "off":
        if len(args) < 2:
            await update.message.reply_text("❌ لینک کانال را وارد کنید.")
            return
        if args[1].lower() == "all":
            for ch in channels:
                ch["enabled"] = False
            admin_config["channels"] = channels
            save_json(ADMIN_CONFIG_FILE, admin_config)
            await update.message.reply_text(f"✅ همه کانال‌ها غیرفعال شدند.\n\n📊 تعداد: {len(channels)} کانال\n📌 وضعیت: ❌ همه غیرفعال", parse_mode="HTML")
            return
        target_link = args[1].strip()
        found = False
        for ch in channels:
            if ch["link"] == target_link:
                ch["enabled"] = False
                found = True
                break
        if not found:
            await update.message.reply_text("❌ کانال مورد نظر یافت نشد.")
            return
        admin_config["channels"] = channels
        save_json(ADMIN_CONFIG_FILE, admin_config)
        await update.message.reply_text(f"✅ کانال غیرفعال شد.\n\n📢 لینک: {target_link}\n📊 وضعیت: ❌ غیرفعال", parse_mode="HTML")
    
    else:
        await update.message.reply_text(
            """❌ دستور نامعتبر.

<b>📌 دستورات موجود:</b>
/channel
/channel add @link
/channel remove @link
/channel on @link
/channel off @link
/channel off all""", parse_mode="HTML")

# ======================== COMMAND SETSUPPORT ========================
async def setsupport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ این دستور فقط برای ادمین است.")
        return
    
    args = context.args
    if not args:
        current = admin_config.get("support", SUPPORT)
        await update.message.reply_text(
            f"""<b>🆘 تنظیم آیدی پشتیبانی</b>

📌 آیدی فعلی: {current}

<b>📌 نحوه استفاده:</b>
/setsupport @new_support""", parse_mode="HTML")
        return
    
    new_support = args[0].strip()
    if not new_support.startswith("@"):
        new_support = "@" + new_support
    admin_config["support"] = new_support
    save_json(ADMIN_CONFIG_FILE, admin_config)
    await update.message.reply_text(f"✅ آیدی پشتیبانی تغییر کرد.\n\n🆘 آیدی جدید: {new_support}", parse_mode="HTML")

# ======================== COMMAND CARD ========================
async def card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ این دستور فقط برای ادمین است.")
        return
    
    args = context.args
    cards = admin_config.get("cards", [])
    
    if not args:
        if not cards:
            await update.message.reply_text(
                """<b>💳 مدیریت کارت‌ها</b>

❌ هیچ کارتی ثبت نشده است.

<b>📌 نحوه استفاده:</b>
/card add شماره_کارت نام_صاحب_کارت
/card remove شماره_کارت
/card on شماره_کارت
/card off شماره_کارت
/card off all""", parse_mode="HTML")
            return
        text = "<b>💳 مدیریت کارت‌های بانکی</b>\n\n<b>📌 کارت‌های فعلی:</b>\n\n"
        active_count = 0
        for i, c in enumerate(cards, 1):
            status = "✅ فعال" if c.get("enabled", True) else "❌ غیرفعال"
            if c.get("enabled", True):
                active_count += 1
            text += f"{i}️⃣ شماره: <code>{c['number']}</code>\n   به نام: {c.get('holder', 'نامشخص')}\n   وضعیت: {status}\n\n"
        text += f"━━━━━━━━━━━━━━━━━━━━━━\n📊 تعداد کل: {len(cards)} کارت\n✅ فعال: {active_count} | ❌ غیرفعال: {len(cards) - active_count}\n\n"
        text += "<b>📌 دستورات:</b>\n/card add شماره نام\n/card remove شماره\n/card on شماره\n/card off شماره\n/card off all"
        await update.message.reply_text(text, parse_mode="HTML")
        return
    
    action = args[0].lower()
    
    if action == "add":
        if len(args) < 3:
            await update.message.reply_text("❌ نحوه استفاده:\n/card add شماره_کارت نام_صاحب_کارت")
            return
        card_number = args[1].strip()
        holder_name = " ".join(args[2:]).strip()
        for c in cards:
            if c["number"] == card_number:
                await update.message.reply_text("❌ این کارت قبلاً ثبت شده است.")
                return
        cards.append({"number": card_number, "holder": holder_name, "enabled": True})
        admin_config["cards"] = cards
        save_json(ADMIN_CONFIG_FILE, admin_config)
        await update.message.reply_text(
            f"""✅ <b>کارت جدید اضافه شد.</b>

💳 شماره کارت: <code>{card_number}</code>
👤 به نام: {holder_name}
📊 وضعیت: ✅ فعال

📌 تعداد کل: {len(cards)} کارت""", parse_mode="HTML")
    
    elif action == "remove":
        if len(args) < 2:
            await update.message.reply_text("❌ نحوه استفاده:\n/card remove شماره_کارت")
            return
        card_number = args[1].strip()
        new_cards = [c for c in cards if c["number"] != card_number]
        if len(new_cards) == len(cards):
            await update.message.reply_text("❌ کارت مورد نظر یافت نشد.")
            return
        admin_config["cards"] = new_cards
        save_json(ADMIN_CONFIG_FILE, admin_config)
        await update.message.reply_text(f"✅ کارت حذف شد.\n\n💳 شماره: {card_number}\n\n📌 تعداد کل: {len(new_cards)} کارت", parse_mode="HTML")
    
    elif action == "on":
        if len(args) < 2:
            await update.message.reply_text("❌ نحوه استفاده:\n/card on شماره_کارت")
            return
        card_number = args[1].strip()
        found = False
        for c in cards:
            if c["number"] == card_number:
                c["enabled"] = True
                found = True
                break
        if not found:
            await update.message.reply_text("❌ کارت مورد نظر یافت نشد.")
            return
        admin_config["cards"] = cards
        save_json(ADMIN_CONFIG_FILE, admin_config)
        await update.message.reply_text(f"✅ کارت فعال شد.\n\n💳 شماره: {card_number}\n📊 وضعیت: ✅ فعال", parse_mode="HTML")
    
    elif action == "off":
        if len(args) < 2:
            await update.message.reply_text("❌ نحوه استفاده:\n/card off شماره_کارت\n/card off all")
            return
        if args[1].lower() == "all":
            for c in cards:
                c["enabled"] = False
            admin_config["cards"] = cards
            save_json(ADMIN_CONFIG_FILE, admin_config)
            await update.message.reply_text(f"✅ همه کارت‌ها غیرفعال شدند.\n\n📊 تعداد: {len(cards)} کارت\n📌 وضعیت: ❌ همه غیرفعال", parse_mode="HTML")
            return
        card_number = args[1].strip()
        found = False
        for c in cards:
            if c["number"] == card_number:
                c["enabled"] = False
                found = True
                break
        if not found:
            await update.message.reply_text("❌ کارت مورد نظر یافت نشد.")
            return
        admin_config["cards"] = cards
        save_json(ADMIN_CONFIG_FILE, admin_config)
        await update.message.reply_text(f"✅ کارت غیرفعال شد.\n\n💳 شماره: {card_number}\n📊 وضعیت: ❌ غیرفعال", parse_mode="HTML")
    
    else:
        await update.message.reply_text(
            """❌ دستور نامعتبر.

<b>📌 دستورات موجود:</b>
/card
/card add شماره نام
/card remove شماره
/card on شماره
/card off شماره
/card off all""", parse_mode="HTML")

# ======================== COMMAND ZIR ========================
async def zir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ این دستور فقط برای ادمین است.")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text(
            """<b>❌ نحوه استفاده:</b>
/zir آیدی_کاربر

<b>مثال:</b>
<code>/zir 123456789</code>""", parse_mode="HTML")
        return
    
    try:
        target_id = int(args[0])
        target_user = get_user(target_id)
        if str(target_id) not in users:
            await update.message.reply_text("❌ کاربری با این آیدی یافت نشد.")
            return
        
        referrer_info = "❌ این کاربر با لینک دعوت وارد نشده است."
        if target_user.get("joined_via_link", False):
            referrer_id = target_user.get("referrer_id")
            referrer_username = target_user.get("referrer_username", "ناشناس")
            if referrer_id:
                referrer_info = f"👤 دعوت‌کننده: @{referrer_username} (ID: {referrer_id})"
        
        text = f"""<b>🔍 اطلاعات دعوت کاربر</b>

🆔 کاربر: @{target_user.get('username', 'کاربر')} (ID: {target_id})
📅 تاریخ عضویت: {target_user.get('created_at', 'نامشخص')}

<b>🔗 لینک دعوت استفاده شده:</b>
{target_user.get('referred_by', '❌ بدون لینک')}

{referrer_info}"""
        await update.message.reply_text(text, parse_mode="HTML")
    except ValueError:
        await update.message.reply_text("❌ لطفاً یک آیدی عددی معتبر وارد کنید.")

# ======================== BROADCAST COMMANDS ========================
async def jayeze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ این دستور فقط برای ادمین است.")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text(
            """<b>❌ نحوه استفاده:</b>
/jayeze مبلغ

<b>مثال:</b>
<code>/jayeze 100000</code>""", parse_mode="HTML")
        return
    
    try:
        amount = int(args[0])
        if amount <= 0:
            await update.message.reply_text("❌ مبلغ باید بزرگتر از صفر باشد.")
            return
        if amount > 10000000:
            await update.message.reply_text("❌ حداکثر مبلغ ۱۰,۰۰۰,۰۰۰ تومان است.")
            return
    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
        return
    
    success = 0
    fail = 0
    total_cost = 0
    msg = await update.message.reply_text(f"📨 در حال ارسال جایزه {format_number(amount)} تومانی...")
    
    for uid, data in users.items():
        if data.get("banned", False):
            continue
        try:
            user = get_user(uid)
            user["balance"] += amount
            add_transaction(uid, amount, "gift", f"جایزه همگانی {format_number(amount)} {CURRENCY}")
            save_user(uid, user)
            success += 1
            total_cost += amount
            try:
                await context.bot.send_message(int(uid),
                    f"""<b>🎁 جایزه ویژه شرطینو</b>

💰 مبلغ {format_number(amount)} {CURRENCY} به حساب شما اضافه شد.
💰 موجودی جدید: {format_number(user['balance'])} {CURRENCY}""", parse_mode="HTML")
            except:
                pass
        except:
            fail += 1
    
    save_json(DATA_FILE, users)
    await msg.edit_text(
        f"""<b>✅ جایزه همگانی ارسال شد!</b>

💰 مبلغ هر جایزه: {format_number(amount)} {CURRENCY}
👥 دریافت‌کنندگان: {success} نفر
💰 کل مبلغ: {format_number(total_cost)} {CURRENCY}
❌ ناموفق: {fail} نفر""", parse_mode="HTML")

async def ersal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ این دستور فقط برای ادمین است.")
        return
    
    text = update.message.text.replace("/ersal", "").strip()
    if not text:
        await update.message.reply_text(
            """<b>❌ نحوه استفاده:</b>
/ersal متن پیام

<b>مثال:</b>
<code>/ersal سلام به همه!</code>""", parse_mode="HTML")
        return
    
    success = 0
    fail = 0
    msg = await update.message.reply_text("📨 در حال ارسال پیام همگانی...")
    
    for uid, data in users.items():
        if data.get("banned", False):
            continue
        try:
            await context.bot.send_message(int(uid), f"{text}", parse_mode="HTML")
            success += 1
        except:
            fail += 1
    
    await msg.edit_text(
        f"""<b>✅ پیام همگانی ارسال شد!</b>

👥 ارسال موفق: {success} نفر
❌ ناموفق: {fail} نفر""", parse_mode="HTML")

async def ersalphoto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ این دستور فقط برای ادمین است.")
        return
    
    if not update.message.photo:
        await update.message.reply_text(
            """<b>❌ نحوه استفاده:</b>
/ersalphoto (همراه با عکس و کپشن)

عکس را با متن (کپشن) ارسال کنید.""", parse_mode="HTML")
        return
    
    photo = update.message.photo[-1]
    file_id = photo.file_id
    caption = update.message.caption or ""
    success = 0
    fail = 0
    msg = await update.message.reply_text("📨 در حال ارسال عکس همگانی...")
    
    for uid, data in users.items():
        if data.get("banned", False):
            continue
        try:
            await context.bot.send_photo(chat_id=int(uid), photo=file_id, caption=f"{caption}", parse_mode="HTML")
            success += 1
        except:
            fail += 1
    
    await msg.edit_text(
        f"""<b>✅ عکس همگانی ارسال شد!</b>

👥 ارسال موفق: {success} نفر
❌ ناموفق: {fail} نفر""", parse_mode="HTML")

async def amar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ این دستور فقط برای ادمین است.")
        return
    
    user_list = []
    for uid, data in users.items():
        user_list.append({
            "id": uid,
            "username": data.get("username", "کاربر"),
            "balance": data.get("balance", 0),
            "referral_count": data.get("referral_count", 0),
            "total_bets": data.get("total_bets", 0),
            "total_wins": data.get("total_wins", 0)
        })
    
    if not user_list:
        await update.message.reply_text("❌ هیچ کاربری وجود ندارد.")
        return
    
    sorted_by_balance = sorted(user_list, key=lambda x: x["balance"], reverse=True)[:20]
    text = "<b>🏆 ۲۰ کاربر برتر از لحاظ موجودی:</b>\n\n"
    for i, user in enumerate(sorted_by_balance, 1):
        username = user["username"] if user["username"] else f"کاربر {user['id'][:8]}"
        text += f"{i}. @{username} — 💰 {format_number(user['balance'])} {CURRENCY}\n"
    
    sorted_by_referral = sorted(user_list, key=lambda x: x["referral_count"], reverse=True)[:20]
    text += "\n━━━━━━━━━━━━━━━━━━━━━━\n<b>👥 ۲۰ کاربر برتر از لحاظ دعوت:</b>\n\n"
    for i, user in enumerate(sorted_by_referral, 1):
        username = user["username"] if user["username"] else f"کاربر {user['id'][:8]}"
        text += f"{i}. @{username} — 👥 {user['referral_count']} نفر\n"
    
    total_users = len(user_list)
    total_balance = sum(u["balance"] for u in user_list)
    total_bets = sum(u["total_bets"] for u in user_list)
    total_wins = sum(u["total_wins"] for u in user_list)
    
    text += f"\n━━━━━━━━━━━━━━━━━━━━━━\n<b>📊 آمار کلی:</b>\n👥 کاربران: {total_users:,}\n💰 موجودی: {format_number(total_balance)} {CURRENCY}\n🎯 شرط‌ها: {total_bets:,}\n🏆 بردها: {total_wins:,}"
    
    await update.message.reply_text(text, parse_mode="HTML")

# ======================== INACTIVE USERS CHECK ========================
async def check_inactive_users(app: Application):
    bot = app.bot
    now = datetime.now()
    support = admin_config.get("support", SUPPORT)
    
    for uid, data in users.items():
        if data.get("banned", False):
            continue
        if data.get("inactive_warning_sent", False):
            continue
        last_activity = data.get("last_activity")
        if not last_activity:
            last_activity = data.get("created_at", now.strftime("%Y-%m-%d %H:%M:%S"))
        try:
            last_time = datetime.strptime(last_activity, "%Y-%m-%d %H:%M:%S")
            diff = (now - last_time).total_seconds() / 3600
            if diff >= INACTIVE_HOURS:
                user = get_user(uid)
                user["balance"] += INACTIVE_BONUS
                user["inactive_warning_sent"] = True
                add_transaction(uid, INACTIVE_BONUS, "gift", f"جایزه کاربر غیرفعال {format_number(INACTIVE_BONUS)} {CURRENCY}")
                save_user(uid, user)
                try:
                    await bot.send_message(chat_id=int(uid),
                        text=f"""<b>🎰 شرطینو</b>

👋 سلام! متوجه شدیم که مدتی است بازی نکرده‌اید.

🎲 بازی‌ها و جوایز جدید برای شما در دسترس است!

💰 به عنوان هدیه، {format_number(INACTIVE_BONUS)} {CURRENCY} به حساب شما اضافه شد!

🆘 پشتیبانی: {support}

👉 برای شروع روی /start کلیک کنید""", parse_mode="HTML")
                except:
                    pass
        except:
            pass
    save_json(DATA_FILE, users)

# ======================== UNKNOWN ========================
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ دستور نامعتبر. لطفاً از منو استفاده کنید.")

# ======================== MAIN ========================
def main():
    import logging
    logging.disable(logging.CRITICAL)
    
    gc.enable()
    gc.set_threshold(700, 10, 5)
    
    web_thread = Thread(target=run_web_server, daemon=True)
    web_thread.start()
    
    periodic_save()
    
    app = Application.builder().token(TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("mojodi", mojodi))
    app.add_handler(CommandHandler("wallet", wallet))
    app.add_handler(CommandHandler("channel", channel))
    app.add_handler(CommandHandler("setsupport", setsupport))
    app.add_handler(CommandHandler("card", card))
    app.add_handler(CommandHandler("zir", zir))
    app.add_handler(CommandHandler("jayeze", jayeze))
    app.add_handler(CommandHandler("ersal", ersal))
    app.add_handler(CommandHandler("ersalphoto", ersalphoto))
    app.add_handler(CommandHandler("amar", amar))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(intro_done, pattern="^intro_done$"))
    app.add_handler(CallbackQueryHandler(main_menu, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(game_menu, pattern="^game_menu$"))
    app.add_handler(CallbackQueryHandler(check_gift, pattern="^check_gift$"))
    app.add_handler(CallbackQueryHandler(check_join, pattern="^check_join$"))
    app.add_handler(CallbackQueryHandler(earnings, pattern="^earnings$"))
    
    # Games
    app.add_handler(CallbackQueryHandler(dice_game, pattern="^dice_game$"))
    app.add_handler(CallbackQueryHandler(dice_bet_selected, pattern="^dice_bet_"))
    app.add_handler(CallbackQueryHandler(dice_coef_selected, pattern="^dice_coef_"))
    app.add_handler(CallbackQueryHandler(dice_roll, pattern="^dice_roll$"))
    
    app.add_handler(CallbackQueryHandler(coin_game, pattern="^coin_game$"))
    app.add_handler(CallbackQueryHandler(coin_bet_selected, pattern="^coin_bet_"))
    app.add_handler(CallbackQueryHandler(coin_predict, pattern="^coin_predict_"))
    
    app.add_handler(CallbackQueryHandler(slot_game, pattern="^slot_game$"))
    app.add_handler(CallbackQueryHandler(slot_bet_selected, pattern="^slot_bet_"))
    app.add_handler(CallbackQueryHandler(slot_spin, pattern="^slot_spin$"))
    
    app.add_handler(CallbackQueryHandler(football_game, pattern="^football_game$"))
    app.add_handler(CallbackQueryHandler(football_bet_selected, pattern="^football_bet_"))
    app.add_handler(CallbackQueryHandler(football_predict, pattern="^football_predict_"))
    
    # Account
    app.add_handler(CallbackQueryHandler(my_account, pattern="^my_account$"))
    app.add_handler(CallbackQueryHandler(deposit, pattern="^deposit$"))
    app.add_handler(CallbackQueryHandler(withdraw, pattern="^withdraw$"))
    app.add_handler(CallbackQueryHandler(withdraw_amount_selected, pattern="^withdraw_"))
    app.add_handler(CallbackQueryHandler(withdraw_card, pattern="^withdraw_card$"))
    app.add_handler(CallbackQueryHandler(withdraw_wallet, pattern="^withdraw_wallet$"))
    app.add_handler(CallbackQueryHandler(transactions, pattern="^transactions$"))
    app.add_handler(CallbackQueryHandler(trust, pattern="^trust$"))
    
    # Admin
    app.add_handler(CallbackQueryHandler(admin_stats, pattern="^admin_stats$"))
    app.add_handler(CallbackQueryHandler(admin_users, pattern="^admin_users$"))
    app.add_handler(CallbackQueryHandler(admin_settings, pattern="^admin_settings$"))
    app.add_handler(CallbackQueryHandler(admin_back, pattern="^admin_back$"))
    app.add_handler(CallbackQueryHandler(admin_close, pattern="^admin_close$"))
    app.add_handler(CallbackQueryHandler(admin_toggle_bot, pattern="^admin_toggle_bot$"))
    app.add_handler(CallbackQueryHandler(admin_set_date, pattern="^admin_set_date$"))
    app.add_handler(CallbackQueryHandler(admin_set_wallets, pattern="^admin_set_wallets$"))
    app.add_handler(CallbackQueryHandler(admin_edit_trx, pattern="^admin_edit_trx$"))
    app.add_handler(CallbackQueryHandler(admin_edit_usdt, pattern="^admin_edit_usdt$"))
    app.add_handler(CallbackQueryHandler(admin_change_limits, pattern="^admin_change_limits$"))
    app.add_handler(CallbackQueryHandler(admin_edit_min_bet, pattern="^admin_edit_min_bet$"))
    app.add_handler(CallbackQueryHandler(admin_edit_min_deposit, pattern="^admin_edit_min_deposit$"))
    app.add_handler(CallbackQueryHandler(admin_edit_min_withdraw, pattern="^admin_edit_min_withdraw$"))
    app.add_handler(CallbackQueryHandler(admin_manage_games, pattern="^admin_manage_games$"))
    app.add_handler(CallbackQueryHandler(admin_toggle_game, pattern="^admin_toggle_game_"))
    app.add_handler(CallbackQueryHandler(admin_ban, pattern="^admin_ban$"))
    app.add_handler(CallbackQueryHandler(admin_broadcast, pattern="^admin_broadcast$"))
    app.add_handler(CallbackQueryHandler(admin_global_gift, pattern="^admin_global_gift$"))
    app.add_handler(CallbackQueryHandler(admin_balance, pattern="^admin_balance$"))
    app.add_handler(CallbackQueryHandler(admin_search, pattern="^admin_search$"))
    app.add_handler(CallbackQueryHandler(admin_add_balance, pattern="^admin_add_"))
    app.add_handler(CallbackQueryHandler(admin_remove_balance, pattern="^admin_remove_"))
    
    # Messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_balance_action))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_withdraw_info))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))
    
    print("🤖 شرطینو روشن شد...")
    try:
        app.run_polling()
    finally:
        save_json(DATA_FILE, users)
        save_json(ADMIN_CONFIG_FILE, admin_config)
        print("✅ ذخیره نهایی انجام شد")

if __name__ == "__main__":
    main()
