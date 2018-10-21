class Remiss(object):

    def __init__(self, url, title, date, sender):
        # super(Remiss, self).__init__()
        self.url = url
        self.title = title
        self.date = date
        self.sender = sender

    def __str__(self):
        return f"{self.title}\n{self.date} from {self.sender}\n{self.url}\n"
