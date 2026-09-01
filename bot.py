import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import re
import json
import os

# ========== التوكن ==========
# يفضل وضعه في متغير بيئة، لكن للاختبار ضعه مباشرة
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8955349729:AAG0JdkQ5gyFd-IPqjjDJHlj1xtLXiNFjBY")
bot = telebot.TeleBot(BOT_TOKEN)

# ========== إدارة الحالة والبيانات المؤقتة ==========
user_states = {}     # {chat_id: 'awaiting_username' or None}
user_data = {}       # {chat_id: {'username':..., 'data':{...}}}

# ========== رؤوس HTTP ==========
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# ========== دالة جلب بيانات تيك توك ==========
def fetch_tiktok_data(username: str):
    """
    تجلب بيانات الحساب من صفحة الملف الشخصي (بدون وهميات)
    تعيد قاموساً يحتوي على جميع البيانات الممكنة
    """
    result = {
        "user_id": "غير متاح",
        "unique_id": username,
        "nickname": "غير متاح",
        "bio": "غير متاح",
        "avatar": "غير متاح",
        "follower_count": "غير متاح",
        "following_count": "غير متاح",
        "video_count": "غير متاح",
        "total_likes": "غير متاح",
        "videos": [],        # قائمة كل فيديو: {id, url, desc}
        "reposts": []        # ليست متاحة من هذه الصفحة
    }

    url = f"https://www.tiktok.com/@{username}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return result

        html = resp.text

        # استخراج كائن JSON المضمن
        pattern = r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>'
        match = re.search(pattern, html, re.DOTALL)
        if not match:
            pattern_old = r'<script id="SIGI_STATE"[^>]*>(.*?)</script>'
            match = re.search(pattern_old, html, re.DOTALL)
            if not match:
                return result

        json_text = match.group(1)
        data = json.loads(json_text)

        # استكشاف المسارات
        user_info = None
        if "__DEFAULT_SCOPE__" in data:
            default = data["__DEFAULT_SCOPE__"]
            if "webapp.user-detail" in default:
                user_info = default["webapp.user-detail"].get("userInfo", {})
            elif "user-detail" in default:
                user_info = default["user-detail"].get("userInfo", {})
        elif "UserModule" in data and "users" in data["UserModule"]:
            users_dict = data["UserModule"]["users"]
            if users_dict:
                first_key = next(iter(users_dict))
                user_info = users_dict[first_key]
        else:
            user_info = data.get("userInfo") or data.get("user")

        if not user_info:
            return result

        # الحقول الأساسية
        result["user_id"] = user_info.get("id", "غير متاح")
        result["unique_id"] = user_info.get("uniqueId", username)
        result["nickname"] = user_info.get("nickname", "غير متاح")
        result["bio"] = user_info.get("signature", "غير متاح")

        avatar = user_info.get("avatarLarger") or user_info.get("avatarMedium") or {}
        if isinstance(avatar, dict):
            result["avatar"] = avatar.get("urlList", ["غير متاح"])[0] if avatar.get("urlList") else "غير متاح"
        elif isinstance(avatar, str):
            result["avatar"] = avatar

        stats = user_info.get("stats", {})
        if stats:
            result["follower_count"] = stats.get("followerCount", "غير متاح")
            result["following_count"] = stats.get("followingCount", "غير متاح")
            result["video_count"] = stats.get("videoCount", "غير متاح")
            result["total_likes"] = stats.get("heartCount", "غير متاح")
        else:
            result["follower_count"] = user_info.get("followerCount", "غير متاح")
            result["following_count"] = user_info.get("followingCount", "غير متاح")
            result["video_count"] = user_info.get("videoCount", "غير متاح")
            result["total_likes"] = user_info.get("heartCount", "غير متاح")

        # جلب الفيديوهات
        video_items = []
        if "__DEFAULT_SCOPE__" in data and "webapp.user-detail" in data["__DEFAULT_SCOPE__"]:
            detail = data["__DEFAULT_SCOPE__"]["webapp.user-detail"]
            video_items = detail.get("itemList", [])
        elif "UserModule" in data and "posts" in data["UserModule"]:
            video_items = data["UserModule"]["posts"]

        if not video_items:
            # بحث عام
            def find_list(obj, keys):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if k in keys and isinstance(v, list) and v and isinstance(v[0], dict):
                            return v
                        res = find_list(v, keys)
                        if res:
                            return res
                return None
            video_items = find_list(data, ["itemList", "awemeList", "posts"]) or []

        for item in video_items[:20]:
            vid_id = item.get("id") or item.get("awemeId") or "غير متاح"
            desc = item.get("desc") or item.get("title") or ""
            if vid_id != "غير متاح":
                vid_url = f"https://www.tiktok.com/@{username}/video/{vid_id}"
            else:
                vid_url = "غير متاح"
            result["videos"].append({
                "id": vid_id,
                "url": vid_url,
                "desc": desc[:60]
            })

        # الريبوستات غير متاحة
        result["reposts"] = []

    except Exception:
        pass

    return result

# ========== أزرار القائمة الرئيسية ==========
def main_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    btn1 = InlineKeyboardButton("🔍 فحص حساب", callback_data="scan")
    btn2 = InlineKeyboardButton("❓ مساعدة", callback_data="help")
    btn3 = InlineKeyboardButton("ℹ️ عن البوت", callback_data="about")
    keyboard.add(btn1, btn2, btn3)
    return keyboard

# ========== أزرار بعد عرض البيانات ==========
def data_actions(chat_id):
    keyboard = InlineKeyboardMarkup(row_width=2)
    btn_vids = InlineKeyboardButton("📹 عرض الفيديوهات", callback_data="show_videos")
    btn_reposts = InlineKeyboardButton("🔄 عرض الريبوستات", callback_data="show_reposts")
    btn_back = InlineKeyboardButton("🔙 رجوع", callback_data="back_main")
    keyboard.add(btn_vids, btn_reposts, btn_back)
    return keyboard

# ========== عرض الفيديوهات (زر) ==========
def show_videos_list(chat_id):
    data = user_data.get(chat_id, {})
    videos = data.get("videos", [])
    if not videos:
        return "❌ لا توجد فيديوهات متاحة."
    msg = "📹 **قائمة الفيديوهات** (أول 10):\n"
    for i, v in enumerate(videos[:10], 1):
        msg += f"{i}. [فيديو {v['id']}]({v['url']})"
        if v['desc']:
            msg += f" - {v['desc']}"
        msg += "\n"
    if len(videos) > 10:
        msg += f"... و {len(videos)-10} فيديوهات أخرى."
    return msg

# ========== عرض الريبوستات (غير متاحة) ==========
def show_reposts_list(chat_id):
    return "🔄 الريبوستات غير متاحة من خلال هذه الواجهة العامة."

# ========== معالج الأزرار ==========
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    msg_id = call.message.message_id

    if call.data == "scan":
        # طلب إدخال اليوزر
        bot.send_message(chat_id, "📝 الرجاء إرسال اسم المستخدم (بدون @) :")
        user_states[chat_id] = "awaiting_username"
        bot.answer_callback_query(call.id)

    elif call.data == "help":
        bot.edit_message_text(
            "❓ **المساعدة**\n\n"
            "• اضغط على 'فحص حساب' ثم أرسل اسم المستخدم.\n"
            "• سأعرض لك بيانات الحساب والفيديوهات.\n"
            "• البيانات تُجلب من الصفحة العامة لتيك توك.",
            chat_id, msg_id, reply_markup=main_menu(), parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id)

    elif call.data == "about":
        bot.edit_message_text(
            "ℹ️ **عن البوت**\n\n"
            "إصدار 2.0\n"
            "يعمل بجلب البيانات الحقيقية من تيك توك عبر requests و regex.\n"
            "المطور: @your_username",
            chat_id, msg_id, reply_markup=main_menu(), parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id)

    elif call.data == "back_main":
        bot.edit_message_text(
            "🏠 **القائمة الرئيسية**",
            chat_id, msg_id, reply_markup=main_menu()
        )
        bot.answer_callback_query(call.id)

    elif call.data == "show_videos":
        text = show_videos_list(chat_id)
        # نرسل رسالة جديدة بدلاً من تعديل الرسالة الأصلية لنحتفظ بالبيانات
        bot.send_message(chat_id, text, parse_mode="Markdown", disable_web_page_preview=True)
        bot.answer_callback_query(call.id)

    elif call.data == "show_reposts":
        bot.send_message(chat_id, show_reposts_list(chat_id))
        bot.answer_callback_query(call.id)

    else:
        bot.answer_callback_query(call.id)

# ========== معالج الرسائل النصية ==========
@bot.message_handler(func=lambda msg: True)
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.strip()

    # إذا كان المستخدم في حالة انتظار اليوزر
    if user_states.get(chat_id) == "awaiting_username":
        # نتأكد أن النص ليس أمراً آخر
        if text.startswith('/'):
            bot.reply_to(message, "⚠️ الرجاء إرسال اسم مستخدم صالح (بدون @) وليس أمراً.")
            return

        # إزالة @ إن وجدت
        username = text.replace("@", "").strip()
        if not username:
            bot.reply_to(message, "❌ الاسم فارغ، أرسل اسماً صحيحاً.")
            return

        bot.reply_to(message, f"⏳ جاري فحص @{username} ...")

        # جلب البيانات
        data = fetch_tiktok_data(username)

        # تخزين البيانات مؤقتاً للمستخدم
        user_data[chat_id] = data

        # بناء رسالة النتيجة
        reply = (
            f"📊 **بيانات حساب TikTok**\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🆔 **الاسم**: @{data['unique_id']}\n"
            f"👤 **اللقب**: {data['nickname']}\n"
            f"📝 **السيرة**: {data['bio']}\n"
            f"🆔 **الرقم الرقمي**: `{data['user_id']}`\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"👥 **المتابعون**: {data['follower_count']}\n"
            f"👤 **يتابع**: {data['following_count']}\n"
            f"🎬 **عدد الفيديوهات**: {data['video_count']}\n"
            f"❤️ **إجمالي الإعجابات**: {data['total_likes']}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📹 **عدد الفيديوهات المحملة**: {len(data['videos'])}"
        )

        # إرسال النتيجة مع أزرار الإجراءات
        bot.send_message(
            chat_id,
            reply,
            reply_markup=data_actions(chat_id),
            parse_mode="Markdown"
        )

        # إلغاء حالة الانتظار
        user_states[chat_id] = None

    else:
        # إذا لم يكن في حالة انتظار، نرد برسالة توجيهية
        bot.reply_to(
            message,
            "👋 مرحباً! استخدم الأزرار أدناه للتفاعل.\n"
            "اضغط على '🔍 فحص حساب' لبدء الفحص.",
            reply_markup=main_menu()
        )

# ========== أمر /start ==========
@bot.message_handler(commands=['start'])
def start_cmd(message):
    chat_id = message.chat.id
    user_states[chat_id] = None  # إعادة تعيين الحالة
    bot.send_message(
        chat_id,
        "👋 أهلاً بك في بوت فحص تيك توك!\nاختر أحد الأزرار:",
        reply_markup=main_menu()
    )

# ========== تشغيل البوت ==========
if __name__ == "__main__":
    print("🤖 البوت يعمل...")
    bot.infinity_polling()
