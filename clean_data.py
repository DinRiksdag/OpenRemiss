import logging

from models import Consultee, Document
from service.cleaner import clean_records
from service.logging_config import configure_logging
from service.storage import DATA_DIR, load, save

logger = logging.getLogger(__name__)


def main(data_dir=DATA_DIR):
    documents = load(Document, data_dir)
    consultees = load(Consultee, data_dir)
    logger.info(
        "Cleaning %d documents and %d invited names", len(documents), len(consultees)
    )
    clean_records(documents, consultees)
    save(Document, documents, data_dir)
    save(Consultee, consultees, data_dir)
    print("Cleaned responding and invited organisation names.")
    logger.info("Cleaned responding and invited organisation names")


if __name__ == "__main__":
    configure_logging("cleaning")
    main()
