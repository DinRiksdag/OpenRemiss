import sqlite3

from model.remiss import Remiss
from model.remiss_file import RemissFile


class Database(object):
    def __init__(self, path):
        # super(Remiss, self).__init__()
        self.path = path
        self.conn = sqlite3.connect(path)
        self.cursor = self.conn.cursor()

        self.create_tables()

    def get_all_remisser(self):
        self.cursor.execute("SELECT * FROM remisser ORDER BY ID ASC")
        remisser = []

        for row in self.cursor.fetchall():
            remisser.append(Remiss(row[0], row[1], row[2], row[3], row[4]))

        return remisser

    def get_all_remiss_answers(self):
        self.cursor.execute('''
            SELECT *
            FROM files
            WHERE files.type = 'answer'
            ORDER BY ID ASC
        ''')

        files = []

        for row in self.cursor.fetchall():
            files.append(RemissFile(row[0], row[1], row[2],
                                    row[3], row[4], row[5]))

        return files

    def get_popular_remiss_file_organisations(self):
        self.cursor.execute('''
            SELECT organisation,
                   COUNT(organisation) AS num
            FROM files
            GROUP BY lower(organisation)
            HAVING num >= 100
            ORDER BY num DESC
        ''')
        organisation_names = []

        for row in self.cursor.fetchall():
            organisation_names.append(row[0])

        return organisation_names

    def save_remiss(self, remiss):
        self.cursor.execute('''
            INSERT INTO remisser (title, url, date, sender)
            VALUES (?, ?, ?, ?);
            ''',
                            (
                                remiss.title,
                                remiss.url,
                                remiss.date,
                                remiss.sender
                            )
                            )
        return self.cursor.lastrowid

    def save_remiss_file(self, file):
        self.cursor.execute('''
            INSERT INTO files (remiss_id, filename, organisation, url, type)
            VALUES (?, ?, ?, ?, ?);
            ''',
                            (
                                file.remiss_id,
                                file.filename,
                                file.organisation,
                                file.url,
                                file.type
                            )
                            )

    def update_remiss_file(self, file, id):
        self.cursor.execute('''
            UPDATE files SET remiss_id=?,
                             filename=?,
                             organisation=?,
                             url=?,
                             type=?
            WHERE id = ?;
            ''',            (
                                file.remiss_id,
                                file.filename,
                                file.organisation,
                                file.url,
                                file.type,
                                id
                            )
                            )

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS remisser
                (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    title text,
                    url text,
                    date text,
                    sender text
                );
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS files
                (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    remiss_id INTEGER,
                    filename text,
                    organisation text,
                    url text,
                    type text
                );
        ''')

    def drop_tables(self):
        self.cursor.execute("DROP TABLE IF EXISTS remisser;")
        self.cursor.execute("DROP TABLE IF EXISTS files;")

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()
