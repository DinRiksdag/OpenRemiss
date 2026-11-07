from service.downloader import Downloader
from service.importer import sync_remisser
from service.storage import DATA_DIR


def main(data_dir=DATA_DIR):
    print("Downloading consultation metadata from g0v.se...")
    count = sync_remisser(Downloader.get_remisser(), Downloader.get_codes(), data_dir)
    print(f"Imported {count} consultations from g0v.se.")


if __name__ == "__main__":
    main()
