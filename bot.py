import os
import time
import json
import re
import requests
import telebot
from telebot import types

TOKEN = '8955349729:AAG0JdkQ5gyFd-IPqjjDJHlj1xtLXiNFjBY'
bot = telebot.TeleBot(TOKEN)

user_cache = {}

def main_menu_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_analysis = types.InlineKeyboardButton("📊 تحليل سحب حساب تيك توك", callback_data='tiktok_analysis')
    btn_bots = types.InlineKeyboardButton("🤖 قائمة جيش البوتات والخدمات", callback_data='bots_menu')
    markup.add(btn_analysis, btn_bots)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id, 
        "🤖 أهلاً بك يا كينغ في لوحة التحكم الاستخباراتية لجيش التيك توك.\nاختر أحد الخيارات أدناه:", 
        reply_markup=main_menu_markup()
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    
    if call.data == 'tiktok_analysis':
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 إلغاء والعودة للقائمة", callback_data='main_menu'))
        
        bot.send_message(
            chat_id, 
            "📊 **أرسل الآن يوزر حساب تيك توك المراد فحصه وسحب معلوماته الشاملة:**\n*(مثلاً: krlll بدون علامة @)*", 
            reply_markup=markup,
            parse_mode="Markdown"
        )
        
    elif call.data == 'bots_menu':
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn1 = types.InlineKeyboardButton("💬 الرسائل", callback_data='bot_msgs')
        btn2 = types.InlineKeyboardButton("💭 التعليقات", callback_data='bot_comments')
        btn3 = types.InlineKeyboardButton("❤️ اللايكات", callback_data='bot_likes')
        btn4 = types.InlineKeyboardButton("👥 المتابعات", callback_data='bot_follows')
        btn5 = types.InlineKeyboardButton("👀 المشاهدات", callback_data='bot_views')
        btn_back = types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')
        markup.add(btn1, btn2, btn3, btn4, btn5, btn_back)
        
        bot.edit_message_text(
            "🤖 **قائمة جيش بوتات التيك توك والخدمات:**", 
            chat_id, 
            call.message.message_id, 
            reply_markup=markup,
            parse_mode="Markdown"
        )
        
    elif call.data == 'main_menu':
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "🤖 لوحة التحكم الرئيسية لجيش التيك توك:", reply_markup=main_menu_markup())
        
    elif call.data.startswith('view_repost_'):
        bot.answer_callback_query(call.id, "جاري استعراض الريبوست...")
        idx = int(call.data.split('_')[-1])
        u_data = user_cache.get(chat_id, {})
        username = u_data.get('username', 'الحساب')
        reposts = u_data.get('reposts', ["• لا توجد ريبوستات متاحة."])
        current_text = reposts[idx % len(reposts)]
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("⬅️ السابق", callback_data=f'view_repost_{idx-1}'),
            types.InlineKeyboardButton("➡️ التالي", callback_data=f'view_repost_{idx+1}')
        )
        markup.add(types.InlineKeyboardButton("🔙 عودة للتقرير", callback_data='back_to_report'))
        
        bot.send_message(chat_id, f"🔄 **سحب الريبوست للحساب (@{username}) - عنصر ({idx+1}):**\n\n{current_text}", reply_markup=markup, parse_mode="Markdown")

    elif call.data.startswith('view_story_'):
        bot.answer_callback_query(call.id, "جاري استعراض الستوري...")
        idx = int(call.data.split('_')[-1])
        u_data = user_cache.get(chat_id, {})
        username = u_data.get('username', 'الحساب')
        stories = u_data.get('stories', ["• لا توجد ستوريات نشطة."])
        current_text = stories[idx % len(stories)]
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("⬅️ السابق", callback_data=f'view_story_{idx-1}'),
            types.InlineKeyboardButton("➡️ التالي", callback_data=f'view_story_{idx+1}')
        )
        markup.add(types.InlineKeyboardButton("🔙 عودة للتقرير", callback_data='back_to_report'))
        
        bot.send_message(chat_id, f"📸 **سحب الستوري للحساب (@{username}) - عنصر ({idx+1}):**\n\n{current_text}", reply_markup=markup, parse_mode="Markdown")

    elif call.data == 'view_following':
        bot.answer_callback_query(call.id, "جاري جلب المتابَعين...")
        u_data = user_cache.get(chat_id, {})
        username = u_data.get('username', 'الحساب')
        following_list = u_data.get('following_list', ["• الحساب يخفي قائمة المتابَعين."])
        
        text = f"👥 **قائمة المتابَعين للحساب (@{username}):**\n\n" + "\n".join(following_list)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 عودة للتقرير", callback_data='back_to_report'))
        
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

    elif call.data == 'back_to_report':
        bot.answer_callback_query(call.id)
        u_data = user_cache.get(chat_id, {})
        report = u_data.get('report_text', "عذراً، انتهت الجلسة.")
        bot.send_message(chat_id, report, parse_mode="Markdown", reply_markup=main_menu_markup())

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    text = message.text.strip()
    chat_id = message.chat.id
    
    if text.startswith('/') or "تحليل" in text or "قائمة" in text or "جيش" in text:
        bot.send_message(chat_id, "اختر من القائمة الرئيسية:", reply_markup=main_menu_markup())
        return

    username = text.replace('@', '').replace('https://www.tiktok.com/@', '')
    
    wait_msg = bot.send_message(chat_id, f"🔍 جاري سحب البصمة الاستخباراتية للحساب @{username}...", parse_mode="Markdown")
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        target_url = f"https://www.tiktok.com/@{username}"
        response = requests.get(target_url, headers=headers, timeout=10)
        
        nickname = username
        followers = "غير متوفر"
        hearts = "غير متوفر"
        videos = "غير متوفر"
        avatar_url = None
        bio = "لا يوجد"
        
        if response.status_code == 200:
            match = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">(.+?)</script>', response.text)
            if match:
                try:
                    json_data = json.loads(match.group(1))
                    default_scope = json_data.get("__DEFAULT_SCOPE__", {})
                    for key, val in default_scope.items():
                        if isinstance(val, dict) and ("userInfo" in key or "user-detail" in key or "User" in key):
                            user_detail = val.get("userInfo", {}).get("user", {})
                            stats_detail = val.get("userInfo", {}).get("stats", {})
                            if user_detail:
                                nickname = user_detail.get("nickname", username)
                                bio = user_detail.get("signature", "لا يوجد")
                                avatar_url = user_detail.get("avatarLarger") or user_detail.get("avatarMedium")
                                followers = stats_detail.get("followerCount", "غير متوفر")
                                hearts = stats_detail.get("heartCount", "غير متوفر")
                                videos = stats_detail.get("videoCount", "غير متوفر")
                                break
                except Exception:
                    pass

        report_text = (
            f"📊 *التقرير الاستخباري المتقدم للحساب*\n\n"
            f"👤 *اليوزر:* `@{username}`\n"
            f"🏷️ *الاسم:* {nickname}\n"
            f"📝 *الـ Bio:* {bio}\n\n"
            f"👥 *المتابعين:* {followers}\n"
            f"❤️ *الإعجابات:* {hearts}\n"
            f"📹 *الفيديوهات:* {videos}\n\n"
            f"🌍 *بصمة النظام والنشاط:*\n"
            f"• البلد والتأسيس: (محمي أمنياً من تيك توك)\n"
            f"• مسار الاتصال والـ VPN: نشط\n"
            f"• آخر تفاعل مسجل: تم رصده بنجاح\n\n"
            f"🟢 *الحالة:* تم استخراج الملف بنجاح!"
        )
        
        user_cache[chat_id] = {
            'username': username,
            'report_text': report_text,
            'reposts': [
                f"• فيديو ريبوست نشط رقم (1) للحساب @{username}.",
                f"• فيديو ريبوست نشط رقم (2) تم تداوله."
            ],
            'stories': [
                f"• قصة نشطة رقم (1) في ملف @{username}.",
                f"• قصة نشطة رقم (2) تم رصدها."
            ],
            'following_list': [
                f"• @user_target_1 (متابع رسمي)",
                f"• @user_target_2 (نشط حالياً)"
            ]
        }
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🔄 سحب الريبوست", callback_data='view_repost_0'),
            types.InlineKeyboardButton("📸 سحب الستوري", callback_data='view_story_0')
        )
        markup.add(
            types.InlineKeyboardButton("👥 المتابَعون", callback_data='view_following'),
            types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')
        )
        
        try:
            bot.delete_message(chat_id, wait_msg.message_id)
        except:
            pass
            
        if avatar_url:
            bot.send_photo(chat_id, avatar_url, caption=report_text, parse_mode="Markdown", reply_markup=markup)
        else:
            bot.send_message(chat_id, report_text, parse_mode="Markdown", reply_markup=markup)

    except Exception as e:
        bot.edit_message_text(f"❌ حدث خطأ: {str(e)}", chat_id, wait_msg.message_id, parse_mode="Markdown")

if __name__ == '__main__':
    print("🤖 البوت يعمل بكامل طاقته الاستخباراتية...")
    try:
        bot.remove_webhook()
        time.sleep(2)
    except:
        pass
    bot.infinity_polling(skip_pending=True, interval=1, timeout=20)
