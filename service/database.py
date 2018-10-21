import sqlite3


class Database(object):
    def __init__(self, path):
        # super(Remiss, self).__init__()
        self.path = path
        self.conn = sqlite3.connect(path)
        self.cursor = self.conn.cursor()

    def save_remiss(self, remiss):
        self.cursor.execute("INSERT INTO remisser VALUES (?, ?, ?, ?);",
                            (
                                remiss.date,
                                remiss.title,
                                remiss.url,
                                remiss.sender
                            )
                            )
        return self.cursor.lastrowid

    def save_remiss_file(self, remiss_file):
        self.cursor.execute("INSERT INTO file VALUES (?, ?, ?);",
                            (
                                remiss_file.remiss_id,
                                remiss_file.filename,
                                remiss_file.url
                            )
                            )

    def drop_tables(self):
        self.cursor.execute("DROP TABLE IF EXISTS remisser;")
        self.cursor.execute('''
            CREATE TABLE remisser
            (date text, title text, url text, sender text);
        ''')

        self.cursor.execute("DROP TABLE IF EXISTS file;")
        self.cursor.execute('''
            CREATE TABLE file
            (remiss_id int, filename text, url text);
        ''')

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()
