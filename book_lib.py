import re
import gzip
import time
import requests
from download_counter import Counter
import mysql.connector
from mysql.connector import Error

from config import *


def normal_name(first_name, middle_name, last_name):
    temp = None
    if last_name:
        temp = last_name
    if first_name:
        if last_name:
            temp += " " + first_name
        else:
            temp = first_name
    if middle_name:
        if last_name or first_name:
            temp += " " + middle_name
        else:
            temp = middle_name
    if temp:
        return temp
    else:
        return ''


def short(last_name, first_name, middle_name):
    temp = None
    if last_name:
        temp = last_name
    if first_name:
        if last_name:
            temp += " " + first_name[0]
        else:
            temp = first_name
    if middle_name:
        if last_name or first_name:
            temp += " " + middle_name[0]
        else:
            temp = middle_name
    if temp:
        return temp
    else:
        return ''


def for_search(arg):
    args = arg.split()
    if len(args) == 1:
        return arg
    else:
        result = '+' + args[0]
        for a in args[1:]:
            result += ' +' + a
        return result


class Book:
    def __init__(self, obj, counter):
        self.counter = counter

        self.last_name = obj[0]
        self.first_name = obj[1]
        self.middle_name = obj[2]
        self.title = obj[3]
        self.subtitle = obj[4]
        self.lang = obj[5]
        self.id_ = obj[6]
        self.file_type = obj[7]
        self.s_names = '{0} {1} {2} {0} {2} {1} {0}'.format(obj[0].lower(),
                                                            obj[1].lower(),
                                                            obj[2].lower())
        self.__set_name()

    @property
    def downloaded(self):
        return self.counter.get(self.id_)

    def __set_name(self):
        self.normal_name = normal_name(self.first_name, self.middle_name,
                                       self.last_name)


class Author:
    def __init__(self, id_, first_name, middle_name, last_name):
        self.id = id_
        self.first_name = first_name
        self.middle_name = middle_name
        self.last_name = last_name
        self.__set_name()

    def __set_name(self):
        self.normal_name = normal_name(self.first_name, self.middle_name,
                                       self.last_name)
        self.short = short(self.first_name, self.middle_name, self.last_name)


class Library:
    def __init__(self):
        from config import counter_name
        self.counter = Counter(counter_name)
        self.__connect()

    def __connect(self):
        try:
            conn = mysql.connector.connect(host=mysql_host,
                                           database=mysql_database,
                                           user=mysql_user,
                                           password=mysql_password)
            if conn.is_connected():
                print('[{0}][FLIBUSTA] Connected to database!'.format(time.strftime("%H:%M:%S")))
        except Error as e:
            print(e)
        else:
            self.conn = conn

    def downloaded(self, _id):
        self.counter.add(_id)

    def __get_cursor(self):
        try:
            return self.conn.cursor()
        except Error:
            self.__connect()
            return self.__get_cursor()

    def get_author_info(self, id_):
        cursor = self.__get_cursor()
        cursor.execute(
            ("SELECT AvtorId FROM `libavtor` "
             "WHERE BookId=%s"), (id_, )
        )
        author_id = cursor.fetchall()
        if author_id:
            author_id = author_id[0]
        cursor.close()

        cursor = self.conn.cursor()
        cursor.execute(
            ("SELECT LastName, FirstName, MiddleName "
             "FROM libavtorname WHERE AvtorId=%s"), (author_id[0], )
        )
        author = cursor.fetchone()
        cursor.close()
        return author

    def good_author_id(self, id_):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM `libavtoraliase` WHERE BadId=%s", (id_, )
        )
        result = cursor.fetchall()
        cursor.close()

        if result:
            return False
        else:
            return True

    def __processing_books(self, row):
        result = []
        for book in row:
            id_ = book[3]
            author = self.get_author_info(id_)
            if author:
                result.append(
                    Book([author[0], author[1], author[2], book[0], book[1],
                          book[2], book[3], book[4]], self.counter)
                )
            else:
                result.append(
                    Book(['', '', '', book[0], book[1],
                          book[2], book[3], book[4]], self.counter)
                )
        return result

    def __processing_authors(self, row):
        result = []
        for author in row:
            if self.good_author_id(author[0]):
                result.append(
                    Author(*author)
                )
        return result

    def get_book(self, id_):
        cursor = self.__get_cursor()
        cursor.execute(
            ("SELECT Title, Title1, Lang, BookId, FileType "
             "FROM `libbook` WHERE BookId=%s AND Deleted=0 AND"
             "(Lang='ru' OR Lang='uk' OR Lang='kk' OR Lang='be')"), (id_, )
        )
        book = cursor.fetchall()
        if book:
            book = book[0]
            author = self.get_author_info(book[3])
            if author:
                return Book([author[0], author[1], author[2], book[0], book[1],
                             book[2], book[3], book[4]], self.counter)
            else:
                return Book(['', '', '', book[0], book[1],
                             book[2], book[3], book[4]], self.counter)
        else:
            return None

    def __by_author_id(self, id_):
        cursor = self.__get_cursor()
        cursor.execute(
            'SELECT BookId FROM `libavtor` WHERE AvtorId=%s', (id_, )
        )
        book_ids = cursor.fetchall()
        cursor.close()

        books = []
        if book_ids:
            for book_id in [x[0] for x in book_ids]:
                book = self.get_book(book_id)
                if book:
                    books.append(book)
        else:
            return None

        if books:
            return books
        else:
            return None

    def __by_title(self, title):
        cursor = self.__get_cursor()
        cursor.execute(
            ("SELECT Title, Title1, Lang, BookId, FileType FROM `libbook` "
             "WHERE MATCH (Title, Title1) "
             """AGAINST (%s IN BOOLEAN MODE) """
             "AND Deleted=0 AND "
             "(Lang='ru' OR Lang='uk' OR Lang='kk' OR Lang='be')"), (title, )
        )
        row = cursor.fetchall()
        cursor.close()
        if row:
            return self.__processing_books(row)
        else:
            return None

    def search_authors(self, author):
        cursor = self.__get_cursor()
        cursor.execute(
            ("SELECT AvtorId, FirstName, MiddleName, LastName "
             "FROM `libavtorname` "
             "WHERE MATCH (FirstName, MiddleName, LastName) "
             "AGAINST (%s IN BOOLEAN MODE)"), (author, )
        )
        row = cursor.fetchall()
        cursor.close()
        if row:
            return self.__processing_authors(row)
        else:
            return None

    def search_by_title(self, title):
        return self.__by_title(title)

    def search_by_author(self, id_):
        return self.__by_author_id(id_)

    def get_author_by_book(self, id_):
        author = self.get_author_info(id_)
        if author:
            return Author(id_, author[0], author[1], author[2])
        else:
            return None
