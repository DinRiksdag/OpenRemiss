import logging

from service.downloader import Downloader
from service.importer import sync_remisser
from service.logging_config import configure_logging
from service.storage import DATA_DIR

logger = logging.getLogger(__name__)


def main(data_dir=DATA_DIR):
    print("Downloading consultation metadata from g0v.se...")
    logger.info("Downloading consultation metadata from g0v.se")
    count = sync_remisser(Downloader.get_remisser(), Downloader.get_codes(), data_dir)
    print(f"Imported {count} consultations from g0v.se.")
    logger.info("Imported %d consultations from g0v.se", count)


if __name__ == "__main__":
    configure_logging("import")
    main()
