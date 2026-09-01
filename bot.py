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

# تعريف الحالات
CHOOSING, TYPING_USERNAME, ACCOUNT_VIEW = range(3)

# إعداد التسجيل
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8955349729:AAG0JdkQ5gyFd-IPqjjDJHlj1xtLXiNFjBY"

# ========== دوال جلب وتنظيف البيانات ==========
def clean_url(url: str) -> str:
    if not url:
        return url
    return url.replace("\\/", "/").replace("\\u002F", "/")

def safe_decode(text: str) -> str:
    """فك ترميز النصوص العربية والإيموجي بشكل سليم منعاً للرموز الغريبة"""
    if not text:
        return ""
    try:
        # معالجة الرموز المهربة Unicode
        return text.encode().decode('unicode-escape').encode('latin1').decode('utf-8', errors='ignore')
    except Exception:
        try:
            return text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
        except Exception:
            return text

def fetch_tiktok_data(username: str) -> dict:
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
                "avatarMedium": r'"avatarMedium":"([^"]+)"',
                "avatarThumb": r'"avatarThumb":"([^"]+)"',
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
                        val = match.group(1)
                        user_data[key] = safe_decode(val)
            
            # البحث عن أفضل صورة بروفايل متاحة احتياطياً
            avatar = user_data.get("avatarLarger") or user_data.get("avatarMedium") or user_data.get("avatarThumb")
            if avatar:
                user_data["avatar"] = clean_url(avatar)
            
            video_urls = re.findall(r'"playAddr":"([^"]+)"', json_text)
            if video_urls:
                user_data["video_urls"] = [clean_url(v) for v in video_urls[:5]]
            
            if user_data:
                break

    return user_data if user_data else None

def format_user_data(username: str, data: dict) -> str:
    if not data:
        return f"⚠️ تعذر جلب بيانات الحساب @{username}. تأكد من صحة اليوزر أو أن الحساب عام."

    nickname = data.get('nickname', username)
    unique_id = data.get('uniqueId', username)
    region = data.get('region', 'غير متاح (مخفي)')
    signature = data.get('signature', 'لا يوجد بايو')
    
    lines = [
        f"📊 **معلومات الحساب**: @{unique_id}",
        f"━━━━━━━━━━━━━━━━",
        f"👤 **الاسم**: {nickname}",
        f"🆔 **اليوزر**: @{unique_id}",
        f"🌍 **البلد**: {region}",
        f"📝 **البايو**: {signature}",
    ]
    
    if "followerCount" in data:
        lines.append(f"👥 **المتابعون**: {data['followerCount']:,}")
    if "followingCount" in data:
        lines.append(f"🔁 **يتابع**: {data['followingCount']:,}")
    if "heartCount" in data:
        lines.append(f"❤️ **الإعجابات**: {data['heartCount']:,}")
    if "videoCount" in data:
        lines.append(f"🎬 **الفيديوهات**: {data['videoCount']:,}")
    if data.get("verified"):
        lines.append("✔️ **حساب موثّق**")

    lines.append("\n📌 **ملاحظات:**")
    lines.append("• معلومات الدولة قد لا تكون متاحة للعامة.")
    lines.append("• معلومات الدخول (إيميل/رقم) خاصة ولا يمكن جلبها من الصفحة العامة.")

    return "\n".join(lines)

# ========== دوال التحكم بالواجهة ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    keyboard = [
        [InlineKeyboardButton("🔍 فحص حساب", callback_data="check_account")],
        [InlineKeyboardButton("🛡️ طريقة الدخول", callback_data="login_info")],
        [InlineKeyboardButton("🌍 معلومات الدولة", callback_data="country_info")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text("👋 أهلاً بك يا كينغ في بوت تحليل تيك توك:\nاختر العملية التي تريدها:", reply_markup=reply_markup)
    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.message.edit_text("👋 اختر العملية التي تريدها:", reply_markup=reply_markup)
    return CHOOSING

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "check_account":
        await query.message.edit_text("📝 أرسل الآن يوزر حساب تيك توك الذي تريد فحصه (بدون @):")
        context.user_data["state"] = "waiting_for_username"
        return TYPING_USERNAME

    elif data == "login_info":
        keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back_to_menu")]]
        await query.message.edit_text(
            "🛡️ معلومات الدخول (إيميل/رقم) هي معلومات خاصة وحساسة، ولا يمكن جلبها من الصفحة العامة لأي حساب.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CHOOSING

    elif data == "country_info":
        keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back_to_menu")]]
        await query.message.edit_text(
            "🌍 معلومات الدولة (الموقع الجغرافي) غالباً ما تكون مخفية في ملف الحساب العام، ولا يمكن استخراجها بشكل موثوق.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CHOOSING

    elif data == "back_to_menu":
        return await start(update, context)

    return CHOOSING

async def receive_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if context.user_data.get("state") != "waiting_for_username":
        return CHOOSING

    username = update.message.text.strip().lstrip("@")
    msg = await update.message.reply_text(f"⏳ جاري جلب بيانات الحساب لـ @{username} ...")

    data = fetch_tiktok_data(username)
    if not data:
        keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back_to_menu")]]
        await update.message.reply_text(
            f"⚠️ تعذر جلب بيانات الحساب @{username}. تأكد من صحة اليوزر وأن الحساب عام.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data["state"] = None
        return CHOOSING

    context.user_data["account_data"] = data
    context.user_data["current_username"] = username

    formatted = format_user_data(username, data)

    keyboard = [
        [InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back_to_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # إرسال الصورة بدقة واحتياطياً النص لو لم تتوفر
    avatar_url = data.get("avatar")
    if avatar_url:
        try:
            await update.message.reply_photo(
                photo=avatar_url,
                caption=formatted,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            # حذف رسالة الانتظار لتنظيف الشاشة
            await msg.delete()
            context.user_data["state"] = None
            return ACCOUNT_VIEW
        except Exception as e:
            logger.warning(f"Failed to send photo: {e}")

    # البديلة في حال تعذر إرسال الصورة
    await update.message.reply_text(formatted, reply_markup=reply_markup, parse_mode="Markdown")
    await msg.delete()
    context.user_data["state"] = None
    return ACCOUNT_VIEW

async def account_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "back_to_menu":
        return await start(update, context)
    return ACCOUNT_VIEW

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING: [CallbackQueryHandler(button_callback)],
            TYPING_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_username),
                CallbackQueryHandler(button_callback)
            ],
            ACCOUNT_VIEW: [CallbackQueryHandler(account_view_callback)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == "__main__":
    main()
