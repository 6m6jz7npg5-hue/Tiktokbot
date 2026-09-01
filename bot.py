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

# تعريف الحالات للتحكم بتسلسل المحادثة
CHOOSING, TYPING_USERNAME, ACCOUNT_VIEW, STORY_VIEW = range(4)

# إعداد التسجيل
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# توكن البوت
BOT_TOKEN = "8955349729:AAG0JdkQ5gyFd-IPqjjDJHlj1xtLXiNFjBY"

# ========== دوال تنظيف وجلب بيانات تيك توك الحقيقية ==========
def clean_url(url: str) -> str:
    """تنظيف الروابط من الهروب البرمجي"""
    if not url:
        return url
    return url.replace("\\/", "/").replace("\\u002F", "/")

def fetch_tiktok_data(username: str) -> dict:
    """جلب بيانات الحساب الحقيقية من الصفحة العامة لـ تيك توك"""
    url = f"https://www.tiktok.com/@{username}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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

    scripts = soup.find_all("script")
    for script in scripts:
        if script.string and ("userInfo" in script.string or "uniqueId" in script.string):
            json_text = script.string
            patterns = {
                "followerCount": r'"followerCount":(\d+)',
                "followingCount": r'"followingCount":(\d+)',
                "heartCount": r'"heartCount":(\d+)',
                "videoCount": r'"videoCount":(\d+)',
                "nickname": r'"nickname":"([^"]+)"',
                "uniqueId": r'"uniqueId":"([^"]+)"',
                "avatarLarger": r'"avatarLarger":"([^"]+)"',
                "signature": r'"signature":"((?:[^"\\]|\\.)*)"',
                "region": r'"region":"([^"]+)"',
                "verified": r'"verified":(true|false)',
                "userId": r'"id":"(\d+)"',
            }
            for key, pattern in patterns.items():
                match = re.search(pattern, json_text)
                if match:
                    if key in ["followerCount", "followingCount", "heartCount", "videoCount"]:
                        user_data[key] = int(match.group(1))
                    elif key == "verified":
                        user_data[key] = match.group(1) == "true"
                    else:
                        value = match.group(1)
                        try:
                            value = value.encode().decode('unicode_escape')
                        except Exception:
                            pass
                        user_data[key] = value
            
            # استخراج روابط الفيديوهات المتاحة
            video_urls = re.findall(r'"playAddr":"([^"]+)"', json_text)
            if video_urls:
                user_data["video_urls"] = [clean_url(v) for v in video_urls[:5]]
            
            if "avatarLarger" in user_data:
                user_data["avatarLarger"] = clean_url(user_data["avatarLarger"])
            
            if user_data:
                break

    return user_data if user_data else None

def format_user_data(username: str, data: dict) -> str:
    """تنسيق البيانات الحقيقية لعرضها بشكل مرتب"""
    if not data:
        return f"⚠️ تعذر جلب بيانات الحساب @{username}. تأكد من صحة اليوزر أو أن الحساب عام."

    lines = [f"📊 **معلومات حساب تيك توك**", f"━━━━━━━━━━━━━━━━"]
    if "nickname" in data:
        lines.append(f"👤 **الاسم**: {data['nickname']}")
    if "uniqueId" in data:
        lines.append(f"🆔 **اليوزر**: @{data['uniqueId']}")
    if "userId" in data:
        lines.append(f"🔢 **الرقم التعريفي (ID)**: `{data['userId']}`")
    if "region" in data:
        lines.append(f"🌍 **البلد**: {data['region']}")
    else:
        lines.append("🌍 **البلد**: غير متاح (مخفي من المنصة)")
    if "signature" in data and data["signature"]:
        lines.append(f"📝 **البايو**: {data['signature']}")
    if "followerCount" in data:
        lines.append(f"👥 **المتابعون**: {data['followerCount']:,}")
    if "followingCount" in data:
        lines.append(f"🔁 **يتابع**: {data['followingCount']:,}")
    if "heartCount" in data:
        lines.append(f"❤️ **الإعجابات**: {data['heartCount']:,}")
    if "videoCount" in data:
        lines.append(f"🎬 **الفيديوهات**: {data['videoCount']:,}")
    if "verified" in data and data["verified"]:
        lines.append("✔️ **حساب موثّق**")

    return "\n".join(lines)

# ========== دوال الواجهة والأزرار ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    keyboard = [
        [InlineKeyboardButton("🔍 فحص حساب", callback_data="check_account")],
        [InlineKeyboardButton("📖 عرض الاستوريات", callback_data="stories")],
        [InlineKeyboardButton("🔄 الريبوستات", callback_data="reposts")],
        [InlineKeyboardButton("🛡️ طريقة الدخول", callback_data="login_info")],
        [InlineKeyboardButton("🌍 معلومات الدولة", callback_data="country_info")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text("👋 أهلاً بك يا كينغ في بوت تحليل تيك توك:\nاختر العملية التي تريدها:", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text("اختر العملية:", reply_markup=reply_markup)
    return CHOOSING

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "check_account":
        await query.edit_message_text("📝 أرسل الآن يوزر حساب تيك توك الذي تريد فحصه (بدون @):")
        context.user_data["state"] = "waiting_for_username"
        return TYPING_USERNAME

    elif data == "stories":
        await query.edit_message_text("📖 ميزة عرض الاستوريات المباشرة تتطلب تفاعل الحساب أو أن تكون متاحة عامة.")
        return CHOOSING

    elif data == "reposts":
        await query.edit_message_text("🔄 ميزة الريبوستات قيد التطوير.")
        return CHOOSING

    elif data == "login_info":
        await query.edit_message_text("🛡️ معلومات الدخول (إيميل/رقم) خاصة بالمستخدم ولا يمكن جلبها نهائياً من الواجهة العامة لأي حساب.")
        return CHOOSING

    elif data == "country_info":
        await query.edit_message_text("🌍 معلومات الدولة تظهر إن كانت متاحة في السجلات العامة، وغالباً ما يخفيها المستخدمون.")
        return CHOOSING

    return CHOOSING

async def receive_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if context.user_data.get("state") != "waiting_for_username":
        return CHOOSING

    username = update.message.text.strip().lstrip("@")
    await update.message.reply_text(f"⏳ جاري جلب بيانات الحساب الحقيقية لـ @{username} ...")

    data = fetch_tiktok_data(username)
    if not data:
        await update.message.reply_text(f"⚠️ تعذر جلب بيانات الحساب @{username}. تأكد من صحة اليوزر وأن الحساب ليس خاصاً (Private).")
        context.user_data["state"] = None
        return CHOOSING

    context.user_data["account_data"] = data
    context.user_data["current_username"] = username

    formatted = format_user_data(username, data)

    keyboard = [
        [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="back_to_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if "avatarLarger" in data and data["avatarLarger"]:
        try:
            await update.message.reply_photo(
                photo=data["avatarLarger"],
                caption=formatted,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception:
            await update.message.reply_text(formatted, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(formatted, reply_markup=reply_markup, parse_mode="Markdown")

    context.user_data["state"] = None
    return ACCOUNT_VIEW

async def account_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "back_to_menu":
        return await start(update, context)
    return ACCOUNT_VIEW

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("تم الإلغاء. استخدم /start للبدء من جديد.")
    context.user_data.clear()
    return ConversationHandler.END

# ========== التشغيل الرئيسي ==========
def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING: [CallbackQueryHandler(button_callback)],
            TYPING_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_username)],
            ACCOUNT_VIEW: [CallbackQueryHandler(account_view_callback)],
        },
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("cancel", cancel),
        ],
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == "__main__":
    main()
