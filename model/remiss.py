class Remiss(object):

    def __init__(self, id, title, url, date, sender):
        self.id = id
        self.title = title
        self.url = url
        self.date = date
        self.sender = sender

    def __str__(self):
        return f"{self.title}\n{self.date} from {self.sender}\n{self.url}\n"
