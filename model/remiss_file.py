class RemissFile(object):

    def __init__(self, id, remiss_id, filename, organisation, url, type):
        self.id = id
        self.remiss_id = remiss_id
        self.filename = filename
        self.organisation = organisation
        self.url = url
        self.type = type

    def __str__(self):
        return f"{self.remiss_id}\n{self.filename} at {self.url}\n"
