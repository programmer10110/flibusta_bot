from telegram_bot_api import *
from book_lib import Library
from file_tokens import FileTokens
from noblockme import noblock as noblock_foo
import botan
import zipfile
import requests
import os
from transliterate import translit

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


def search(by, arg):
    if by == 'title':
        return books.search_by_title(arg)
    if by == 'authors':
        return books.search_authors(arg)
    if by == 'by_author':
        if arg:
            return books.search_by_author(arg)
    if by == 'book_id':
        if arg:
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
    help_msg = ("Для поиска по названию набери /title <Название>\n"
                "  Например: /title Лолита\n"
                "\n"
                "Для поиска автора набери /author <Имя>\n"
                "  Например: /author Булгаков\n"
                "Также можешь посмотреть видео: https://youtu.be/pNAZWxDmfPo")
    msg.reply_to_chat(Text(help_msg), to_message=True)
    track(msg.from_, 'help', None)


@add_command(r'info')
def info(msg):
    info_msg = ("Каталог книг от 17.10.16\n"
                "Если хотите помочь проекту /donate\n"
                "Связь с создателем проекта @kurbezz\n"
                "Версия бота 1.1.2\n"
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
        len(books_list),max_books * page_number)], pages


@add_command(r'title', args=1)
def by_title(msg, title):
    if title:
        books_list = search('title', title)
        msg.reply_to_chat(ChatAction('typing'))
        if books_list:
            send(msg, books_list, 1, 'book', first=True)
        else:
            msg.reply_to_chat(Text('Книги не найдены!'), to_message=True)
        track(msg.from_, 'title', title)
    else:
        msg.reply_to_chat(Text('/title <Название>'), to_message=True)
        track(msg.from_, 'title', None)


@add_command(r'author', args=1)
def get_authors(msg, author):
    if author:
        authors_list = search('authors', author)
        msg.reply_to_chat(ChatAction('typing'))
        if authors_list:
            send(msg, authors_list, 1, 'author', first=True)
        else:
            msg.reply_to_chat(Text('Автор не найден!'), to_message=True)
        track(msg.from_, 'author', author)
    else:
        msg.reply_to_chat(Text('/author <Автор>'), to_message=True)
        track(msg.from_, 'author', None)


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
                    request = request.get(new_url)
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
        except requests.exceptions.ConnectTimeout as exp:
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
                name = author.short.replace(' ', '_') + '_-_'
                name +=  book.title.replace(' ', '_') +  '.' + f_type
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
            name = author.short.replace(' ', '_') + '_-_'
            name +=  book.title.replace(' ', '_') +  '.' + f_type
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
    url = 'http://flibusta.is/b/{0}'.format(book.id_)
    if book.file_type == 'fb2':
        result += ('📖 Читать(Бета): /read_{0}\n'
                   '⬇ fb2: /fb2_{0}\n'
                   '⬇ epub: /epub_{0}\n'
                   '⬇ mobi: /mobi_{0}\n\n').format(book.id_)
    else:
        result += '⬇ {0}: /{0}_{1}\n\n'.format(book.file_type, book.id_)
    return result


def author_to_send(author):
    return "👤 <b>{0}</b>\n/a_{1}\n\n".format(author.normal_name, author.id)


def send(msg, list_, page, type_, first=False):
    msg.reply_to_chat(ChatAction('typing'))
    list_, pages = get_page(list_, page)
    msg_text = ''
    for obj in list_:
        if type_ == 'book':
            msg_text += book_to_send(obj)
        if type_ == 'author':
            msg_text += author_to_send(obj)
    msg_text += '<code>Страница {0}/{1}</code>'.format(page, pages)

    keyboard = InlineKeyboardMarkup()
    if page == 1 and pages == 1:
        pass
    elif page == 1 and pages != 1:
        keyboard.add_row(
            InlineKeyboardButton('>>>',
                                 callback_data='page_{0}'.format(page + 1))
                         )
    elif page == pages:
        keyboard.add_row(
            InlineKeyboardButton('<<<',
                                 callback_data='page_{0}'.format(page - 1))
                         )
    else:
        keyboard.add_row(
            InlineKeyboardButton('<<<',
                                 callback_data='page_{0}'.format(page - 1)),
            InlineKeyboardButton('>>>',
                                 callback_data='page_{0}'.format(page + 1))
        )
    if first:
        msg.reply_to_chat(Text(msg_text, parse_mode='HTML',
                               reply_markup=keyboard),
                          to_message=True)
    else:
        msg.edit_message(msg_text, parse_mode='HTML', reply_markup=keyboard)


@add_callback(r'page_[0-9]+')
def pages_changer(query):
    msg = query.message
    msg.reply_to_chat(ChatAction('typing'))
    _, page = query.data.split('_')
    text = msg.reply_to_message.text
    if '_' in text:
        command = text[:text.find('_')]
        arg = text[text.find('_') + 1:]
    else:
        command = text[:text.find(' ')]
        arg = text[text.find(' ') + 1:]
    if command[1:] == 'title':
        list_ = search('title', arg)
        track(msg.from_, 'title', arg)
        send(msg, list_, int(page), 'book')
    elif command[1:] == 'author':
        list_ = search('authors', arg)
        track(msg.from_, 'author', arg)
        send(msg, list_, int(page), 'author')
    elif command[1:] == 'a':
        list_ = search('by_author', arg)
        send(msg, list_, int(page), 'book')


@add_command(r'a', args=1, endl='_')
def by_author(msg, id_):
    books_list = search('by_author', id_)
    msg.reply_to_chat(ChatAction('typing'))
    if books_list:
        send(msg, books_list, 1, 'book', first=True)
    else:
        msg.reply_to_chat(Text('Ошибка!'), to_message=True)


@add_message(r'http://flibusta.is\/b\/([0-9]+)$', args=1)
def url_book(msg, id_):
    books_list = search('book_id', id_)
    msg.reply_to_chat(ChatAction('typing'))
    if books_list:
        send(msg, books_list, 1, 'book', first=True)
    else:
        msg.reply_to_chat(Text('Ошибка!'), to_message=True)


@add_message(r'http://flibusta.is\/a\/([0-9]+)$', args=1)
def url_author(msg, id_):
    books_list = search('by_author', id_)
    msg.reply_to_chat(ChatAction('typing'))
    if books_list:
        send(msg, books_list, 1, 'book', first=True)
    else:
        msg.reply_to_chat(Text('Ошибка!'), to_message=True)


@add_command(r'read', args=1, endl='_')
def read(msg, id_):
    msg.reply_to_chat(ChatAction('typing'))
    basic_url = 'flibusta.is/b/{0}/read'.format(id_)
    url = noblock_foo(basic_url)
    if url:
        msg.reply_to_chat(Text(('<a href="{0}">'
                                'Ссылка для чтения</a>').format(url),
                                parse_mode='HTML',
                                disable_web_page_preview=True),
                          to_message=True)
    else:
        msg.reply_to_chat(Text('Ошибка! Попробуй позднее :('),
                          to_message=True)


#new search

@add_message(r'^([^(http|/)]*)')
def new_search(msg):
    keyboard = InlineKeyboardMarkup()
    keyboard.add_row(InlineKeyboardButton('По названию',
                                          callback_data='page_t_1'),
                     InlineKeyboardButton('По автору',
                                          callback_data='page_a_1')
                     )
    msg.reply_to_chat(Text('Поиск (Бета):', reply_markup=keyboard),
                      to_message=True)


@add_callback(r'page_[at]_[0-9]+')
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
    if type_ == 'a':
        list_ = search('authors', msg.reply_to_message.text)
        if list_:
            new_send(msg, 'author', int(page), list_)
        else:
            msg.edit_message('Автор не найден!')


def new_send(msg, type_, page, list_):
    msg.reply_to_chat(ChatAction('typing'))
    list_, pages = get_page(list_, page)
    msg_text = ''
    for obj in list_:
        if type_ == 'book':
            msg_text += book_to_send(obj)
        if type_ == 'author':
            msg_text += author_to_send(obj)
    msg_text += '<code>Страница {0}/{1}</code>'.format(page, pages)

    if type_ == 'author':
        page_t = 'a'
    if type_ == 'book':
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
    
    msg.edit_message(msg_text, parse_mode='HTML', reply_markup=keyboard)


if __name__ == '__main__':
    books = Library()
    tokens = FileTokens(config.tokens_name)
    bot = Bot(config.bot_token)
    bot.handler.start(config.bot_threads)
