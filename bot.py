import os
import telebot
from telebot import types

TOKEN = '8937971566:AAHx4iLorg1ZFi1ssT6bCpDQSzl7wWintIY'
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_analysis = types.InlineKeyboardButton("📊 تحليل حساب التيك توك", callback_data='tiktok_analysis')
    btn_bots = types.InlineKeyboardButton("🤖 زر البوتات", callback_data='bots_menu')
    markup.add(btn_analysis, btn_bots)
    
    bot.send_message(
        message.chat.id, 
        "🤖 أهلاً بك يا كينغ في لوحة التحكم الرئيسية.\nاختر أحد الخيارات أدناه:", 
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
        btn_single = types.InlineKeyboardButton("⚙️ تحكم بحساب بوت منفصل", callback_data='single_bot_ctrl')
        btn_back = types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='main_menu')
        
        markup.add(btn1, btn2, btn3, btn4, btn5, btn_single, btn_back)
        bot.edit_message_text(
            "🤖 **قائمة البوتات والخدمات:**\nاختر القسم المطلوب:", 
            call.message.chat.id, 
            call.message.message_id, 
            reply_markup=markup
        )
        
    elif call.data == 'main_menu':
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_analysis = types.InlineKeyboardButton("📊 تحليل حساب التيك توك", callback_data='tiktok_analysis')
        btn_bots = types.InlineKeyboardButton("🤖 زر البوتات", callback_data='bots_menu')
        markup.add(btn_analysis, btn_bots)
        
        bot.edit_message_text(
            "🤖 القائمة الرئيسية:", 
            call.message.chat.id, 
            call.message.message_id, 
            reply_markup=markup
        )
        
    elif call.data in ['bot_msgs', 'bot_comments', 'bot_likes', 'bot_follows', 'bot_views']:
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️ تم اختيار القسم، جاري التفعيل...")
        
    elif call.data == 'single_bot_ctrl':
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "⚙️ أرسل معرف حساب البوت المنفصل للتحكم به:")

if __name__ == '__main__':
    print("🤖 البوت يعمل سحابياً...")
    bot.infinity_polling()
