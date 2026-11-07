import logging

import ocrmypdf
import pikepdf

logger = logging.getLogger(__name__)


class OCR(object):
    @staticmethod
    def ocr(path):
        new_path = path.replace(".pdf", "-ocr.pdf")

        try:
            ocrmypdf.ocr(
                path,
                new_path,
                language="swe",
                deskew=True,
                force_ocr=True,
                progress_bar=False,
            )
        except ocrmypdf.exceptions.EncryptedPdfError:
            logger.info("Trying to decrypt PDF with an empty password: %s", path)
            with pikepdf.Pdf.open(
                path, password="", allow_overwriting_input=True
            ) as pdf:
                pdf.save(path)
            return OCR.ocr(path)

        return new_path
