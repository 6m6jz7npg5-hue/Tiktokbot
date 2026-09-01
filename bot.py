import logging
import re
import requests
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaVideo
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)

# تعريف الحالات
CHOOSING, TYPING_USERNAME, ACCOUNT_VIEW, STORY_VIEW = range(4)

# إعداد التسجيل
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ========== دوال جلب البيانات من تيك توك ==========
def fetch_tiktok_data(username: str) -> dict:
    """
    جلب بيانات حساب تيك توك من الصفحة العامة.
    تُعيد قاموسًا يحتوي على المعلومات المستخرجة.
    """
    url = f"https://www.tiktok.com/@{username}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Error fetching TikTok page: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    user_data = {}

    # البحث عن بيانات JSON المدمجة في الصفحة
    scripts = soup.find_all("script")
    for script in scripts:
        if script.string and "userInfo" in script.string:
            json_text = script.string
            patterns = {
                "followerCount": r'"followerCount":(\d+)',
                "followingCount": r'"followingCount":(\d+)',
                "heartCount": r'"heartCount":(\d+)',
                "videoCount": r'"videoCount":(\d+)',
                "nickname": r'"nickname":"([^"]+)"',
                "uniqueId": r'"uniqueId":"([^"]+)"',
                "avatarLarger": r'"avatarLarger":"([^"]+)"',
                "signature": r'"signature":"((?:[^"\\]|\\.)*)"',  # البايو
                "region": r'"region":"([^"]+)"',                  # البلد
                "verified": r'"verified":(true|false)',
            }
            for key, pattern in patterns.items():
                match = re.search(pattern, json_text)
                if match:
                    if key in ["followerCount", "followingCount", "heartCount", "videoCount"]:
                        user_data[key] = int(match.group(1))
                    elif key == "verified":
                        user_data[key] = match.group(1) == "true"
                    else:
                        user_data[key] = match.group(1).encode().decode('unicode_escape')  # فك ترميز النصوص
            # استخراج أحدث الفيديوهات (لعمل الستوري)
            video_urls = re.findall(r'"playAddr":"([^"]+)"', json_text)
            if video_urls:
                user_data["video_urls"] = video_urls[:5]  # أول 5 فيديوهات
            if user_data:
                break

    return user_data if user_data else None

def format_user_data(username: str, data: dict) -> str:
    """تنسيق البيانات لعرضها في رسالة نصية."""
    if not data:
        return f"⚠️ تعذر جلب بيانات الحساب @{username}. تأكد من أن اليوزر صحيح."

    lines = [f"📊 معلومات حساب: @{username}"]
    if "nickname" in data:
        lines.append(f"👤 الاسم: {data['nickname']}")
    if "uniqueId" in data:
        lines.append(f"🆔 اليوزر: @{data['uniqueId']}")
    if "region" in data:
        lines.append(f"🌍 البلد: {data['region']}")
    if "signature" in data and data["signature"]:
        lines.append(f"📝 البايو: {data['signature']}")
    if "followerCount" in data:
        lines.append(f"👥 المتابعون: {data['followerCount']:,}")
    if "followingCount" in data:
        lines.append(f"🔁 يتابع: {data['followingCount']:,}")
    if "heartCount" in data:
        lines.append(f"❤️ الإعجابات: {data['heartCount']:,}")
    if "videoCount" in data:
        lines.append(f"🎬 الفيديوهات: {data['videoCount']:,}")
    if "verified" in data and data["verified"]:
        lines.append("✔️ موثّق")
    return "\n".join(lines)

# ========== دوال معالجة الأوامر والأزرار ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إرسال رسالة الترحيب مع الأزرار الرئيسية."""
    keyboard = [
        [InlineKeyboardButton("🔍 فحص حساب", callback_data="check_account")],
        [InlineKeyboardButton("📖 عرض الاستوريات", callback_data="stories")],
        [InlineKeyboardButton("🔄 الريبوستات", callback_data="reposts")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "مرحباً! أنا بوت تيك توك.\nاختر العملية التي تريدها:",
        reply_markup=reply_markup,
    )
    return CHOOSING

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة ضغطات الأزرار في القائمة الرئيسية."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "check_account":
        await query.edit_message_text("📝 أرسل يوزر حساب تيك توك الذي تريد فحصه (بدون @):")
        context.user_data["state"] = "waiting_for_username"
        return TYPING_USERNAME

    elif data == "stories":
        await query.edit_message_text("⚠️ لعرض الستوري، يجب أولاً فحص حساب معين ثم الضغط على زر عرض الستوري.")
        return CHOOSING

    elif data == "reposts":
        await query.edit_message_text("⚠️ لجلب الريبوست، يجب أولاً فحص حساب معين ثم الضغط على زر جلب الريبوست.")
        return CHOOSING

    else:
        await query.edit_message_text("خيار غير معروف.")
        return CHOOSING

async def receive_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """استقبال اليوزر بعد الضغط على زر فحص حساب."""
    if context.user_data.get("state") != "waiting_for_username":
        await update.message.reply_text("الرجاء استخدام الأزرار أولاً.")
        return CHOOSING

    username = update.message.text.strip().lstrip("@")
    await update.message.reply_text("⏳ جاري جلب البيانات...")

    data = fetch_tiktok_data(username)
    if not data:
        await update.message.reply_text(f"⚠️ تعذر جلب بيانات الحساب @{username}. تأكد من صحة اليوزر.")
        context.user_data["state"] = None
        return CHOOSING

    # حفظ البيانات في context لاستخدامها لاحقاً
    context.user_data["account_data"] = data
    context.user_data["current_username"] = username

    # إرسال الصورة الرمزية إن وجدت
    if "avatarLarger" in data:
        try:
            await update.message.reply_photo(photo=data["avatarLarger"])
        except Exception as e:
            logger.warning(f"Could not send avatar: {e}")

    # إرسال المعلومات النصية
    formatted = format_user_data(username, data)
    keyboard = [
        [
            InlineKeyboardButton("📖 عرض الستوري", callback_data="show_stories"),
            InlineKeyboardButton("🔄 جلب الريبوست", callback_data="show_reposts"),
        ],
        [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(formatted, reply_markup=reply_markup)

    context.user_data["state"] = None
    return ACCOUNT_VIEW

async def account_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة الأزرار بعد عرض معلومات الحساب."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back_to_menu":
        await back_to_menu(update, context)
        return CHOOSING

    elif data == "show_stories":
        return await show_stories(update, context)

    elif data == "show_reposts":
        await query.edit_message_text("🔄 جاري جلب الريبوست... (قيد التطوير حالياً)")
        return ACCOUNT_VIEW

    else:
        await query.edit_message_text("خيار غير معروف.")
        return ACCOUNT_VIEW

async def show_stories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """عرض قائمة الفيديوهات (كاستوري) مع أزرار تنقل."""
    query = update.callback_query
    await query.answer()

    data = context.user_data.get("account_data")
    if not data or "video_urls" not in data or not data["video_urls"]:
        await query.edit_message_text("⚠️ لا توجد فيديوهات متاحة لهذا الحساب.")
        return ACCOUNT_VIEW

    # حفظ قائمة الفيديوهات والمؤشر الحالي
    context.user_data["stories"] = data["video_urls"]
    context.user_data["story_index"] = 0

    return await send_story(update, context, edit=False)

async def send_story(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = True) -> int:
    """إرسال الفيديو الحالي مع أزرار التنقل."""
    query = update.callback_query
    stories = context.user_data.get("stories")
    if not stories:
        await query.edit_message_text("⚠️ لا توجد استوريات.")
        return ACCOUNT_VIEW

    index = context.user_data.get("story_index", 0)
    total = len(stories)
    video_url = stories[index]

    keyboard = [
        [
            InlineKeyboardButton("◀️ السابق", callback_data="prev_story"),
            InlineKeyboardButton(f"{index+1}/{total}", callback_data="noop"),
            InlineKeyboardButton("التالي ▶️", callback_data="next_story"),
        ],
        [InlineKeyboardButton("🔙 خروج", callback_data="exit_stories")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if edit:
            # تعديل الرسالة الحالية إلى فيديو جديد
            await query.edit_message_media(
                media=InputMediaVideo(media=video_url),
                reply_markup=reply_markup,
            )
        else:
            # إرسال فيديو جديد
            await query.message.reply_video(
                video=video_url,
                reply_markup=reply_markup,
            )
    except Exception as e:
        logger.error(f"Error sending story: {e}")
        await query.edit_message_text("⚠️ تعذر عرض الفيديو، ربما يكون الرابط غير صالح.")
        return ACCOUNT_VIEW

    return STORY_VIEW

async def story_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة أزرار التنقل في الستوري."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "next_story":
        index = context.user_data.get("story_index", 0)
        stories = context.user_data.get("stories", [])
        if index < len(stories) - 1:
            context.user_data["story_index"] = index + 1
            return await send_story(update, context, edit=True)
        else:
            await query.answer("هذا آخر ستوري")
            return STORY_VIEW

    elif data == "prev_story":
        index = context.user_data.get("story_index", 0)
        if index > 0:
            context.user_data["story_index"] = index - 1
            return await send_story(update, context, edit=True)
        else:
            await query.answer("هذا أول ستوري")
            return STORY_VIEW

    elif data == "exit_stories":
        await query.edit_message_text("تم الخروج من الستوري.")
        return ACCOUNT_VIEW

    elif data == "noop":
        return STORY_VIEW

    else:
        return STORY_VIEW

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """الرجوع إلى القائمة الرئيسية."""
    query = update.callback_query
    if query:
        await query.answer()
        keyboard = [
            [InlineKeyboardButton("🔍 فحص حساب", callback_data="check_account")],
            [InlineKeyboardButton("📖 عرض الاستوريات", callback_data="stories")],
            [InlineKeyboardButton("🔄 الريبوستات", callback_data="reposts")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("اختر العملية:", reply_markup=reply_markup)
    return CHOOSING

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إلغاء العملية الحالية."""
    await update.message.reply_text("تم الإلغاء. استخدم /start للبدء من جديد.")
    context.user_data.clear()
    return ConversationHandler.END

# ========== الدالة الرئيسية ==========
def main() -> None:
    """تشغيل البوت."""
    # التوكن الخاص بك
    application = Application.builder().token("8955349729:AAG0JdkQ5gyFd-IPqjjDJHlj1xtLXiNFjBY").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING: [
                CallbackQueryHandler(button_callback),
            ],
            TYPING_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_username),
            ],
            ACCOUNT_VIEW: [
                CallbackQueryHandler(account_view_callback),
            ],
            STORY_VIEW: [
                CallbackQueryHandler(story_view_callback),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == "__main__":
    main()
