import random
from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup

# Импортируем нашу базу данных
from model import Session, CommonWord, UserWord, get_all_words_for_user


print('Start telegram bot...')

state_storage = StateMemoryStorage()
token_bot = ''
bot = TeleBot(token_bot, state_storage=state_storage)

userStep = {}


def show_hint(*lines):
    return '\n'.join(lines)


def show_target(data):
    return f"{data['target_word']} -> {data['translate_word']}"


class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'


class MyStates(StatesGroup):
    target_word = State()
    waiting_new_word = State()
    waiting_new_translate = State()


@bot.message_handler(commands=['cards', 'start'])
def create_cards(message):
    cid = message.chat.id
    uid = message.from_user.id

    all_words = get_all_words_for_user(cid)

    if len(all_words) < 4:
        bot.send_message(cid, "У тебя слишком мало слов! Добавь хотя бы 4 слова чтобы начать")
        return

    # Выбираем случайное целевое слово
    target, translate = random.choice(all_words)
    # Выбираем 3 других случайных слова для вариантов ответа
    other_words = [w[0] for w in random.sample([w for w in all_words if w[0] != target], 3)]

    # Собираем кнопки
    buttons = []
    buttons.append(types.KeyboardButton(target))
    buttons.extend([types.KeyboardButton(word) for word in other_words])
    random.shuffle(buttons)

    buttons.extend([
        types.KeyboardButton(Command.NEXT),
        types.KeyboardButton(Command.ADD_WORD),
        types.KeyboardButton(Command.DELETE_WORD)
    ])

    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(*buttons)

    greeting = f"Выбери перевод слова:\n🇷🇺 {translate}"
    bot.send_message(cid, greeting, reply_markup=markup)

    bot.set_state(uid, MyStates.target_word, cid)
    with bot.retrieve_data(uid, cid) as data:
        data['target_word'] = target
        data['translate_word'] = translate
        data['buttons'] = buttons


@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    create_cards(message)


@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    cid = message.chat.id
    with bot.retrieve_data(message.from_user.id, cid) as data:
        word_to_delete = data['target_word']

    session = Session()
    # Помечаем слово как удалённое для этого пользователя
    exists = session.query(UserWord).filter(UserWord.user_id == cid, UserWord.word == word_to_delete).first()
    if not exists:
        session.add(UserWord(user_id=cid, word=word_to_delete, translate="", is_deleted=True))
    else:
        exists.is_deleted = True
    session.commit()
    session.close()

    bot.send_message(cid, f"Слово {word_to_delete} удалено из твоего списка")
    create_cards(message)


@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    cid = message.chat.id
    bot.send_message(cid, "Напиши английское слово которое хочешь добавить")
    bot.set_state(message.from_user.id, MyStates.waiting_new_word, cid)


@bot.message_handler(state=MyStates.waiting_new_word)
def get_new_word(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['new_word'] = message.text
    bot.send_message(message.chat.id, "А теперь напиши его перевод на русский")
    bot.set_state(message.from_user.id, MyStates.waiting_new_translate, message.chat.id)


@bot.message_handler(state=MyStates.waiting_new_translate)
def save_new_word(message):
    cid = message.chat.id
    with bot.retrieve_data(message.from_user.id, cid) as data:
        new_word = data['new_word']
        new_translate = message.text

    session = Session()
    session.add(UserWord(user_id=cid, word=new_word, translate=new_translate))
    session.commit()
    session.close()

    bot.send_message(cid, f"✅ Слово {new_word} = {new_translate} добавлено!")
    bot.delete_state(message.from_user.id, cid)
    create_cards(message)


@bot.message_handler(func=lambda message: True, content_types=['text'])
@bot.message_handler(state=MyStates.target_word, content_types=['text'])
def message_reply(message):
    text = message.text
    cid = message.chat.id
    uid = message.from_user.id

    with bot.retrieve_data(uid, cid) as data:
        # Защита если данных нет
        if 'target_word' not in data:
            create_cards(message)
            return

        target_word = data['target_word']
        buttons = data['buttons']

        if text == target_word:
            hint = show_target(data)
            hint_text = ["Отлично!❤", hint]
            hint = show_hint(*hint_text)
        else:
            for btn in buttons:
                if btn.text == text:
                    btn.text = text + '❌'
                    break
            hint = show_hint("Допущена ошибка!",
                             f"Попробуй ещё раз вспомнить слово 🇷🇺 {data['translate_word']}")

    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(*buttons)
    bot.send_message(cid, hint, reply_markup=markup)


bot.add_custom_filter(custom_filters.StateFilter(bot))

bot.infinity_polling(skip_pending=True)