from database import base
from service.database import Database
from service.downloader import Downloader
from service.importer import sync_remisser


def main():
    print("Downloading consultation metadata from g0v.se...")
    items = Downloader.get_remisser()
    codes = Downloader.get_codes()
    Database.create_tables()
    with base.db_session() as session, session.begin():
        count = sync_remisser(items, codes, session)
    print(f"Imported {count} consultations from g0v.se.")


if __name__ == "__main__":
    main()
