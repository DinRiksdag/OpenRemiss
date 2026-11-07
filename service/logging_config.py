import logging
from pathlib import Path

from service.storage import DATA_DIR


def configure_logging(command: str, log_dir: Path = DATA_DIR.parent / "tmp" / "logs"):
    log_dir.mkdir(parents=True, exist_ok=True)
    details = log_dir / f"{command}.log"
    warnings = log_dir / f"{command}.warnings.log"
    warning_handler = logging.FileHandler(warnings, encoding="utf-8")
    warning_handler.setLevel(logging.WARNING)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(details, encoding="utf-8"), warning_handler],
        force=True,
    )
    logging.captureWarnings(True)
    print(f"Logs: {details}\nWarnings and errors: {warnings}")
