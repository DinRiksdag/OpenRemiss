import logging

from service.logging_config import configure_logging


def test_warnings_are_separate_and_logs_do_not_interrupt_terminal(
    tmp_path, capsys, monkeypatch
):
    # Keep pytest's own logging handlers intact.
    root = logging.getLogger()
    monkeypatch.setattr(root, "handlers", [])
    monkeypatch.setattr(root, "level", root.level)
    with monkeypatch.context() as patch:
        patch.setattr(logging, "captureWarnings", lambda capture: None)
        configure_logging("extraction", tmp_path)
    try:
        logger = logging.getLogger("openremiss.test")
        logger.info("Downloaded a PDF")
        logger.warning("Unrecognised invitation list")
        logger.error("Extraction failed")
    finally:
        for handler in root.handlers:
            handler.close()

    details = (tmp_path / "extraction.log").read_text()
    warnings = (tmp_path / "extraction.warnings.log").read_text()
    assert "INFO openremiss.test: Downloaded a PDF" in details
    assert "Downloaded a PDF" not in warnings
    assert "WARNING openremiss.test: Unrecognised invitation list" in warnings
    assert "ERROR openremiss.test: Extraction failed" in warnings
    captured = capsys.readouterr()
    assert str(tmp_path / "extraction.warnings.log") in captured.out
    assert "Unrecognised invitation list" not in captured.out
    assert captured.err == ""
