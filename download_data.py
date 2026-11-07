import argparse
import logging

from service.downloader import Downloader
from service.importer import sync_remisser
from service.logging_config import configure_logging
from service.storage import DATA_DIR

logger = logging.getLogger(__name__)


def main(data_dir=DATA_DIR, *, include_source_exceptions=False):
    print("Downloading consultation metadata from g0v.se...")
    logger.info("Downloading consultation metadata from g0v.se")
    count = sync_remisser(
        Downloader.get_remisser(),
        Downloader.get_codes(),
        data_dir,
        include_source_exceptions=include_source_exceptions,
    )
    print(f"Imported {count} consultations from g0v.se.")
    logger.info("Imported %d consultations from g0v.se", count)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--include-source-exceptions",
        action="store_true",
        help="Include known mislabelled source attachments using their reviewed types",
    )
    args = parser.parse_args()
    configure_logging("import")
    main(include_source_exceptions=args.include_source_exceptions)
