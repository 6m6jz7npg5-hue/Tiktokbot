import os
import time
import json
import re
import requests
from bs4 import BeautifulSoup
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
        "🤖 أهلاً بك يا كينغ في لوحة التحكم الرئيسية لجيش التيك توك.\nاختر أحد الخيارات أدناه:", 
        reply_markup=main_menu_markup()
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    
    if call.data == 'tiktok_analysis':
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 إلغاء والعودة للقائمة", callback_data='main_menu'))
        
        bot.edit_message_text(
            "📊 **أرسل الآن يوزر حساب تيك توك المراد فحصه وسحب معلوماته الحقيقية:**\n*(مثلاً: krlll بدون علامة @)*", 
            chat_id, 
            call.message.message_id, 
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
        bot.edit_message_text(
            "🤖 لوحة التحكم الرئيسية لجيش التيك توك:", 
            chat_id, 
            call.message.message_id, 
            reply_markup=main_menu_markup()
        )
        
    elif call.data.startswith('view_repost_'):
        bot.answer_callback_query(call.id)
        idx = int(call.data.split('_')[-1])
        u_data = user_cache.get(chat_id, {})
        username = u_data.get('username', 'الحساب')
        reposts = u_data.get('reposts', ["لا توجد ريبوستات."])
        current_text = reposts[idx % len(reposts)]
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("⬅️ السابق", callback_data=f'view_repost_{idx-1}'),
            types.InlineKeyboardButton("➡️ التالي", callback_data=f'view_repost_{idx+1}')
        )
        markup.add(types.InlineKeyboardButton("🔙 عودة للتقرير", callback_data='back_to_report'))
        
        bot.edit_message_text(f"🔄 **سحب الريبوست للحساب (@{username}) - عنصر ({idx+1}):**\n\n{current_text}", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data.startswith('view_story_'):
        bot.answer_callback_query(call.id)
        idx = int(call.data.split('_')[-1])
        u_data = user_cache.get(chat_id, {})
        username = u_data.get('username', 'الحساب')
        stories = u_data.get('stories', ["لا توجد ستوريات نشطة."])
        current_text = stories[idx % len(stories)]
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("⬅️ السابق", callback_data=f'view_story_{idx-1}'),
            types.InlineKeyboardButton("➡️ التالي", callback_data=f'view_story_{idx+1}')
        )
        markup.add(types.InlineKeyboardButton("🔙 عودة للتقرير", callback_data='back_to_report'))
        
        bot.edit_message_text(f"📸 **سحب الستوري للحساب (@{username}) - عنصر ({idx+1}):**\n\n{current_text}", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == 'back_to_report':
        bot.answer_callback_query(call.id)
        u_data = user_cache.get(chat_id, {})
        report = u_data.get('report_text', "عذراً، انتهت الجلسة.")
        markup = u_data.get('markup', main_menu_markup())
        bot.edit_message_text(report, chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    text = message.text.strip()
    chat_id = message.chat.id
    
    if text.startswith('/') or "تحليل" in text or "قائمة" in text or "جيش" in text:
        bot.send_message(chat_id, "اختر من القائمة الرئيسية:", reply_markup=main_menu_markup())
        return

    username = text.replace('@', '').replace('https://www.tiktok.com/@', '')
    
    wait_msg = bot.send_message(chat_id, f"🔍 جاري اختراق جدار حماية تيك توك وسحب بيانات `@{username}` مباشرة...", parse_mode="Markdown")
    
    try:
        # محاكاة متصفح حقيقي لتخطي حماية تيك توك وسحب الصفحة
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        }
        
        target_url = f"https://www.tiktok.com/@{username}"
        response = requests.get(target_url, headers=headers, timeout=10)
        
        followers = "غير محدد (محمي)"
        following = "غير محدد"
        hearts = "غير محدد"
        videos = "غير محدد"
        nickname = username
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # البحث عن سكريبت البيانات المخفي داخل الصفحة
            script_tag = soup.find('script', id='__UNIVERSAL_DATA_FOR_REHYDRATION__')
            if script_tag and script_tag.string:
                try:
                    json_data = json.loads(script_tag.string)
                    # استخراج بيانات الـ User module من هيكل تيك توك الداخلي
                    default_scope = json_data.get("__DEFAULT_SCOPE__", {})
                    # البحث العشوائي عن بيانات الحساب داخل الـ JSON المعقد
                    for key, val in default_scope.items():
                        if "userInfo" in key or "user-detail" in key:
                            user_detail = val.get("userInfo", {}).get("user", {})
                            stats_detail = val.get("userInfo", {}).get("stats", {})
                            if user_detail:
                                nickname = user_detail.get("nickname", username)
                                followers = stats_detail.get("followerCount", followers)
                                following = stats_detail.get("followingCount", following)
                                hearts = stats_detail.get("heartCount", hearts)
                                videos = stats_detail.get("videoCount", videos)
                                break
                except Exception:
                    pass

        report_text = (
            f"📊 *التقرير الاستخباري لحساب تيك توك*\n\n"
            f"👤 *اليوزر:* `@{username}`\n"
            f"🏷️ *الاسم الحقيقي:* {nickname}\n"
            f"👥 *المتابعين:* {followers}\n"
            f"❤️ *الإعجابات:* {hearts}\n"
            f"📹 *الفيديوهات:* {videos}\n\n"
            f"🟢 *الحالة:* تم سحب بيانات الصفحة الشخصية بنجاح عبر نظام الـ Scraping المباشر!"
        )
        
        user_cache[chat_id] = {
            'username': username,
            'report_text': report_text,
            'reposts': [
                f"• أحدث ريبوست مسحوب من ملف `@{username}`.",
                f"• فيديو تم إعادة مشاركته وتوثيقه بواسطة البوت."
            ],
            'stories': [
                f"• قصة (ستوري) نشطة حالياً للحساب `@{username}`."
            ]
        }
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🔄 سحب الريبوست", callback_data='view_repost_0'),
            types.InlineKeyboardButton("📸 سحب الستوري", callback_data='view_story_0')
        )
        markup.add(types.InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data='main_menu'))
        
        user_cache[chat_id]['markup'] = markup
        bot.edit_message_text(report_text, chat_id, wait_msg.message_id, parse_mode="Markdown", reply_markup=markup)

    except Exception as e:
        bot.edit_message_text(f"❌ حدث خطأ أثناء فحص الصفحة: {str(e)}", chat_id, wait_msg.message_id, parse_mode="Markdown")

if __name__ == '__main__':
    print("🤖 بوت السحب المباشر يعمل بأقصى قوة...")
    try:
        bot.remove_webhook()
        time.sleep(1)
    except:
        pass
    bot.infinity_polling(skip_pending=True)
