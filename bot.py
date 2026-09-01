import logging
import re
import requests
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)

# تعريف الحالات (States) للتحكم في المحادثة
CHOOSING, TYPING_USERNAME = range(2)

# إعداد التسجيل
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ========== دوال جلب البيانات من تيك توك ==========
def fetch_tiktok_data(username: str) -> dict:
    """
    جلب بيانات حساب تيك توك من الصفحة العامة باستخدام requests و BeautifulSoup/Regex.
    تُعيد قاموسًا يحتوي على المعلومات المستخرجة (المتابعون، الإعجابات، إلخ).
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

    # البحث عن بيانات JSON المدمجة في الصفحة (عادة داخل وسم script)
    scripts = soup.find_all("script")
    for script in scripts:
        if script.string and "userInfo" in script.string:
            json_text = script.string
            # استخدام Regex لاستخراج المعلومات الشائعة
            patterns = {
                "followerCount": r'"followerCount":(\d+)',
                "followingCount": r'"followingCount":(\d+)',
                "heartCount": r'"heartCount":(\d+)',
                "videoCount": r'"videoCount":(\d+)',
                "nickname": r'"nickname":"([^"]+)"',
                "uniqueId": r'"uniqueId":"([^"]+)"',
                "avatarLarger": r'"avatarLarger":"([^"]+)"',
            }
            for key, pattern in patterns.items():
                match = re.search(pattern, json_text)
                if match:
                    if key in ["followerCount", "followingCount", "heartCount", "videoCount"]:
                        user_data[key] = int(match.group(1))
                    else:
                        user_data[key] = match.group(1)
            # إذا وجدنا بيانات نخرج من الحلقة
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
    if "followerCount" in data:
        lines.append(f"👥 المتابعون: {data['followerCount']:,}")
    if "followingCount" in data:
        lines.append(f"🔁 يتابع: {data['followingCount']:,}")
    if "heartCount" in data:
        lines.append(f"❤️ الإعجابات: {data['heartCount']:,}")
    if "videoCount" in data:
        lines.append(f"🎬 الفيديوهات: {data['videoCount']:,}")
    if "avatarLarger" in data:
        lines.append(f"🖼️ الصورة الرمزية: {data['avatarLarger']}")
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
    """معالجة ضغطات الأزرار."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "check_account":
        await query.edit_message_text("📝 أرسل يوزر حساب تيك توك الذي تريد فحصه (بدون @):")
        # تعيين حالة الانتظار لاستقبال اليوزر
        context.user_data["state"] = "waiting_for_username"
        return TYPING_USERNAME

    elif data == "stories":
        await query.edit_message_text("📖 ميزة عرض الاستوريات غير متوفرة حالياً.")
        return CHOOSING

    elif data == "reposts":
        await query.edit_message_text("🔄 ميزة الريبوستات غير متوفرة حالياً.")
        return CHOOSING

    else:
        await query.edit_message_text("خيار غير معروف.")
        return CHOOSING

async def receive_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    استقبال اليوزر بعد أن يكون المستخدم قد ضغط زر "فحص حساب".
    يتم التحقق من الحالة قبل المعالجة.
    """
    # التحقق من أن الحالة هي waiting_for_username
    if context.user_data.get("state") != "waiting_for_username":
        await update.message.reply_text("الرجاء استخدام الأزرار أولاً.")
        return CHOOSING

    username = update.message.text.strip()
    # إزالة @ إذا كانت موجودة
    if username.startswith("@"):
        username = username[1:]

    # رسالة انتظار
    await update.message.reply_text("⏳ جاري جلب البيانات...")

    # جلب البيانات
    data = fetch_tiktok_data(username)
    formatted = format_user_data(username, data)

    # عرض النتيجة مع زر للعودة للقائمة
    keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(formatted, reply_markup=reply_markup)

    # إعادة تعيين الحالة
    context.user_data["state"] = None
    return CHOOSING

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """الرجوع إلى القائمة الرئيسية."""
    query = update.callback_query
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
    context.user_data["state"] = None
    return ConversationHandler.END

# ========== الدالة الرئيسية ==========
def main() -> None:
    """تشغيل البوت."""
    # ضع التوكن الخاص بك هنا (تم إدراجه)
    application = Application.builder().token("8955349729:AAG0JdkQ5gyFd-IPqjjDJHlj1xtLXiNFjBY").build()

    # إعداد ConversationHandler لإدارة الحالات
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING: [
                CallbackQueryHandler(button_callback),
            ],
            TYPING_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_username),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    # بدء البوت
    application.run_polling()

if __name__ == "__main__":
    main()
