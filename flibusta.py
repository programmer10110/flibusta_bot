from telegram_bot_api import *
from book_lib import Library
from file_tokens import FileTokens
import botan
import zipfile
import requests
import os
from transliterate import translit
from stopwords import StopWords
from noblockme import noblock as noblock_foo

import config


def track(user, event, arg):
    botan.track(config.botan_token,
                user.id,
                {user.id: {'first_name': user.first_name,
                           'last_name': user.last_name,
                           'username': user.username,
                           'request': arg}
                 },
                event)


def track_error():
    botan.track(config.botan_token,
                0,
                'bot',
                'Error')


def test_words(string):
    words = string.split()
    if len(words) <= 2:
        res = ''
        for word in words:
            if not stop.word_status(word.lower()):
                if res:
                    res += ' ' + word
                else:
                    res += word
        return res
    else:
        return string


def search(by, arg):
    if arg:
        if by == 'title':
            if test_words(arg):
                return books.search_by_title(test_words(arg))
        if by == 'authors':
            return books.search_authors(arg)
        if by == 'by_author':
            return books.search_by_author(arg)
        if by == 'book_id':
            return [books.get_book(arg)]


@add_command(r'start')
def start(msg):
    start_msg = ("Привет!\n"
                 "Этот бот поможет тебе загружать книги с флибусты.\n"
                 "Набери /help что бы получить помощь.\n"
                 "Информация о боте /info.\n")
    msg.reply_to_chat(Text(start_msg))
    track(msg.from_, 'start', None)


@add_command(r'help')
def bot_help(msg):
    help_msg = ("Лучше один раз увидеть, чем сто раз услышать.\n"
                "https://youtu.be/V8XHzRSRcWk")
    msg.reply_to_chat(Text(help_msg), to_message=True)
    track(msg.from_, 'help', None)


@add_command(r'info')
def info(msg):
    info_msg = ("Каталог книг от 10.12.16\n"
                "Если хотите помочь проекту /donate\n"
                "Связь с создателем проекта @kurbezz\n"
                "Версия бота 1.2.0\n"
                "Github: https://goo.gl/V0Iw7m")
    msg.reply_to_chat(Text(info_msg,
                           parse_mode='HTML'),
                      to_message=True)
    track(msg.from_, 'info', None)


@add_command(r'donate')
def donate(msg):
    donate_msg_new = ('Хочешь поддержать проект или автора?\n'
                      'Можешь перевести деньги на карту '
                      '<b>5321 3002 4071 3904</b>\n'
                      'В комментарии к пожертвованию можешь указать '
                      'на что пойдут деньги:\n'
                      ' Улучшение сервера\n'
                      ' Работу над ботом (автору на книги, кофе и т.д.)')
    msg.reply_to_chat(Text(donate_msg_new,
                           parse_mode='HTML',
                           disable_web_page_preview=True),
                      to_message=True)
    track(msg.from_, 'donate', None)


def get_page(books_list, page_number):
    max_books = 10
    if len(books_list) <= max_books:
        pages = 1
    else:
        pages = len(books_list) // max_books + 1
    return books_list[max_books * (page_number - 1):min(
        len(books_list), max_books * page_number)], pages


@add_command(r'add_stopword', args=1)
def add_stopword(msg, word):
    if word:
        stop.add(word)
        msg.reply_to_chat(Text('Добавлено!'),
                          to_message=True)


@add_command(r'word_status', args=1)
def word_status(msg, word):
    if stop.word_status(word):
        text = 'Слово есть в стоп листе!'
    else:
        text = 'Слова нет в стоп листе!'
    msg.reply_to_chat(Text(text), to_message=True)


@add_command(r'fb2', args=1, endl='_')
def download_fb2(*args):
    download_ziped(*args, f_type='fb2')


@add_command(r'epub', args=1, endl='_')
def download_epub(*args):
    download(*args, f_type='epub')


@add_command(r'mobi', args=1, endl='_')
def download_mobi(*args):
    download(*args, f_type='mobi')


@add_command(r'djvu', args=1, endl='_')
def download_djvu(*args):
    download(*args, f_type='djvu')


@add_command(r'pdf', args=1, endl='_')
def download_pdf(*args):
    download(*args, f_type='pdf')


@add_command(r'doc', args=1, endl='_')
def download_doc(*args):
    download(*args, f_type='doc')


def make_request(url, timeout=10, noblock=False):
    cookies = {'onion2web_confirmed': 'true'}

    try_n = 0
    while try_n < 3:
        try:
            if noblock:
                new_url = noblock_foo(url)
                if new_url:
                    request = requests.get(new_url)
                else:
                    raise requests.exceptions.ConnectionError
            else:
                request = requests.get(url,
                                       proxies=config.proxies,
                                       cookies=cookies,
                                       timeout=timeout)
        except requests.exceptions.ConnectionError as exp:
            print(exp)
            try_n += 1
        except requests.exceptions.ReadTimeout as exp:
            print(exp)
            try_n += 1
        else:
            return request


def download_ziped(msg, ident, f_type, noblock=False):
    book = books.get_book(ident)
    author = books.get_author_by_book(book.id_)
    caption = '{1}\n\n{0}'.format(book.title, book.normal_name)
    msg.reply_to_chat(ChatAction('upload_document'))
    if tokens.get(ident, f_type):
        msg.reply_to_chat(Document(tokens.get(ident, f_type),
                                   caption=caption),
                          to_message=True)
    else:
        if noblock:
            url = 'http://flibusta.is{0}'.format('/b/' + ident + '/')
        else:
            url = 'http://flibustahezeous3.onion{0}'.format('/b/' + ident + '/')
        if f_type in ['fb2', 'epub', 'mobi']:
            url += f_type
        else:
            url += download

        request = make_request(url)
        if request:
            with open('{0}.zip'.format(ident), 'wb') as f:
                f.write(request.content)
            try:
                zip_obj = zipfile.ZipFile('{0}.zip'.format(ident))
            except zipfile.BadZipfile:
                os.remove('{0}.zip'.format(ident))
                msg.reply_to_chat(Text('Ошибка! Поврежденный файл:('),
                                  to_message=True)
                return 0
            else:
                if author:
                    name = author.short.replace(' ', '_') + '_-_'
                else:
                    name = ""
                name += book.title.replace(' ', '_') + '.' + f_type
                name = translit(name, 'ru', reversed=True)
                filename = zip_obj.namelist()[0]
                zip_obj.extract(filename)
                zip_obj.close()
                reply = msg.reply_to_chat(Document(InputFile(filename,
                                                             custom=name),
                                                   caption=caption),
                                          to_message=True
                                          )
                os.remove(filename)
                os.remove('{0}.zip'.format(ident))
                if reply:
                    tokens.add(ident, f_type, reply.document.file_id)
        else:
            if noblock:
                msg.reply_to_chat(Text('Ошибка! Попробуй позже!'),
                                  to_message=True)
                track_error()
            else:
                download_ziped(msg, ident, f_type, noblock=True)
    track(msg.from_, 'download', ident)


def download(msg, ident, f_type, noblock=False):
    book = books.get_book(ident)
    author = books.get_author_by_book(book.id_)
    caption = '{1}\n\n{0}'.format(book.title, book.normal_name)
    msg.reply_to_chat(ChatAction('upload_document'))
    if tokens.get(ident, f_type):
        msg.reply_to_chat(Document(tokens.get(ident, f_type),
                                   caption=caption),
                          to_message=True)
    else:
        if noblock:
            url = 'http://flibusta.is{0}'.format('/b/' + ident + '/')
        else:
            url = 'http://flibustahezeous3.onion{0}'.format('/b/' + ident + '/')
        if f_type in ['fb2', 'epub', 'mobi']:
            url += f_type
        else:
            url += "download"
        request = make_request(url)
        if request:
            if author:
                name = author.short.replace(' ', '_') + '_-_'
            else:
                name = ""
            name += book.title.replace(' ', '_') + '.' + f_type
            name = translit(name, 'ru', reversed=True)
            reply = msg.reply_to_chat(
                Document(
                    Bytes(request.content,
                          name),
                    caption=caption),
                to_message=True)
            if reply:
                tokens.add(ident, f_type, reply.document.file_id)
        else:
            if noblock:
                msg.reply_to_chat(Text('Ошибка! Попробуй позже!'),
                                  to_message=True)
                track_error()
            else:
                download(msg, ident, f_type, noblock=True)

    track(msg.from_, 'download', ident)


def book_to_send(book):
    result = ("<b>{0}</b> | {2}\n"
              "<b>{1}</b>\n").format(book.title,
                                     book.normal_name,
                                     book.lang)
    if book.file_type == 'fb2':
        result += (  # '📖 Читать(Бета): /read_{0}\n'
            '⬇ fb2: /fb2_{0}\n'
            '⬇ epub: /epub_{0}\n'
            '⬇ mobi: /mobi_{0}\n\n').format(book.id_)
    else:
        result += '⬇ {0}: /{0}_{1}\n\n'.format(book.file_type, book.id_)
    return result


def author_to_send(author):
    return "👤 <b>{0}</b>\n/a_{1}\n\n".format(author.normal_name, author.id)


@add_command(r'a', args=1, endl='_')
def by_author(msg, id_):
    books_list = search('by_author', id_)
    msg.reply_to_chat(ChatAction('typing'))
    if books_list:
        new_send(msg, 'by_author', 1, books_list, first=True)
    else:
        msg.reply_to_chat(Text('Ошибка!'), to_message=True)


@add_message(r'http://flibusta.is\/b\/([0-9]+)$', args=1)
def url_book(msg, id_):
    books_list = search('book_id', id_)
    msg.reply_to_chat(ChatAction('typing'))
    if books_list:
        new_send(msg, 'book', 1, books_list)
    else:
        msg.reply_to_chat(Text('Ошибка!'), to_message=True)


@add_message(r'http://flibusta.is\/a\/([0-9]+)$', args=1)
def url_author(msg, id_):
    books_list = search('by_author', id_)
    msg.reply_to_chat(ChatAction('typing'))
    if books_list:
        new_send(msg, 'book', 1, books_list)
    else:
        msg.reply_to_chat(Text('Ошибка!'), to_message=True)


@add_command(r'read', args=1, endl='_')
def read(msg, id_):
    msg.reply_to_chat(ChatAction('typing'))
    url = 'http://s7m03fvh.mfxc.http.s11.wbprx.com/b/{0}/read'.format(id_)
    msg.reply_to_chat(Text(('<a href="{0}">'
                            'Ссылка для чтения</a>').format(url),
                           parse_mode='HTML',
                           disable_web_page_preview=True),
                      to_message=True)


# new search

@add_message(r'^([^(http|/)]*)')
def new_search(msg):
    keyboard = InlineKeyboardMarkup()
    keyboard.add_row(InlineKeyboardButton('По названию',
                                          callback_data='page_t_1'),
                     InlineKeyboardButton('По авторам',
                                          callback_data='page_a_1')
                     )
    msg.reply_to_chat(Text('Поиск:', reply_markup=keyboard),
                      to_message=True)


@add_callback(r'page_[atb]_[0-9]+')
def new_page_changer(query):
    msg = query.message
    msg.reply_to_chat(ChatAction('typing'))
    _, type_, page = query.data.split('_')
    if type_ == 't':
        list_ = search('title', msg.reply_to_message.text)
        if list_:
            new_send(msg, 'book', int(page), list_)
        else:
            msg.edit_message('Книги не найдены!')
        track(msg.from_, 'title', msg.reply_to_message.text)
    if type_ == 'a':
        list_ = search('authors', msg.reply_to_message.text)
        if list_:
            new_send(msg, 'author', int(page), list_)
        else:
            msg.edit_message('Автор не найден!')
        track(msg.from_, 'author', msg.reply_to_message.text)
    if type_ == 'b':
        _, id_ = msg.reply_to_message.text.split('_')
        list_ = search('by_author', id_)
        if list_:
            new_send(msg, 'by_author', int(page), list_)
        else:
            msg.edit_message('Книги не найдены!')
        track(msg.from_, 'author', id_)


def new_send(msg, type_, page, list_, first=False):
    msg.reply_to_chat(ChatAction('typing'))
    list_, pages = get_page(list_, page)
    msg_text = ''
    for obj in list_:
        if type_ == 'book' or type_ == 'by_author':
            msg_text += book_to_send(obj)
        elif type_ == 'author':
            msg_text += author_to_send(obj)
    msg_text += '<code>Страница {0}/{1}</code>'.format(page, pages)

    if type_ == 'author':
        page_t = 'a'
    elif type_ == 'by_author':
        page_t = 'b'
    else:
        page_t = 't'

    keyboard = InlineKeyboardMarkup()
    if page == 1 and pages == 1:
        pass
    elif page == 1 and pages != 1:
        keyboard.add_row(
            InlineKeyboardButton('>>>',
                                 callback_data='page_{1}_{0}'.format(page + 1,
                                                                     page_t)
                                 )
        )
    elif page == pages:
        keyboard.add_row(
            InlineKeyboardButton('<<<',
                                 callback_data='page_{1}_{0}'.format(page - 1,
                                                                     page_t)
                                 )
        )
    else:
        keyboard.add_row(
            InlineKeyboardButton('<<<',
                                 callback_data='page_{1}_{0}'.format(page - 1,
                                                                     page_t)
                                 ),
            InlineKeyboardButton('>>>',
                                 callback_data='page_{1}_{0}'.format(page + 1,
                                                                     page_t)
                                 )
        )
    if pages >= 10:
        if page == 1:
            keyboard.add_row(
                InlineKeyboardButton('>{0}'.format(min(pages, page + 10)),
                                     callback_data='page_{0}'.format(min(page + 10, pages),
                                                                     page_t)
                                     )
            )
        elif page == pages:
            keyboard.add_row(
                InlineKeyboardButton('{0}<'.format(max(1, page - 10)),
                                     callback_data='page_{1}_{0}'.format(max(1, page - 10),
                                                                         page_t)
                                     )
            )
        else:
            keyboard.add_row(
                InlineKeyboardButton('{0}<'.format(max(1, page - 10)),
                                     callback_data='page_{1}_{0}'.format(max(1, page - 10),
                                                                         page_t)
                                     ),
                InlineKeyboardButton('>{0}'.format(min(pages, page + 10)),
                                     callback_data='page_{1}_{0}'.format(min(page + 10, pages),
                                                                         page_t)
                                     )
            )
    if first:
        msg.reply_to_chat(Text(msg_text, parse_mode='HTML', reply_markup=keyboard), to_message=True)
    else:
        msg.edit_message(msg_text, parse_mode='HTML', reply_markup=keyboard)


if __name__ == '__main__':
    books = Library()
    tokens = FileTokens(config.tokens_name)
    stop = StopWords('stop_list.db')
    bot = Bot(config.bot_token)
    bot.handler.start(config.bot_threads)
