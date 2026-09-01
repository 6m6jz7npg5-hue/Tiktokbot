import telebot
import requests
import json
import re
import time

# ============================================================
# 🔴 هام جداً: هذا التوكن تم وضعه بناءً على طلبك، لكنه أصبح مكشوفاً.
# يرجى إلغاؤه فوراً من @BotFather واستبدال الرقم أدناه بالتوكن الجديد.
# ============================================================
BOT_TOKEN = "8955349729:AAG0JdkQ5gyFd-IPqjjDJHlj1xtLXiNFjBY"

bot = telebot.TeleBot(BOT_TOKEN)

# رؤوس تحاكي المتصفح لتجنب الحظر
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0"
}

def get_tiktok_user_data(username: str):
    """
    تجلب بيانات الحساب من صفحة الملف الشخصي لـ TikTok
    باستخدام نقاط النهاية العامة (بدون توقيعات)
    """
    # القيمة الافتراضية (جميع الحقول "غير متاح")
    result = {
        "user_id": "غير متاح",
        "unique_id": username,
        "nickname": "غير متاح",
        "bio": "غير متاح",
        "avatar_url": "غير متاح",
        "follower_count": "غير متاح",
        "following_count": "غير متاح",
        "video_count": "غير متاح",
        "total_likes": "غير متاح",
        "create_time": "غير متاح",
        "videos": [],
        "repost_videos": []
    }

    url = f"https://www.tiktok.com/@{username}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return result

        html = resp.text

        # 1. استخراج كائن JSON من <script id="__UNIVERSAL_DATA_FOR_REHYDRATION__">
        pattern = r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>'
        match = re.search(pattern, html, re.DOTALL)
        if not match:
            pattern_old = r'<script id="SIGI_STATE"[^>]*>(.*?)</script>'
            match = re.search(pattern_old, html, re.DOTALL)
            if not match:
                return result
        
        json_text = match.group(1)
        data = json.loads(json_text)

        # 2. استكشاف المسار الصحيح للبيانات
        user_info = None

        # المسار 1: __UNIVERSAL_DATA_FOR_REHYDRATION__
        if "__DEFAULT_SCOPE__" in data:
            default = data["__DEFAULT_SCOPE__"]
            if "webapp.user-detail" in default:
                user_info = default["webapp.user-detail"].get("userInfo", {})
            elif "user-detail" in default:
                user_info = default["user-detail"].get("userInfo", {})
        # المسار 2: SIGI_STATE
        elif "UserModule" in data and "users" in data["UserModule"]:
            users_dict = data["UserModule"]["users"]
            if users_dict:
                first_key = next(iter(users_dict))
                user_info = users_dict[first_key]
        else:
            if "userInfo" in data:
                user_info = data["userInfo"]
            elif "user" in data:
                user_info = data["user"]

        if not user_info:
            return result

        # 3. استخراج الحقول
        result["user_id"] = user_info.get("id", "غير متاح")
        result["unique_id"] = user_info.get("uniqueId", username)
        result["nickname"] = user_info.get("nickname", "غير متاح")
        result["bio"] = user_info.get("signature", "غير متاح")

        avatar = user_info.get("avatarLarger", {})
        if isinstance(avatar, dict):
            result["avatar_url"] = avatar.get("urlList", ["غير متاح"])[0] if avatar.get("urlList") else "غير متاح"
        elif isinstance(avatar, str):
            result["avatar_url"] = avatar

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

        result["create_time"] = "غير متاح"

        # 4. جلب الفيديوهات
        video_items = []
        if "__DEFAULT_SCOPE__" in data and "webapp.user-detail" in data["__DEFAULT_SCOPE__"]:
            detail = data["__DEFAULT_SCOPE__"]["webapp.user-detail"]
            if "itemList" in detail:
                video_items = detail["itemList"]
        elif "UserModule" in data and "posts" in data["UserModule"]:
            video_items = data["UserModule"]["posts"]

        if not video_items:
            def find_list(obj, keys):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if k in keys and isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                            return v
                        res = find_list(v, keys)
                        if res:
                            return res
                return None
            video_items = find_list(data, ["itemList", "awemeList", "posts"]) or []

        for i, item in enumerate(video_items[:20]):
            video_id = item.get("id", item.get("awemeId", "غير متاح"))
            desc = item.get("desc", item.get("title", ""))
            if video_id != "غير متاح":
                video_url = f"https://www.tiktok.com/@{username}/video/{video_id}"
            else:
                video_url = "غير متاح"
            result["videos"].append({
                "id": video_id,
                "url": video_url,
                "desc": desc[:50]
            })

        result["repost_videos"] = []

    except Exception as e:
        # في حال أي خطأ، نعود بالبيانات الافتراضية
        pass

    return result

# ========== أوامر البوت ==========
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message,
        "👋 أهلاً! أرسل لي اسم مستخدم TikTok (بدون @) وسأحاول جلب بيانات الحساب.\n"
        "مثال: `tiktokuser`"
    )

@bot.message_handler(func=lambda msg: True)
def handle_username(message):
    username = message.text.strip().replace("@", "")
    if not username:
        bot.reply_to(message, "❌ الرجاء إدخال اسم مستخدم صحيح.")
        return

    bot.reply_to(message, f"⏳ جاري البحث عن @{username} ...")

    data = get_tiktok_user_data(username)

    # بناء الرد
    reply = (
        f"📊 **بيانات حساب TikTok**\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🆔 **الاسم**: @{data['unique_id']}\n"
        f"👤 **اللقب**: {data['nickname']}\n"
        f"📝 **السيرة**: {data['bio']}\n"
        f"🆔 **الرقم الرقمي**: `{data['user_id']}`\n"
        f"📅 **تاريخ الإنشاء**: {data['create_time']}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"👥 **المتابعون**: {data['follower_count']}\n"
        f"👤 **يتابع**: {data['following_count']}\n"
        f"🎬 **عدد الفيديوهات**: {data['video_count']}\n"
        f"❤️ **إجمالي الإعجابات**: {data['total_likes']}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📹 **روابط الفيديوهات** (أول 5):\n"
    )

    videos = data.get("videos", [])
    if videos:
        for i, v in enumerate(videos[:5]):
            reply += f"{i+1}. [فيديو {v['id']}]({v['url']})"
            if v['desc']:
                reply += f" - {v['desc']}"
            reply += "\n"
        if len(videos) > 5:
            reply += f"... و {len(videos)-5} فيديوهات أخرى\n"
    else:
        reply += "لا توجد فيديوهات متاحة.\n"

    reply += f"\n📤 **الريبوستات**: {len(data.get('repost_videos', []))}"

    bot.reply_to(message, reply, parse_mode="Markdown")

# ========== تشغيل البوت ==========
if __name__ == "__main__":
    print("🤖 البوت يعمل الآن على Render...")
    bot.infinity_polling()
