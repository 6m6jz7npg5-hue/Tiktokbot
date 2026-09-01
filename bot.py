import telebot
from tiktokflow import TikTokAPI

# ---------- الإعدادات ----------
BOT_TOKEN = "8955349729:AAG0JdkQ5gyFd-IPqjjDJHlj1xtLXiNFjBY"  # توكن بوتك
bot = telebot.TeleBot(BOT_TOKEN)

# تهيئة TikTok API
api = TikTokAPI()

# ---------- الدالة الأساسية لجلب بيانات المستخدم ----------
def get_tiktok_user_data(username: str):
    """
    جلب بيانات مستخدم تيك توك عبر المعرّف
    الرجوع: قاموس يحتوي على البيانات، والغير متوفر يظهر كـ 'غير متاح'
    """
    result = {
        "user_id": "غير متاح",
        "sec_user_id": "غير متاح",
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

    try:
        # 1. البحث عن المستخدم وجلب المعرّف الفرعي sec_user_id
        search_results = api.user.search(username)
        if not search_results or "user_list" not in search_results:
            return result
        
        user_data = search_results["user_list"][0]
        sec_user_id = user_data.get("sec_user_id")
        
        if not sec_user_id:
            return result

        # 2. جلب المعلومات التفصيلية للحساب
        profile = api.user.info(sec_user_id)
        if not profile:
            return result

        user_info = profile.get("user_info", {})
        result["user_id"] = user_info.get("uid", "غير متاح")
        result["sec_user_id"] = sec_user_id
        result["unique_id"] = user_info.get("unique_id", username)
        result["nickname"] = user_info.get("nickname", "غير متاح")
        result["bio"] = user_info.get("signature", "غير متاح")
        result["avatar_url"] = user_info.get("avatar_larger", {}).get("url_list", ["غير متاح"])[0]
        
        # الإحصائيات
        stats = user_info.get("stats", {})
        result["follower_count"] = stats.get("follower_count", "غير متاح")
        result["following_count"] = stats.get("following_count", "غير متاح")
        result["video_count"] = stats.get("video_count", "غير متاح")
        result["total_likes"] = stats.get("digg_count", "غير متاح")
        
        result["create_time"] = user_info.get("create_time", "غير متاح")

        # 3. جلب قائمة الفيديوهات
        try:
            posts = api.feed.user_posts(sec_user_id, count=20)
            if posts and "aweme_list" in posts:
                for video in posts["aweme_list"]:
                    video_id = video.get("aweme_id", "غير متاح")
                    video_url = f"https://www.tiktok.com/@{username}/video/{video_id}" if video_id != "غير متاح" else "غير متاح"
                    result["videos"].append({
                        "id": video_id,
                        "url": video_url,
                        "desc": video.get("desc", "")
                    })
        except Exception:
            pass

        result["repost_videos"] = []

    except Exception as e:
        pass

    return result

# ---------- أوامر بوت تيليجرام ----------
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, 
        "👋 أهلاً بك يا كينغ في نظام التتبع المطور!\n"
        "أرسل لي اسم مستخدم TikTok لجلب بيانات الحساب الحقيقية:\n"
        "مثال: `username`",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda msg: True)
def fetch_user_handler(message):
    username = message.text.strip()
    if username.startswith("@"):
        username = username[1:]
    
    bot.reply_to(message, f"⏳ جاري جلب بيانات الحساب بدقة: @{username} ...")
    
    data = get_tiktok_user_data(username)
    
    reply = (
        f"📊 **بيانات حساب TikTok الحقيقية**\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🆔 **الاسم**: @{data['unique_id']}\n"
        f"👤 **اللقب**: {data['nickname']}\n"
        f"📝 **السيرة الذاتية**: {data['bio']}\n"
        f"🆔 **الرقم التعريفي (ID)**: `{data['user_id']}`\n"
        f"📅 **تاريخ الإنشاء**: {data['create_time']}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"👥 **المتابعون**: {data['follower_count']}\n"
        f"👤 **يتابع**: {data['following_count']}\n"
        f"🎬 **الفيديوهات**: {data['video_count']}\n"
        f"❤️ **إجمالي الإعجابات**: {data['total_likes']}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📹 **أحدث روابط الفيديوهات**:\n"
    )
    
    if data["videos"]:
        for i, v in enumerate(data["videos"][:5]):
            reply += f"{i+1}. [فيديو {v['id']}]({v['url']})\n"
        if len(data["videos"]) > 5:
            reply += f"... و {len(data['videos'])-5} فيديوهات أخرى\n"
    else:
        reply += "لا توجد فيديوهات متاحة للعامة\n"
    
    bot.reply_to(message, reply, parse_mode="Markdown")

# ---------- تشغيل البوت ----------
if __name__ == "__main__":
    print("🤖 البوت يعمل بكامل طاقته النظيفة والخالية من الوهم...")
    bot.infinity_polling()
