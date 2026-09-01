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

# تعريف الحالات لتنظيم تدفق المحادثة والأزرار المتفرعة
CHOOSING, TYPING_USERNAME, ACCOUNT_VIEW = range(3)

# إعداد التسجيل
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# توكن البوت
BOT_TOKEN = "8955349729:AAG0JdkQ5gyFd-IPqjjDJHlj1xtLXiNFjBY"

# ========== دوال جلب البيانات من تيك توك ==========
def clean_url(url: str) -> str:
    if not url:
        return url
    return url.replace("\\/", "/").replace("\\u002F", "/")

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
            
            video_urls = re.findall(r'"playAddr":"([^"]+)"', json_text)
            if video_urls:
                user_data["video_urls"] = [clean_url(v) for v in video_urls[:5]]
            
            if "avatarLarger" in user_data:
                user_data["avatarLarger"] = clean_url(user_data["avatarLarger"])
            
            if user_data:
                break

    return user_data if user_data else None

def format_user_data(username: str, data: dict) -> str:
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

# ========== دوال التنقل والأزرار التفاعلية ==========
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
            "🛡️ معلومات الدخول (إيميل/رقم) خاصة بالمستخدم ولا يمكن جلبها نهائياً من الواجهة العامة لأي حساب.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CHOOSING

    elif data == "country_info":
        keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back_to_menu")]]
        await query.message.edit_text(
            "🌍 معلومات الدولة تظهر إن كانت متاحة في السجلات العامة، وغالباً ما يخفيها المستخدمون.",
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
    await update.message.reply_text(f"⏳ جاري جلب بيانات الحساب الحقيقية لـ @{username} ...")

    data = fetch_tiktok_data(username)
    if not data:
        keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back_to_menu")]]
        await update.message.reply_text(
            f"⚠️ تعذر جلب بيانات الحساب @{username}. تأكد من صحة اليوزر وأن الحساب ليس خاصاً.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data["state"] = None
        return CHOOSING

    context.user_data["account_data"] = data
    context.user_data["current_username"] = username

    formatted = format_user_data(username, data)

    # أزرار متفرعة بعد فحص الحساب
    keyboard = [
        [InlineKeyboardButton("📖 عرض الاستوريات / الفيديوهات", callback_data="show_stories")],
        [InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back_to_menu")],
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
    data = query.data

    if data == "back_to_menu":
        return await start(update, context)

    elif data == "show_stories":
        account_data = context.user_data.get("account_data", {})
        video_urls = account_data.get("video_urls", [])
        
        if not video_urls:
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_menu")]]
            await query.message.edit_text("⚠️ لا توجد فيديوهات/استوريات متاحة لهذا الحساب.", reply_markup=InlineKeyboardMarkup(keyboard))
            return ACCOUNT_VIEW

        # عرض أول فيديو كمثال مع أزرار التنقل (التالي، السابق، الرجوع)
        context.user_data["stories"] = video_urls
        context.user_data["story_index"] = 0
        
        await send_story_message(update, context)
        return ACCOUNT_VIEW

    return ACCOUNT_VIEW

async def send_story_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    stories = context.user_data.get("stories", [])
    index = context.user_data.get("story_index", 0)
    
    if not stories:
        return

    video_url = stories[index]
    total = len(stories)

    keyboard = [
        [
            InlineKeyboardButton("◀️ السابق", callback_data="prev_story"),
            InlineKeyboardButton(f"{index+1}/{total}", callback_data="noop"),
            InlineKeyboardButton("التالي ▶️", callback_data="next_story"),
        ],
        [InlineKeyboardButton("🔙 رجوع لملف الحساب", callback_data="back_to_account")],
    ]
    
    # بما أن الـ callback query يعرض فيديو أو رسالة جديدة
    await query.message.reply_video(
        video=video_url,
        caption=f"🎬 فيديو رقم {index+1} من {total}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========== التشغيل الرئيسي ==========
def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING: [
                CallbackQueryHandler(button_callback, pattern="^(check_account|login_info|country_info|back_to_menu)$")
            ],
            TYPING_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_username),
                CallbackQueryHandler(button_callback)
            ],
            ACCOUNT_VIEW: [
                CallbackQueryHandler(account_view_callback)
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
        ],
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name> == "__main__":
    main()
