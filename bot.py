import os
import telebot
from telebot import types

TOKEN = '8955349729:AAG0JdkQ5gyFd-IPqjjDJHlj1xtLXiNFjBY'
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_analysis = types.InlineKeyboardButton("📊 تحليل حساب التيك توك", callback_data='tiktok_analysis')
    btn_bots = types.InlineKeyboardButton("🤖 قائمة جيش البوتات", callback_data='bots_menu')
    markup.add(btn_analysis, btn_bots)
    
    bot.send_message(
        message.chat.id, 
        "🤖 أهلاً بك يا كينغ في لوحة التحكم الرئيسية لجيش التيك توك.\nاختر أحد الخيارات أدناه:", 
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == 'tiktok_analysis':
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📊 أرسل لي يوزر حساب التيك توك المراد تحليله الآن:")
        
    elif call.data == 'bots_menu':
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn1 = types.InlineKeyboardButton("💬 الرسائل", callback_data='bot_msgs')
        btn2 = types.InlineKeyboardButton("💭 التعليقات", callback_data='bot_comments')
        btn3 = types.InlineKeyboardButton("❤️ اللايكات", callback_data='bot_likes')
        btn4 = types.InlineKeyboardButton("👥 المتابعات", callback_data='bot_follows')
        btn5 = types.InlineKeyboardButton("👀 المشاهدات", callback_data='bot_views')
        btn_single = types.InlineKeyboardButton("⚙️ اختيار بوت من الجيش للتحكم", callback_data='single_bot_ctrl')
        btn_back = types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')
        
        markup.add(btn1, btn2, btn3, btn4, btn5, btn_single, btn_back)
        bot.edit_message_text(
            "🤖 **قائمة جيش بوتات التيك توك والخدمات:**\nاختر القسم المطلوب:", 
            call.message.chat.id, 
            call.message.message_id, 
            reply_markup=markup
        )
        
    elif call.data == 'main_menu':
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_analysis = types.InlineKeyboardButton("📊 تحليل حساب التيك توك", callback_data='tiktok_analysis')
        btn_bots = types.InlineKeyboardButton("🤖 قائمة جيش البوتات", callback_data='bots_menu')
        markup.add(btn_analysis, btn_bots)
        
        bot.edit_message_text(
            "🤖 القائمة الرئيسية:", 
            call.message.chat.id, 
            call.message.message_id, 
            reply_markup=markup
        )
        
    elif call.data in ['bot_msgs', 'bot_comments', 'bot_likes', 'bot_follows', 'bot_views']:
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️ تم اختيار القسم لجيش البوتات، جاري التنفيذ...")
        
    elif call.data == 'single_bot_ctrl':
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "🎯 **التحكم الفردي:**\nأرسل الآن معرف (ID) أو اسم بوت التيك توك المحدد من الجيش الذي ترغب بالتحكم به:")

if __name__ == '__main__':
    print("🤖 البوت يعمل سحابياً...")
    bot.infinity_polling()
