import telebot
from telebot import types
from pymongo import MongoClient
import base64
import datetime
import re
from dotenv import load_dotenv
import os


load_dotenv()

client = MongoClient(os.getenv("MONGODB_URL"))
db = client['schoolHelper']
hw_collection = db['homeworks']
users_collection = db['users']
logging_collection = db['logging']
settings_collection = db['settings']
temp_collection = db['temp']

bot = telebot.TeleBot(os.getenv("TELEBOT_TOKEN"))

HELP = '''
/help - получить это сообщение
'''

# main menu keyboard
main_menu_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
main_menu_kb.add("📗 Домашнее задание на завтра")
main_menu_kb.add("📚 Все домашние задания")
main_menu_kb.add("🗃 Архив Д/З")
main_menu_kb.row("➕ Добавить Д/З", "➖ Удалить Д/З")

# cancel keyboard
cancel_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
cancel_kb.add("❌ Отмена")

# select date keyboard
select_date_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
select_date_kb.add("▶️ Завтра")
select_date_kb.row("⏩ Послезавтра", "⏭ Через неделю")
select_date_kb.add("❌ Отмена")


@bot.message_handler(content_types=['text'])
def main(message):
    is_free_access = settings_collection.find()[0]['is_free_access']
    if not is_free_access:
        if users_collection.find_one({"user_id": message.from_user.id}) is None:
            bot.send_message(message.from_user.id, 'Доступ запрещен')
            return
    for el in users_collection.find({"is_banned": True}):
        if el['user_id'] == message.from_user.id:
            bot.send_message(message.from_user.id, 'Вы заблокированы')
            return
    
    if message.text == "/help":
        bot.send_message(message.from_user.id, HELP)
    
    elif message.text == "/start":
        if not users_collection.find_one({"user_id": message.from_user.id}):
            add_user = {
                "user_id": message.from_user.id,
                "first_name": message.from_user.first_name,
                "last_name": message.from_user.last_name,
                "username": message.from_user.username,
                "is_banned": False,
            }
            users_collection.insert_one(add_user)
        bot.send_message(message.from_user.id, HELP,
                            reply_markup=main_menu_kb)
    
    elif message.text == "📚 Все домашние задания":
        show_hws(message)
    
    elif message.text == "📗 Домашнее задание на завтра":
        show_hws_for_tomorrow(message)
    
    elif message.text == "🗃 Архив Д/З":
        show_hws_archive(message)
    
    elif message.text == "➕ Добавить Д/З":
        bot.register_next_step_handler(bot.send_message(message.from_user.id,
                                                        "Введите название предмета",
                                                        reply_markup=cancel_kb),
                                       request_add_hw_subject)
        
    elif message.text == "➖ Удалить Д/З":
        is_hws = show_hws(message)
        if is_hws:
            bot.register_next_step_handler(bot.send_message(message.from_user.id,
                                                            "Введите номер Д/З, которое нужно удалить",
                                                            reply_markup=cancel_kb),
                                           request_delete_hw_number)
    
    
    elif message.text.lower() == "ты бот":
                bot.send_message(message.from_user.id,
                                 "Ну да, и что? Зато я могу посчитать 1639^357/109. А ты нет! Ха-ха-ха!",
                                 reply_markup=main_menu_kb)


def show_hws(message):
    i = 1
    for hw_item in hw_collection.find({'date_to': {'$gte': datetime.datetime.now()}}).sort('date_to', 1):
        if isBase64(hw_item["text"]):
            hw_photo = base64.b64decode(hw_item["text"].decode())
            bot.send_photo(message.from_user.id,
                           hw_photo,
                           caption=str(i) + ") <b>" + hw_item["subject"] + "</b> (на <i>" + hw_item["date_to"].strftime("%d.%m.%Y") + "</i>)",
                           parse_mode='html',
                           reply_markup=main_menu_kb)
        else:
            mess = str(i) + ") <b>" + hw_item["subject"] + "</b> (на <i>" + \
                hw_item["date_to"].strftime("%d.%m.%Y") + "</i>):\n" + hw_item["text"]
            bot.send_message(message.from_user.id, mess,
                             parse_mode='html', reply_markup=main_menu_kb)
        i += 1
        
    if i == 1:
        bot.send_message(message.from_user.id, "Д/З не найдено",
                         reply_markup=main_menu_kb)
        return False
    return True


def show_hws_for_tomorrow(message):
    i = 1
    for hw_item in hw_collection.find({'date_to': {'$gte': datetime.datetime.now(), '$lt': datetime.datetime.now() + datetime.timedelta(days=1)}}).sort('date_to', 1):
        if isBase64(hw_item["text"]):
            hw_photo = base64.b64decode(hw_item["text"].decode())
            bot.send_photo(message.from_user.id,
                           hw_photo,
                           caption=str(i) + ") <b>" + hw_item["subject"] + "</b>",
                           parse_mode='html',
                           reply_markup=main_menu_kb)
        else:
            mess = str(i) + ") <b>" + hw_item["subject"] + "</b>:\n" + hw_item["text"]
            bot.send_message(message.from_user.id, mess,
                             parse_mode='html', reply_markup=main_menu_kb)
        i += 1
        
    if i == 1:
        bot.send_message(message.from_user.id, "Д/З на завтра не найдено",
                         reply_markup=main_menu_kb)
        return False
    return True


def show_hws_archive(message):
    i = 1
    for hw_item in hw_collection.find({'date_to': {'$lt': datetime.datetime.now()}}).sort('date_to', -1):
        if isBase64(hw_item["text"]):
            hw_photo = base64.b64decode(hw_item["text"].decode())
            bot.send_photo(message.from_user.id,
                           hw_photo,
                           caption=str(
                               i) + ") <b>" + hw_item["subject"] + "</b> (на <i>" + hw_item["date_to"].strftime("%d.%m.%Y") + "</i>)",
                           parse_mode='html',
                           reply_markup=main_menu_kb)
        else:
            mess = str(i) + ") <b>" + hw_item["subject"] + "</b> (на <i>" + \
                hw_item["date_to"].strftime(
                    "%d.%m.%Y") + "</i>):\n" + hw_item["text"]
            bot.send_message(message.from_user.id, mess,
                             parse_mode='html', reply_markup=main_menu_kb)
        i += 1

    if i == 1:
        bot.send_message(message.from_user.id, "Архив пуст",
                         reply_markup=main_menu_kb)


def isBase64(s):
    try:
        return base64.b64encode(base64.b64decode(s.decode())) == s
    except Exception:
        return False



def request_add_hw_subject(message):
    if message.text == "❌ Отмена":
        bot.send_message(message.from_user.id,
                            "Отменено", reply_markup=main_menu_kb)
        return
    
    if re.search(r'[<>]', message.text):
            bot.send_message(message.from_user.id, "Недопустимые символы в названии предмета")
            bot.register_next_step_handler(bot.send_message(message.from_user.id,
                                                            "Введите название предмета",
                                                            reply_markup=cancel_kb),
                                           request_add_hw_subject)
            return
    
    temp_collection.delete_many({"chat_id": message.from_user.id})
    temp_collection.insert_one({"chat_id": message.from_user.id,
                               "createdAt": datetime.datetime.now(), "subject": message.text})
    
    bot.register_next_step_handler(bot.send_message(message.from_user.id, "Введите Д/З или отправьте фото"),
                                    request_add_hw_text)


def request_add_hw_text(message):
    if message.content_type == "text":
        if message.text == "❌ Отмена":
            bot.send_message(message.from_user.id,
                                "Отменено", reply_markup=main_menu_kb)
            temp_collection.delete_one({"chat_id": message.from_user.id})
            return
        
        if re.search(r'[<>]', message.text):
            bot.send_message(message.from_user.id, "Недопустимые символы в тексте Д/З")
            bot.register_next_step_handler(bot.send_message(message.from_user.id, "Введите Д/З или отправьте фото"),
                                           request_add_hw_text)
            return
        
        temp_collection.update_one({"chat_id": message.from_user.id}, {"$set": {"text": message.text}})
        bot.register_next_step_handler(bot.send_message(message.from_user.id,
                                                        "Введите дату на которое задано Д/З\n(в формате дд.мм.гггг)",
                                                        reply_markup=select_date_kb),
                                        request_add_hw_date_to)

    elif message.content_type == "photo":
        file_info = bot.get_file(
            message.photo[len(message.photo) - 1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        encoded_string = base64.b64encode(downloaded_file)
        #add_hw_text = encoded_string.decode()
        
        temp_collection.update_one({"chat_id": message.from_user.id}, {"$set": {"text": encoded_string}})
        
        bot.register_next_step_handler(bot.send_message(message.from_user.id,
                                                        "Введите дату на которое задано Д/З\n(в формате дд.мм.гггг)",
                                                        reply_markup=select_date_kb),
                                        request_add_hw_date_to)
    

def request_add_hw_date_to(message):
    add_hw_date_to = ''
    if message.text == "❌ Отмена":
        temp_collection.delete_one({"chat_id": message.from_user.id})
        bot.send_message(message.from_user.id,
                            "Отменено", reply_markup=main_menu_kb)
        return

    elif message.text == "▶️ Завтра":
        add_hw_date_to = datetime.date.today() + datetime.timedelta(days=1)
        # add_hw_date_to = d.strftime("%d.%m.%Y")

    elif message.text == "⏩ Послезавтра":
        add_hw_date_to = datetime.date.today() + datetime.timedelta(days=2)

    elif message.text == "⏭ Через неделю":
        add_hw_date_to = datetime.date.today() + datetime.timedelta(days=7)

    else:
        try:
            input_date = []
            if "." in message.text:
                input_date = message.text.split(".")
            elif "/" in message.text:
                input_date = message.text.split("/")

            if len(input_date[2]) == 2:
                input_date[2] = "20" + input_date[2]
            add_hw_date_to = datetime.date(int(input_date[2]), int(input_date[1]), int(input_date[0]))

        except:
            bot.register_next_step_handler(bot.send_message(message.from_user.id,
                                                            "Введите дату на которое задано Д/З\n(в формате дд.мм.гггг)"),
                                            request_add_hw_date_to)
            return

    hw_obj = temp_collection.find_one({"chat_id": message.from_user.id})
    add_hw_subject = hw_obj["subject"]
    add_hw_text = hw_obj["text"]
    
    add_hw = {
        "subject": add_hw_subject,
        "text": add_hw_text,
        "user_id": message.from_user.id,
        "user_first_name": message.from_user.first_name,
        "user_last_name": message.from_user.last_name,
        "username": message.from_user.username,
        "date_to": datetime.datetime.combine(add_hw_date_to, datetime.time()),
    }
    hw_collection.insert_one(add_hw)
    temp_collection.delete_one({"chat_id": message.from_user.id})
    bot.send_message(message.from_user.id,
                        "Д/З добавлено", reply_markup=main_menu_kb)



def request_delete_hw_number(message):
    if message.text == "❌ Отмена":
        bot.send_message(message.from_user.id,
                            "Отменено", reply_markup=main_menu_kb)
        return
    del_hw_number = message.text
    hws = list(hw_collection.find({'date_to': {'$gte': datetime.datetime.now()}}).sort('date_to', 1))
    if int(del_hw_number) > len(hws):
        bot.register_next_step_handler(bot.send_message(message.from_user.id,
                                                        "Введите номер Д/З, которое нужно удалить",
                                                        reply_markup=cancel_kb),
                                        request_delete_hw_number)
        return
    number = int(del_hw_number)-1
    hw_collection.delete_one({"_id": hws[number]["_id"]})
    bot.send_message(message.from_user.id,
                        "Д/З удалено", reply_markup=main_menu_kb)



bot.polling(none_stop=True, interval=0)
