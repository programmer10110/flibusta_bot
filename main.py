# pyTelegramBotAPI lib
import telebot  # https://github.com/eternnoir/pyTelegramBotAPI
from telebot import types

# transcription translate lib
import transliterate  # https://github.com/barseghyanartur/transliterate

# standard libs
import os
import re
import zipfile
import time
import logging
import requests
import shutil

# yandex metric lib
import botan

# bot's modules and config files
import config
from catalog import Library
from debug_utils import timeit
from users_db import Database
from ftp_file_controller import Controller

# bot's consts
ELEMENTS_ON_PAGE = 7

bot = telebot.TeleBot(config.TOKEN)
lib = Library()
db = Database()

logger = telebot.logger

if config.DEBUG:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)


def track(uid, msg, name):  # botan tracker
    if type(msg) is types.Message:
        return botan.track(config.BOTAN_TOKEN, uid,
                           {'message': {
                               'user': {
                                   'id': msg.from_user.id,
                                   'first_name': msg.from_user.first_name,
                                   'username': msg.from_user.username,
                                   'last_name': msg.from_user.last_name
                               },
                               'text': msg.text
                           }
                           },
                           name=name)
    if type(msg) is types.CallbackQuery:
        return botan.track(config.BOTAN_TOKEN, uid,
                           {'callback_query': {
                               'user': {
                                   'id': msg.from_user.id,
                                   'first_name': msg.from_user.first_name,
                                   'username': msg.from_user.username,
                                   'last_name': msg.from_user.last_name
                               },
                               'text': msg.message.reply_to_message.text
                           }
                           },
                           name=name)
    if type(msg) is types.InlineQuery:
        return botan.track(config.BOTAN_TOKEN, uid,
                           {'inline_query': {
                               'user': {
                                   'id': msg.from_user.id,
                                   'first_name': msg.from_user.first_name,
                                   'username': msg.from_user.username,
                                   'last_name': msg.from_user.last_name
                               },
                               'query': msg.query
                           }},
                           name=name)


def normalize(book, type_):  # remove chars that don't accept in Telegram Bot API
    filename = ''
    if book.author:
        if book.author.short:
            filename += book.author.short + '_-_'
    filename += book.title
    filename = transliterate.translit(filename, 'ru', reversed=True)
    filename = filename.strip('(').strip(')').strip(',').strip('«').strip('…').strip('.')
    filename = filename.strip('’').strip('!').strip('"').strip('?').strip('»').strip("'")
    filename = filename.replace('—', '-').replace('/', '_').replace('№', 'N')
    filename = filename.replace(' ', '_').replace('–', '-')
    return filename + '.' + type_


def get_keyboard(page, pages, t):  # make keyboard for current page
    if pages == 1:
        return None
    keyboard = types.InlineKeyboardMarkup()
    if page == 1:
        keyboard.row(types.InlineKeyboardButton('⏩', callback_data=f'{t}_2'))
        if pages >= 7:
            next_l = min(pages, page+ELEMENTS_ON_PAGE)
            keyboard.row(types.InlineKeyboardButton(f'{next_l} ⏭',
                                                    callback_data=f'{t}_{next_l}'))
    elif page == pages:
        keyboard.row(types.InlineKeyboardButton('⏪', callback_data=f'{t}_{pages-1}'))
        if pages >= 7:
            previous_l = max(1, page-ELEMENTS_ON_PAGE)
            keyboard.row(types.InlineKeyboardButton(f'⏮ {previous_l}',
                                                    callback_data=f'{t}_{previous_l}'))
    else:
        keyboard.row(types.InlineKeyboardButton('⏪', callback_data=f'{t}_{page-1}'),
                     types.InlineKeyboardButton('⏩', callback_data=f'{t}_{page+1}'))
        if pages >= 7:
            next_l = min(pages, page + ELEMENTS_ON_PAGE)
            previous_l = max(1, page - ELEMENTS_ON_PAGE)
            keyboard.row(types.InlineKeyboardButton(f'⏮ {previous_l}',
                                                    callback_data=f'{t}_{previous_l}'),
                         types.InlineKeyboardButton(f'{next_l} ⏭',
                                                    callback_data=f'{t}_{next_l}')
                         )
    return keyboard


@bot.message_handler(commands=['start'])
def start(msg):
    try:  # try get data that use in user share book
        _, rq = msg.text.split(' ')
    except ValueError:
        start_msg = ("Привет!\n"
                     "Этот бот поможет тебе загружать книги с флибусты.\n"
                     "Набери /help что бы получить помощь.\n"
                     "Информация о боте /info.\n"
                     "Материальная помощь /donate\n")
        bot.reply_to(msg, start_msg)
        track(msg.from_user.id, msg, 'start')
    else:
        type_, id_ = rq.split('_')
        send_book(msg, type_, book_id=int(id_))
        track(msg.from_user.id, msg, 'get_shared_book')


@bot.message_handler(commands=['help'])
def help_foo(msg):  # send help message
    help_msg = ("Лучше один раз увидеть, чем сто раз услышать.\n"
                "https://youtu.be/HV6Wm87D6_A")
    bot.reply_to(msg, help_msg)
    track(msg.from_user.id, msg, 'help')


@bot.message_handler(commands=['info'])
def info(msg):  # send information message
    info_msg = (f"Каталог книг от {config.DB_DATE}\n"
                "Связь с создателем проекта @kurbezz\n"
                f"Версия бота {config.VERSION}\n"
                "Github: https://goo.gl/V0Iw7m")
    bot.reply_to(msg, info_msg, disable_web_page_preview=True)
    track(msg.from_user.id, msg, 'info')


@bot.callback_query_handler(func=lambda x: re.search(r'b_([0-9])+', x.data) is not None)
@timeit
def search_by_title(callback):  # search books by title
    msg = callback.message
    user_sets = db.get_lang_settings(callback.from_user.id)
    books = lib.book_by_title(msg.reply_to_message.text, user_sets)
    try:
        _, page = callback.data.split('_')
    except ValueError as err:
        print(f"{time.strftime('%H:%M:%S')} {err} | ", end='')
        print('Callback.data = ' + callback.data)
        return
    page = int(page)
    if not books:
        bot.edit_message_text('Книги не найдены!', chat_id=msg.chat.id, message_id=msg.message_id)
        track(msg.from_user.id, callback, 'search_by_title')
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
    track(msg.from_user.id, callback, 'search_by_title')


@bot.callback_query_handler(func=lambda x: re.search(r'ba_([0-9])+', x.data) is not None)
@timeit
def books_by_author(callback):  # search books by author (use callback query)
    msg = callback.message
    _, id_ = msg.reply_to_message.text.split('_')
    id_ = int(id_)
    _, page = callback.data.split('_')
    page = int(page)
    user_sets = db.get_lang_settings(callback.from_user.id)
    books = lib.book_by_author(id_, user_sets)
    if not books:
        bot.edit_message_text('Книги не найдены!', chat_id=msg.chat.id, message_id=msg.message_id)
        track(msg.from_user.id, callback, 'search_by_title')
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
    keyboard = get_keyboard(page, page_max, 'ba')
    if keyboard:
        bot.edit_message_text(msg_text, chat_id=msg.chat.id, message_id=msg.message_id, parse_mode='HTML',
                              reply_markup=keyboard)
    else:
        bot.edit_message_text(msg_text, chat_id=msg.chat.id, message_id=msg.message_id, parse_mode='HTML')
    track(msg.from_user.id, callback, 'books_by_author')


@bot.callback_query_handler(func=lambda x: re.search(r'a_([0-9])+', x.data) is not None)
@timeit
def search_by_authors(callback):  # search authors
    msg = callback.message
    authors = lib.author_by_name(msg.reply_to_message.text)
    _, page = callback.data.split('_')
    page = int(page)
    if not authors:
        bot.send_message(msg.chat.id, 'Автор не найден!')
        track(msg.from_user.id, callback, 'search_by_authors')
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
    track(msg.from_user.id, callback, 'search_by_authors')


@bot.message_handler(regexp='/a_([0-9])+')
@timeit
def books_by_author(msg):  # search books by author (use messages)
    _, id_ = msg.text.split('_')
    id_ = int(id_)
    user_sets = db.get_lang_settings(msg.from_user.id)
    books = lib.book_by_author(id_, user_sets)
    if not books:
        bot.reply_to(msg, 'Ошибка! Книги не найдены!')
        track(msg.from_user.id, msg, 'books_by_author')
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
    track(msg.from_user.id, msg, 'books_by_author')


@bot.message_handler(commands=['donate'])
def donation(msg):  # send donation information
    text = "О том, как поддержать проект можно узнать "
    text += '<a href="http://telegra.ph/Pozhertvovaniya-02-11">тут</a>.'
    bot.reply_to(msg, text, parse_mode='HTML')


@bot.message_handler(regexp='^/fb2_([0-9])+$')
def send_fb2(message):  # fb2 books handler
    return send_book(message, 'fb2')


@bot.message_handler(regexp='^/epub_([0-9])+$')
def send_epub(message):  # epub books handler
    return send_book(message, 'epub')


@bot.message_handler(regexp='^/mobi_([0-9])+$')
def send_mobi(message):  # mobi books handler
    return send_book(message, 'mobi')


@bot.message_handler(regexp='^/djvu_([0-9])+$')
def send_djvu(message):  # djvu books handler
    return send_book(message, 'djvu')


@bot.message_handler(regexp='^/pdf_([0-9])+$')
def send_pdf(message):  # pdf books handler
    return send_book(message, 'pdf')


@bot.message_handler(regexp='^/doc_([0-9])+$')
def send_doc(message):  # doc books handler
    return send_book(message, 'doc')


def send_by_file_id(foo):  # try to send document by file_id
    def try_send(msg, type_, book_id=None):
        if not book_id:
            _, book_id = msg.text.split('_')
            book_id = int(book_id)
        file_id = lib.get_file_id(book_id, type_)  # try to get file_id from BD
        if file_id:
            return foo(msg, type_, book_id=book_id, file_id=file_id)  # if file_id not found
        else:
            return foo(msg, type_, book_id=book_id)

    return try_send


def download(type_, book_id, msg):
    try:
        if type_ in ['fb2', 'epub', 'mobi']:
            r = requests.get(f"http://flibusta.is/b/{book_id}/{type_}")
        else:
            r = requests.get(f"http://flibusta.is/b/{book_id}/download")
    except requests.exceptions.ConnectionError as err:
        telebot.logger.exception(err)
        return None
    if '<!DOCTYPE html' in str(r.content[:100]):  # if bot get html file with error message
        try:  # try download file from tor
            if type_ in ['fb2', 'epub', 'mobi']:
                r = requests.get(f"http://flibustahezeous3.onion/b/{book_id}/{type_}",
                                 proxies=config.PROXIES)
            else:
                r = requests.get(f"http://flibustahezeous3.onion/b/{book_id}/download",
                                 proxies=config.PROXIES)
        except requests.exceptions.ConnectionError as err:
            telebot.logger.exception(err)
            bot.reply_to(msg, "Ошибка подключения к серверу! Попробуйте позднее.")
            return None
    if '<!DOCTYPE html' in str(r.content[:100]) or '<html>' in str(r.content[:100]):  # send message to user when get
        bot.reply_to(msg, 'Ошибка!')                                                  # html file
        return None
    return r


@timeit
@send_by_file_id
def send_book(msg, type_, book_id=None, file_id=None):  # download from flibusta server and send document to user
    track(msg.from_user.id, msg, 'download')
    if not book_id:
        _, book_id = msg.text.split('_')
        book_id = int(book_id)
    book = lib.book_by_id(book_id)
    if not book:
        bot.reply_to(msg, 'Книга не найдена!')
        return
    caption = ''
    if book.author:
        if book.author.short:
            caption += book.author.normal_name
    caption += '\n' + book.title
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton('Поделиться',
                                   switch_inline_query=f"share_{book_id}"))
    if file_id:
        try:
            bot.send_document(msg.chat.id, file_id, reply_to_message_id=msg.message_id,
                              caption=caption, reply_markup=markup)
        except Exception as err:
            logger.debug(err)
        else:
            return
    r = download(type_, book_id, msg)
    if not r:
        return
    bot.send_chat_action(msg.chat.id, 'upload_document')
    filename = normalize(book, type_)
    with open(filename, 'wb') as f:
        f.write(r.content)
    if type_ == 'fb2':  # if type "fb2" extract file from archive
        os.rename(filename, filename.replace('.fb2', '.zip'))
        try:
            zip_obj = zipfile.ZipFile(filename.replace('.fb2', '.zip'))
        except zipfile.BadZipFile as err:
            logger.debug(err)
            return
        extracted = zip_obj.namelist()[0]
        zip_obj.extract(extracted)
        zip_obj.close()
        os.rename(extracted, filename)
        os.remove(filename.replace('.fb2', '.zip'))
    file_size = lib.get_file_size(book_id)
    if file_size < 50 * 1024 * 1024:
        try:
            res = bot.send_document(msg.chat.id, open(filename, 'rb'), reply_to_message_id=msg.message_id,
                                    caption=caption, reply_markup=markup)
        except requests.ConnectionError as err:
            logger.debug(err)
        else:
            lib.set_file_id(book_id, res.document.file_id, type_)
            try:
                os.remove(filename)
            except FileNotFoundError:
                pass
            return
    try:
        shutil.move(filename, './ftp')
    except shutil.Error:  # todo: удаление файла в главной папке
        lib.update_life_time(filename)
    else:
        lib.set_life_time(filename)

    life_time = lib.get_life_time(filename)
    if not life_time:  # todo: сообщение об ошибке
        return
    text = 'Не могу загрузить сюда файл, но у меня есть ссылка для скачивания: \n'
    text += f'📎  <a href="http://35.164.29.201/ftp/download.php?filename={filename}">Скачать</a>\n'
    text += 'Ссылка будет доступна 3 часа ( начиная с ' + time.strftime("%H:%M") + ' MSK)'

    keyboard = types.InlineKeyboardMarkup().row(
        types.InlineKeyboardButton('Обновить ссылку', callback_data=f'updatelink_{book_id}_{type_}')
    )
    bot.reply_to(msg, text, parse_mode='HTML', reply_markup=keyboard)


@bot.inline_handler(func=lambda x: re.search(r'share_([0-9])+$', x.query) is not None)
@timeit
def inline_share(query):  # share book to others user with use inline query
    track(query.from_user.id, query, 'share_book')
    _, book_id = query.query.split('_')
    result = list()
    book = lib.book_by_id(book_id)
    if not book:
        return
    result.append(types.InlineQueryResultArticle('1', 'Поделиться',
                                                 types.InputTextMessageContent(book.to_share, parse_mode='HTML',
                                                                               disable_web_page_preview=True), ))
    bot.answer_inline_query(query.id, result)


@bot.inline_handler(func=lambda query: query.query)
@timeit
def inline_hand(query):  # inline search
    track(query.from_user.id, query, 'inline_search')
    user_sets = db.get_lang_settings(query.from_user.id)
    books = lib.book_by_title(query.query, user_sets)
    if not books:
        bot.answer_inline_query(query.id, [types.InlineQueryResultArticle('1', 'Книги не найдены!',
                                                                          types.InputTextMessageContent(
                                                                              'Книги не найдены!'))]
                                )
        return
    book_index = 1
    result = list()
    for book in books[0:min(len(books) - 1, 50 - 1)]:
        result.append(types.InlineQueryResultArticle(str(book_index), book.title,
                                                     types.InputTextMessageContent(book.to_share, parse_mode='HTML',
                                                                                   disable_web_page_preview=True)))
        book_index += 1
    bot.answer_inline_query(query.id, result)


@bot.message_handler(commands=['settings'])
def settings(msg):  # send settings message
    user_set = db.get_lang_settings(msg.from_user.id)
    text = 'Настройки: '
    keyboard = types.InlineKeyboardMarkup()
    if user_set['allow_uk'] == 0:
        keyboard.row(types.InlineKeyboardButton('Украинский: 🅾 выключен!', callback_data='uk_on'))
    else:
        keyboard.row(types.InlineKeyboardButton('Украинский: ✅ включен!', callback_data='uk_off'))
    if user_set['allow_be'] == 0:
        keyboard.row(types.InlineKeyboardButton('Белорусский: 🅾 выключен!', callback_data='be_on'))
    else:
        keyboard.row(types.InlineKeyboardButton('Белорусский: ✅ включен!', callback_data='be_off'))
    bot.reply_to(msg, text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda x: re.search(r'^(uk|be)_(on|off)$', x.data) is not None)
def lang_setup(query):  # language settings
    lang, set_ = query.data.split('_')
    if set_ == 'on':
        db.set_land_settings(query.from_user.id, lang, 1)
    else:
        db.set_land_settings(query.from_user.id, lang, 0)

    keyboard = types.InlineKeyboardMarkup()
    user_set = db.get_lang_settings(query.from_user.id)
    if user_set['allow_uk'] == 0:
        keyboard.row(types.InlineKeyboardButton('Украинский: 🅾 выключен!', callback_data='uk_on'))
    else:
        keyboard.row(types.InlineKeyboardButton('Украинский: ✅ включен!', callback_data='uk_off'))
    if user_set['allow_be'] == 0:
        keyboard.row(types.InlineKeyboardButton('Белорусский: 🅾 выключен!', callback_data='be_on'))
    else:
        keyboard.row(types.InlineKeyboardButton('Белорусский: ✅ включен!', callback_data='be_off'))
    bot.edit_message_reply_markup(chat_id=query.message.chat.id, message_id=query.message.message_id,
                                  reply_markup=keyboard)


@bot.callback_query_handler(func=lambda x: re.search(r'updatelink_*', x.data) is not None)
def update_file_link(query):
    _, book_id, type_ = query.data.split('_')
    msg = query.message
    book_id = int(book_id)
    book = lib.book_by_id(book_id)
    filename = normalize(book, type_)
    lib.set_life_time(filename)

    if filename not in os.listdir(config.FTP_DIR):
        r = download(type_, book_id, msg)
        if not r:
            return
        with open(filename, 'wb') as f:
            f.write(r.content)
        if type_ == 'fb2':
            os.rename(filename, filename.replace('.fb2', '.zip'))
            try:
                zip_obj = zipfile.ZipFile(filename.replace('.fb2', '.zip'))
            except zipfile.BadZipFile as err:
                logger.debug(err)
                return
            extracted = zip_obj.namelist()[0]
            zip_obj.extract(extracted)
            zip_obj.close()
            os.rename(extracted, filename)
            os.remove(filename.replace('.fb2', '.zip'))

            shutil.move(filename, './ftp')

    text = 'Не могу загрузить сюда файл, но у меня есть ссылка для скачивания: \n'
    text += f'📎  <a href="http://35.164.29.201/ftp/download.php?filename={filename}">Скачать</a>\n'
    text += 'Ссылка будет доступна 3 часа (начиная с ' + time.strftime("%H:%M") + ' MSK)'

    keyboard = types.InlineKeyboardMarkup().row(
        types.InlineKeyboardButton('Обновить ссылку', callback_data=f'updatelink_{book_id}_{type_}')
    )

    bot.edit_message_text(text, chat_id=msg.chat.id, message_id=msg.message_id,
                          reply_markup=keyboard, parse_mode='HTML')
    track(msg.from_user.id, query, 'search_by_authors')


@bot.message_handler(func=lambda message: True)
def search(msg):
    track(msg.from_user.id, msg, 'receive_message')
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton('По названию', callback_data='b_1'),
                 types.InlineKeyboardButton('По авторам', callback_data='a_1')
                 )
    bot.reply_to(msg, 'Поиск: ', reply_markup=keyboard)


ftp = Controller()
ftp.start()

if config.WEBHOOK:
    import flask

    app = flask.Flask(__name__)


    @app.route('/', methods=['GET', 'POST'])
    def index():
        return ''


    @app.route(config.WEBHOOK_URL_PATH, methods=['POST'])
    def webhook():
        if flask.request.headers.get('content-type') == 'application/json':
            json_string = flask.request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return ''
        else:
            flask.abort(403)


    bot.remove_webhook()

    time.sleep(0.3)

    bot.set_webhook(url=config.WEBHOOK_URL_BASE + config.WEBHOOK_URL_PATH,
                    certificate=open(config.WEBHOOK_SSL_CERT, 'r'))

    app.run(host=config.WEBHOOK_LISTEN,
            port=config.WEBHOOK_PORT,
            ssl_context=(config.WEBHOOK_SSL_CERT, config.WEBHOOK_SSL_PRIV),
            debug=config.DEBUG)

    bot.remove_webhook()

else:
    bot.polling()

print('Closing ftp controller...')
ftp.stop()
