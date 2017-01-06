import mysql.connector  # https://github.com/sanpingz/mysql-connector
from mysql.connector import Error
import time

import config


class Author:
    def __init__(self, id_, last_name, first_name, middle_name):
        self.id = id_
        self.last_name = last_name
        self.first_name = first_name
        self.middle_name = middle_name

    @property
    def normal_name(self):
        temp = ''
        if self.last_name:
            temp = self.last_name
        if self.first_name:
            if temp:
                temp += " "
            temp += self.first_name
        if self.middle_name:
            if temp:
                temp += " "
            temp += self.middle_name
        if temp:
            return temp

    @property
    def short(self):
        temp = ''
        if self.last_name:
            temp += self.last_name
        if self.first_name:
            if temp:
                temp += " "
            temp += self.first_name[0]
        if self.middle_name:
            if temp:
                temp += " "
            temp += self.middle_name[0]
        return temp

    @property
    def to_send(self):
        return f'👤 <b>{self.normal_name}</b>\n/a_{self.id}\n\n'


class Book:
    def __init__(self, book, author):
        self.author = author
        self.title = book[0]
        self.subtitle = book[1]
        self.lang = book[2]
        self.id_ = book[3]
        self.file_type = book[4]

    @property
    def to_send(self):
        res = f'<b>{self.title}</b>'
        if self.author:
            res += f' | {self.lang}\n<b>{self.author.normal_name}</b>\n'
        else:
            res += '\n'
        if self.file_type == 'fb2':
            return res + f'⬇ fb2: /fb2_{self.id_}\n⬇ epub: /epub_{self.id_}\n⬇ mobi: /mobi_{self.id_}\n\n'
        else:
            return res + f'⬇ {self.file_type}: /{self.file_type}_{self.id_}\n\n'

    @property
    def to_share(self):
        url = 'https://telegram.me/flibusta_rebot?start='
        res = f'<b>{self.title}</b>'
        if self.author:
            res += f' | {self.lang}\n<b>{self.author.normal_name}</b>\n'
        else:
            res += '\n'
        if self.file_type == 'fb2':
            return res + (f'⬇ fb2: <a href="{url}fb2_{self.id_}">/fb2_{self.id_}</a>\n'
                          f'⬇ epub: <a href="{url}epub_{self.id_}">/epub_{self.id_}</a>\n'
                          f'⬇ mobi: <a href="{url}mobi_{self.id_}">/mobi_{self.id_}</a>\n')
        else:
            return res + (f'⬇ {self.file_type}: <a href="{url}{self.file_type}_{self.id_}">'
                          f'/{self.file_type}_{self.id_}</a>\n')


def for_search(arg):
    args = arg.split()
    if len(args) == 1:
        return arg
    else:
        result = '+' + args[0]
        for a in args[1:]:
            result += ' +' + a
        return result


def sort_by_alphabet(obj):
    if obj.title:
        return obj.title.replace('«', '').replace('»', '')
    else:
        return None


class Library:
    def __init__(self):
        self.conn = None
        self.__connect()

    def __connect(self):
        while True:
            try:
                self.conn = mysql.connector.connect(host=config.MYSQL_HOST,
                                                    database=config.MYSQL_DATABASE,
                                                    user=config.MYSQL_USER,
                                                    password=config.MYSQL_PASSWORD)
            except Error as err:
                print(f"{time.strftime('%H:%M:%S')} {err}")
            else:
                return

    def __get_cursor(self):
        try:
            return self.conn.cursor()
        except Error as err:
            print(f"{time.strftime('%H:%M:%S')} {err}")
            self.__connect()
            return self.conn.cursor(buffered=True)

    def fetchone(self, sql, args):
        cursor = self.__get_cursor()
        try:
            cursor.execute(sql, args)
            return cursor.fetchone()
        except Error as err:
            print(f"{time.strftime('%H:%M:%S')} {err}")
            return None

    def fetchall(self, sql, args):
        cursor = self.__get_cursor()
        try:
            cursor.execute(sql, args)
            return cursor.fetchall()
        except Error as err:
            print(f"{time.strftime('%H:%M:%S')} {err}")
            return None
        finally:
            try:
                cursor.close()
            except ReferenceError as err:
                print(f"{time.strftime('%H:%M:%S')} {err}")

    def good_author_id(self, id_):
        result = self.fetchall(
            "SELECT * FROM libavtoraliase WHERE BadId=%s", (id_,)
        )
        if result and not isinstance(result, Error):
            return False
        else:
            return True

    def __add_author_info(self, books):
        result = []
        for book in books:
            author = self.author_by_id(book[3])
            result.append(
                Book(book, author)
            )
        return result

    def __filter_authors(self, authors):
        result = []
        for author in authors:
            if self.good_author_id(author[0]):
                result.append(
                    Author(*author)
                )
        return result

    def author_have_books(self, id_):
        return self.fetchone('SELECT count(*) FROM libavtor WHERE AvtorId=%s;',
                             (id_,)
                             )

    def author_by_id(self, id_):
        author_id = self.fetchone("SELECT AvtorId FROM libavtor WHERE BookId=%s", (id_,))
        if author_id:
            author = self.fetchone(
                ("SELECT LastName, FirstName, MiddleName "
                 "FROM libavtorname WHERE AvtorId=%s"), (author_id[0],)
            )
            if author:
                return Author(id, *author)
            else:
                return None

    def book_by_id(self, id_):
        book = self.fetchall(
            ("SELECT Title, Title1, Lang, BookId, FileType "
             "FROM libbook WHERE BookId=%s"), (id_,)
        )
        if book:
            book = book[0]
            author = self.author_by_id(book[3])
            return Book(book, author)
        else:
            return None

    def book_by_author(self, id_):
        book_ids = self.fetchall(
            'SELECT BookId FROM libavtor WHERE AvtorId=%s;', (id_,)
        )
        if book_ids:
            books = []
            for book_id in [x[0] for x in book_ids]:
                book = self.book_by_id(book_id)
                if book:
                    books.append(book)
            if books:
                return sorted(books, key=sort_by_alphabet)
            else:
                return None
        else:
            return None

    def book_by_title(self, title):
        books = self.fetchall(
            ("SELECT Title, Title1, Lang, BookId, FileType FROM libbook WHERE "
             'MATCH (Title) AGAINST (%s IN BOOLEAN MODE)'), (for_search(title),)
        )
        if books:
            return self.__add_author_info(books)
        else:
            return None

    def author_by_name(self, author):
        row = self.fetchall(("SELECT AvtorId, FirstName, MiddleName, LastName "
                             "FROM libavtorname "
                             "WHERE MATCH (FirstName, MiddleName, LastName) "
                             "AGAINST (%s IN BOOLEAN MODE)"), (for_search(author),)
                            )
        if row:
            authors = self.__filter_authors(row)
            res = []
            for author in authors:
                if self.author_have_books(author.id):
                    res.append(author)
            if res:
                return res
            else:
                return None
        else:
            return None
