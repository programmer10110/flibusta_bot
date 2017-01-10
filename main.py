import telebot  # https://github.com/eternnoir/pyTelegramBotAPI
from telebot import types
import re
import requests
import transliterate  # https://github.com/barseghyanartur/transliterate
import os
import zipfile
import time
import logging
import flask

import config
from catalog import Library

ELEMENTS_ON_PAGE = 10

bot = telebot.TeleBot(config.TOKEN)
lib = Library()

telebot.logger.setLevel(logging.DEBUG)


app = flask.Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def index():
    return ''


@app.route('/status', methods=['GET'])
def status():
    return 'OK!'


@app.route(config.WEBHOOK_URL_PATH, methods=['POST'])
def webhook():
    if flask.request.headers.get('content-type') == 'application/json':
        json_string = flask.request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        flask.abort(403)


def get_keyboard(page, pages, t):
    if pages == 1:
        return None
    keyboard = types.InlineKeyboardMarkup()
    if page == 1:
        keyboard.row(types.InlineKeyboardButton('>>>', callback_data=f'{t}_2'))
    elif page == pages:
        keyboard.row(types.InlineKeyboardButton(f'<<<', callback_data=f'{t}_{pages-1}'))
    else:
        keyboard.row(types.InlineKeyboardButton(f'<<<', callback_data=f'{t}_{page-1}'),
                     types.InlineKeyboardButton(f'>>>', callback_data=f'{t}_{page+1}'))
    return keyboard


@bot.message_handler(commands=['start'])
def start(msg):
    try:
        _, rq = msg.text.split(' ')
    except ValueError:
        start_msg = ("Привет!\n"
                     "Этот бот поможет тебе загружать книги с флибусты.\n"
                     "Набери /help что бы получить помощь.\n"
                     "Информация о боте /info.\n")
        bot.reply_to(msg, start_msg)
    else:
        type_, id_ = rq.split('_')
        download(msg, type_, book_id=int(id_))


@bot.message_handler(commands=['help'])
def help_foo(msg):
    help_msg = ("Лучше один раз увидеть, чем сто раз услышать.\n"
                "https://youtu.be/V8XHzRSRcWk")
    bot.reply_to(msg, help_msg)


@bot.message_handler(commands=['info'])
def info(msg):
    info_msg = (f"Каталог книг от {config.DB_DATE}\n"
                "Связь с создателем проекта @kurbezz\n"
                f"Версия бота {config.VERSION}\n"
                "Github: https://goo.gl/V0Iw7m")
    bot.reply_to(msg, info_msg, disable_web_page_preview=True)


@bot.callback_query_handler(func=lambda x: re.search(r'b_([0-9])+', x.data) is not None)
def search_by_title(callback):
    msg = callback.message
    books = lib.book_by_title(msg.reply_to_message.text)
    try:
        _, page = callback.data.split('_')
    except ValueError as err:
        print(f"{time.strftime('%H:%M:%S')} {err} | ", end='')
        print('Callback.data = ' + callback.data)
        return
    page = int(page)
    if not books:
        bot.edit_message_text('Книги не найдены!', chat_id=msg.chat.id, message_id=msg.message_id)
        return
    bot.send_chat_action(msg.chat.id, 'typing')
    if len(books) % ELEMENTS_ON_PAGE == 0:
        page_max = len(books) // ELEMENTS_ON_PAGE
    else:
        page_max = len(books) // ELEMENTS_ON_PAGE + 1
    msg_text = ''
    for book in books[ELEMENTS_ON_PAGE * (page - 1):ELEMENTS_ON_PAGE * page]:
        msg_text += book.to_send
    msg_text += f'<code>Страница {page}/{page_max}</code>'
    keyboard = get_keyboard(page, page_max, 'b')
    if keyboard:
        bot.edit_message_text(msg_text, chat_id=msg.chat.id, message_id=msg.message_id, parse_mode='HTML',
                              reply_markup=keyboard)
    else:
        bot.edit_message_text(msg_text, chat_id=msg.chat.id, message_id=msg.message_id, parse_mode='HTML')


@bot.callback_query_handler(func=lambda x: re.search(r'ba_([0-9])+', x.data) is not None)
def books_by_author(callback):
    msg = callback.message
    _, id_ = msg.reply_to_message.text.split('_')
    id_ = int(id_)
    _, page = callback.data.split('_')
    page = int(page)
    books = lib.book_by_author(id_)
    bot.send_chat_action(msg.chat.id, 'typing')
    if len(books) % ELEMENTS_ON_PAGE == 0:
        page_max = len(books) // ELEMENTS_ON_PAGE
    else:
        page_max = len(books) // ELEMENTS_ON_PAGE + 1
    msg_text = ''
    for book in books[ELEMENTS_ON_PAGE * (page - 1):ELEMENTS_ON_PAGE * page]:
        msg_text += book.to_send
    msg_text += f'<code>Страница {page}/{page_max}</code>'
    keyboard = get_keyboard(page, page_max, 'ba')
    if keyboard:
        bot.edit_message_text(msg_text, chat_id=msg.chat.id, message_id=msg.message_id, parse_mode='HTML',
                              reply_markup=keyboard)
    else:
        bot.edit_message_text(msg_text, chat_id=msg.chat.id, message_id=msg.message_id, parse_mode='HTML')


@bot.callback_query_handler(func=lambda x: re.search(r'a_([0-9])+', x.data) is not None)
def search_by_authors(callback):
    msg = callback.message
    authors = lib.author_by_name(msg.reply_to_message.text)
    _, page = callback.data.split('_')
    page = int(page)
    if not authors:
        bot.send_message(msg.chat.id, 'Автор не найден!')
        return
    bot.send_chat_action(msg.chat.id, 'typing')
    if len(authors) % ELEMENTS_ON_PAGE == 0:
        page_max = len(authors) // ELEMENTS_ON_PAGE
    else:
        page_max = len(authors) // ELEMENTS_ON_PAGE + 1
    msg_text = ''
    for author in authors:
        msg_text += author.to_send
    msg_text += f'<code>Страница {page}/{page_max}</code>'
    keyboard = get_keyboard(page, page_max, 'a')
    if keyboard:
        bot.edit_message_text(msg_text, chat_id=msg.chat.id, message_id=msg.message_id, parse_mode='HTML',
                              reply_markup=keyboard)
    else:
        bot.edit_message_text(msg_text, chat_id=msg.chat.id, message_id=msg.message_id, parse_mode='HTML')


@bot.message_handler(regexp='/a_([0-9])+')
def books_by_author(msg):
    _, id_ = msg.text.split('_')
    id_ = int(id_)
    books = lib.book_by_author(id_)
    if not books:
        bot.reply_to(msg, 'Ошибка! Книги не найдены!')
        return
    bot.send_chat_action(msg.chat.id, 'typing')
    if len(books) % ELEMENTS_ON_PAGE == 0:
        page_max = len(books) // ELEMENTS_ON_PAGE
    else:
        page_max = len(books) // ELEMENTS_ON_PAGE + 1
    msg_text = ''
    for book in books[0:ELEMENTS_ON_PAGE]:
        msg_text += book.to_send
    msg_text += f'<code>Страница {1}/{page_max}</code>'
    keyboard = get_keyboard(1, page_max, 'ba')
    if keyboard:
        bot.reply_to(msg, msg_text, parse_mode='HTML', reply_markup=keyboard)
    else:
        bot.reply_to(msg, msg_text, parse_mode='HTML')


@bot.message_handler(regexp='^/fb2_([0-9])+$')
def download_fb2(message):
    return download(message, 'fb2')


@bot.message_handler(regexp='^/epub_([0-9])+$')
def download_epub(message):
    return download(message, 'epub')


@bot.message_handler(regexp='^/mobi_([0-9])+$')
def download_mobi(message):
    return download(message, 'mobi')


@bot.message_handler(regexp='^/djvu_([0-9])+$')
def download_djvu(message):
    return download(message, 'djvu')


@bot.message_handler(regexp='^/pdf_([0-9])+$')
def download_pdf(message):
    return download(message, 'pdf')


def download(msg, type_, book_id=None):
    if not book_id:
        _, book_id = msg.text.split('_')
        book_id = int(book_id)
    try:
        r = requests.get(f"http://flibusta.is/b/{book_id}/{type_}")
    except requests.exceptions.ConnectionError as err:
        telebot.logger.exception(err)
        return
    if '<!DOCTYPE html' in str(r.content[:100]):
        try:
            r = requests.get(f"http://flibustahezeous3.onion/b/{book_id}/{type_}",
                             proxies=config.PROXIES)
        except requests.exceptions.ConnectionError as err:
            telebot.logger.exception(err)
            bot.reply_to(msg, "Ошибка подключения к серверу! Попробуйте позднее.")
            return
    if '<!DOCTYPE html' in str(r.content[:100]):
        bot.reply_to(msg, 'Ошибка!')
        return
    book = lib.book_by_id(book_id)
    if not book:
        bot.reply_to(msg, 'Книга не найдена!')
        return
    bot.send_chat_action(msg.chat.id, 'upload_document')
    filename = ''
    caption = ''
    if book.author:
        if book.author.short:
            filename += f'{book.author.short}_-_'.replace(' ', '_')
            caption += book.author.normal_name
    filename += f'{book.title}.{type_}'.replace(' ', '_').replace('/', '_').replace(',', '')
    filename = transliterate.translit(filename, 'ru', reversed=True)
    caption += '\n' + book.title
    with open(filename, 'wb') as f:
        f.write(r.content)
    if type_ == 'fb2':
        os.rename(filename, filename.replace('.fb2', '.zip'))
        try:
            zip_obj = zipfile.ZipFile(filename.replace('.fb2', '.zip'))
        except zipfile.BadZipFile as err:
            print(err)
            return
        extracted = zip_obj.namelist()[0]
        zip_obj.extract(extracted)
        zip_obj.close()
        os.rename(extracted, filename)
        os.remove(filename.replace('.fb2', '.zip'))
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton('Поделиться',
                                   switch_inline_query=f"share_{book_id}"))
    bot.send_document(msg.chat.id, open(filename, 'rb'), reply_to_message_id=msg.message_id,
                      caption=caption, reply_markup=markup)
    try:
        os.remove(filename)
    except FileNotFoundError:
        pass


@bot.inline_handler(func=lambda x: re.search(r'share_([0-9])+$', x.query) is not None)
def inline_share(query):
    _, book_id = query.query.split('_')
    result = list()
    book = lib.book_by_id(book_id)
    if not book:
        return
    result.append(types.InlineQueryResultArticle('1', 'Поделиться',
                                                 types.InputTextMessageContent(book.to_share, parse_mode='HTML',
                                                                               disable_web_page_preview=True)))
    bot.answer_inline_query(query.id, result)


@bot.inline_handler(func=lambda query: query.query)
def inline_hand(query):
    books = lib.book_by_title(query.query)
    if not books:
        return
    index = 1
    result = list()
    for book in books[0:min(len(books)-1, 50-1)]:
        result.append(types.InlineQueryResultArticle(str(index), book.title,
                                                     types.InputTextMessageContent(book.to_share, parse_mode='HTML',
                                                                                   disable_web_page_preview=True)))
        index += 1
    bot.answer_inline_query(query.id, result)


@bot.message_handler(func=lambda message: True)
def search(msg):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton('По названию', callback_data='b_1'),
                 types.InlineKeyboardButton('По авторам', callback_data='a_1')
                 )
    bot.reply_to(msg, 'Поиск: ', reply_markup=keyboard)


bot.remove_webhook()

time.sleep(0.5)

bot.set_webhook(url=config.WEBHOOK_URL_BASE + config.WEBHOOK_URL_PATH,
                certificate=open(config.WEBHOOK_SSL_CERT, 'r'))


app.run(host=config.WEBHOOK_LISTEN,
        port=config.WEBHOOK_PORT,
        ssl_context=(config.WEBHOOK_SSL_CERT, config.WEBHOOK_SSL_PRIV),
        debug=True)
