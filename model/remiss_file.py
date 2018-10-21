class RemissFile(object):

    def __init__(self, remiss_id, filename, url):
        self.remiss_id = remiss_id
        self.filename = filename
        self.url = url

    def __str__(self):
        return f"{self.remiss_id}\n{self.filename} at {self.url}\n"
