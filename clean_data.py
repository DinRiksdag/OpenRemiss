from models import Consultee, Document
from service.cleaner import clean_records
from service.storage import DATA_DIR, load, save


def main(data_dir=DATA_DIR):
    documents = load(Document, data_dir)
    consultees = load(Consultee, data_dir)
    clean_records(documents, consultees)
    save(Document, documents, data_dir)
    save(Consultee, consultees, data_dir)
    print("Cleaned responding and invited organisation names.")


if __name__ == "__main__":
    main()
