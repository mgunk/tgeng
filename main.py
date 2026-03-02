import os
import random
from dotenv import load_dotenv
from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup
from model import Session, User, CommonWord, UserWord, create_db

load_dotenv()
create_db()

bot = TeleBot(os.getenv("BOT_TOKEN"), state_storage=StateMemoryStorage())


class Command:
    NEXT = "Дальше ⏭"
    DELETE = "Удалить слово 🗑️"
    ADD = "Добавить слово ➕"
    STAT = "Статистика 📊"


def get_main_keyboard(options):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btns = [types.KeyboardButton(opt) for opt in options]
    markup.add(*btns)
    markup.row(types.KeyboardButton(Command.NEXT), types.KeyboardButton(Command.DELETE))
    markup.row(types.KeyboardButton(Command.ADD), types.KeyboardButton(Command.STAT))
    return markup


class MyStates(StatesGroup):
    target_word = State()
    waiting_new_word = State()
    waiting_new_translate = State()


def get_user(session, chat_id):
    user = session.query(User).filter(User.chat_id == chat_id).first()
    if not user:
        user = User(chat_id=chat_id)
        session.add(user)
        session.commit()
    return user


@bot.message_handler(commands=['start', 'cards'])
@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def create_cards(message):
    cid = message.chat.id
    uid = message.from_user.id
    session = Session()
    user = get_user(session, cid)

    deleted_ids = session.query(UserWord.word_id).filter(
        UserWord.user_id == user.id,
        UserWord.is_deleted == True
    ).all()
    deleted_ids_list = [d[0] for d in deleted_ids]

    words = session.query(CommonWord).filter(~CommonWord.id.in_(deleted_ids_list)).all()

    if len(words) < 4:
        bot.send_message(cid, "Недостаточно слов! Добавьте свои через меню.")
        session.close()
        return

    target = random.choice(words)
    others = random.sample([w for w in words if w.id != target.id], 3)
    options = [w.target_word for w in others] + [target.target_word]
    random.shuffle(options)

    bot.send_message(cid, f"Как переводится: {target.translate_word}?",
                     reply_markup=get_main_keyboard(options))

    bot.set_state(uid, MyStates.target_word, cid)
    with bot.retrieve_data(uid, cid) as data:
        data['target_word'] = target.target_word
        data['target_word_id'] = target.id
        data['translate_word'] = target.translate_word
        data['options'] = options
    session.close()


@bot.message_handler(func=lambda message: message.text == Command.STAT)
def show_stats(message):
    cid = message.chat.id
    session = Session()
    user = get_user(session, cid)
    total = user.total_answers
    correct = user.correct_answers
    accuracy = (correct / total * 100) if total > 0 else 0

    stat_text = (f"📊 Статистика:\n"
                 f"Всего попыток: {total}\n"
                 f"Верно: {correct}\n"
                 f"Точность: {accuracy:.1f}%")
    bot.send_message(cid, stat_text)
    session.close()


@bot.message_handler(func=lambda message: message.text == Command.DELETE)
def delete_word(message):
    cid = message.chat.id
    uid = message.from_user.id
    with bot.retrieve_data(uid, cid) as data:
        word_id = data.get('target_word_id')

    if not word_id: return

    session = Session()
    user = get_user(session, cid)
    uw = session.query(UserWord).filter_by(user_id=user.id, word_id=word_id).first()
    if not uw:
        session.add(UserWord(user_id=user.id, word_id=word_id, is_deleted=True))
    else:
        uw.is_deleted = True
    session.commit()
    session.close()
    bot.send_message(cid, "Слово удалено!")
    create_cards(message)


@bot.message_handler(func=lambda message: message.text == Command.ADD)
def add_word_start(message):
    bot.send_message(message.chat.id, "Введите слово на английском:")
    bot.set_state(message.from_user.id, MyStates.waiting_new_word, message.chat.id)


@bot.message_handler(state=MyStates.waiting_new_word)
def add_word_name(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['new_target'] = message.text
    bot.send_message(message.chat.id, "Введите перевод:")
    bot.set_state(message.from_user.id, MyStates.waiting_new_translate, message.chat.id)


@bot.message_handler(state=MyStates.waiting_new_translate)
def add_word_finish(message):
    cid = message.chat.id
    session = Session()
    user = get_user(session, cid)
    with bot.retrieve_data(message.from_user.id, cid) as data:
        new_w = CommonWord(target_word=data['new_target'], translate_word=message.text)
        session.add(new_w)
        session.flush()
        session.add(UserWord(user_id=user.id, word_id=new_w.id))
    session.commit()
    session.close()
    bot.send_message(cid, "Добавлено!")
    create_cards(message)


@bot.message_handler(func=lambda message: True, state=MyStates.target_word)
def check_answer(message):
    cid = message.chat.id
    uid = message.from_user.id
    user_answer = message.text
    # Если нажата кнопка управления, не считаем это за ответ
    if user_answer in [Command.NEXT, Command.DELETE, Command.ADD, Command.STAT]:
        return

    session = Session()
    user = get_user(session, cid)
    with bot.retrieve_data(uid, cid) as data:
        target_word = data.get('target_word')
        options = data.get('options')
        user.total_answers += 1
        if user_answer == target_word:
            user.correct_answers += 1
            session.commit()
            bot.send_message(cid, "Правильно! ✅", reply_markup=get_main_keyboard(options))
        else:
            session.commit()
            new_options = [opt + " ❌" if opt == user_answer else opt for opt in options]
            data['options'] = new_options
            bot.send_message(cid, "Неверно! ❌", reply_markup=get_main_keyboard(new_options))
    session.close()


bot.add_custom_filter(custom_filters.StateFilter(bot))
bot.infinity_polling(skip_pending=True)