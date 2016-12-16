import time
import mysql.connector
from mysql.connector import Error

from config import *


def sort_by_alphabet(obj):
    if obj.title:
        return obj.title.replace('«', '').replace('»', '')
    else:
        return None


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
    def __init__(self, obj):
        self.last_name = obj[0]
        self.first_name = obj[1]
        self.middle_name = obj[2]
        self.title = obj[3]
        self.subtitle = obj[4]
        self.lang = obj[5]
        self.id_ = obj[6]
        self.file_type = obj[7]
        self.normal_name = normal_name(self.first_name, self.middle_name,
                                       self.last_name)


class Author:
    def __init__(self, id_, first_name, middle_name, last_name):
        self.id = id_
        self.first_name = first_name
        self.middle_name = middle_name
        self.last_name = last_name
        self.normal_name = normal_name(self.first_name, self.middle_name,
                                       self.last_name)
        self.short = short(self.first_name, self.middle_name, self.last_name)


class Library:
    def __init__(self):
        self.conn = None
        self.__connect()

    def __connect(self):
        try:
            conn = mysql.connector.connect(host=mysql_host,
                                           database=mysql_database,
                                           user=mysql_user,
                                           password=mysql_password)
        except Error as e:
            time.sleep(0.01)
            self.__connect()
        else:
            self.conn = conn

    def __get_cursor(self):
        try:
            return self.conn.cursor()
        except Error as e:
            self.__connect()
            return self.__get_cursor()

    def __processing_books(self, row):
        result = []
        for book in row:
            id_ = book[3]
            author = self.get_author_info(id_)
            if author and not isinstance(author, Error):
                result.append(
                    Book([author[0], author[1], author[2], book[0], book[1],
                          book[2], book[3], book[4]])
                )
            else:
                result.append(
                    Book(['', '', '', book[0], book[1],
                          book[2], book[3], book[4]])
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

    def fetchone(self, sql, args):
        cursor = self.__get_cursor()
        try:
            cursor.execute(sql, args)
            res = cursor.fetchone()
            cursor.close()
        except Error as e:
            return e
        else:
            return res

    def fetchall(self, sql, args):
        cursor = self.__get_cursor()
        try:
            cursor.execute(sql, args)
            res = cursor.fetchall()
            cursor.close()
        except Error as e:
            return e
        else:
            return res

    def get_author_info(self, id_):
        author_id = self.fetchone(
            ("SELECT AvtorId FROM `libavtor` WHERE BookId=%s"), (id_,)
        )

        if author_id and not isinstance(author_id, Error):
            return self.fetchone(
                ("SELECT LastName, FirstName, MiddleName "
                 "FROM libavtorname WHERE AvtorId=%s"), (author_id[0],)
            )

    def good_author_id(self, id_):
        result = self.fetchall(
            "SELECT * FROM `libavtoraliase` WHERE BadId=%s", (id_,)
        )
        if result and not isinstance(result, Error):
            return False
        else:
            return True

    def __by_author_id(self, id_):
        book_ids = self.fetchall(
            'SELECT BookId FROM `libavtor` WHERE AvtorId=%s;', (id_,)
        )
        if book_ids and not isinstance(book_ids, Error):
            books = []
            for book_id in [x[0] for x in book_ids]:
                book = self.get_book(book_id)
                if book:
                    books.append(book)
            if books:
                books.sort(key=sort_by_alphabet)
                return books
            else:
                return None
        else:
            return None

    def get_book(self, id_):
        book = self.fetchall(
            ("SELECT Title, Title1, Lang, BookId, FileType "
             "FROM `libbook` WHERE BookId=%s"), (id_,)
        )
        if book and not isinstance(book, Error):
            book = book[0]
            author = self.get_author_info(book[3])
            if author and not isinstance(author, Error):
                return Book([author[0], author[1], author[2], book[0], book[1],
                             book[2], book[3], book[4]])
            else:
                return Book(['', '', '', book[0], book[1],
                             book[2], book[3], book[4]])
        else:
            return None

    def author_have_book(self, id_):
        return self.fetchone('SELECT count(*) FROM `libavtor` WHERE AvtorId=%s;',
                             (id_,)
                             )

    def search_authors(self, author):
        row = self.fetchall(("SELECT AvtorId, FirstName, MiddleName, LastName "
                             "FROM `libavtorname` "
                             "WHERE MATCH (FirstName, MiddleName, LastName) "
                             "AGAINST (%s IN BOOLEAN MODE)"), (for_search(author),)
                            )
        if row and not isinstance(row, Error):
            authors = self.__processing_authors(row)
            res = []
            for aut in authors:
                hb = self.author_have_book(aut.id)
                if isinstance(hb, Error):
                    res.append(aut)
                else:
                    if hb[0] > 0:
                        res.append(aut)
            if res:
                return res
            else:
                return None
        else:
            return None

    def __by_title(self, title):
        row = self.fetchall(
            ("SELECT Title, Title1, Lang, BookId, FileType FROM `libbook` "
             "WHERE MATCH (Title) "
             """AGAINST (%s IN BOOLEAN MODE) """), (for_search(title),)
        )
        if row and not isinstance(row, Error):
            return self.__processing_books(row)
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
