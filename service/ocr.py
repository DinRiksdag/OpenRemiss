import ocrmypdf
import pikepdf

class OCR(object):

    @staticmethod
    def ocr(path):
        new_path = path.replace('.pdf', '-ocr.pdf')

        try:
            ocrmypdf.ocr(
                path,
                new_path,
                language='swe',
                deskew=True,
                force_ocr=True
                )
        except ocrmypdf.exceptions.EncryptedPdfError:
            print('Document seems to be encrypted, attempting to decrypt with empty password.')
            with pikepdf.Pdf.open(path, password='', allow_overwriting_input=True) as pdf:
                pdf.save(path)
            return OCR.ocr(path)

        return new_path
