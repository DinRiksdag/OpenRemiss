import json

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent

class Selenium_Driver(object):

    def __init__(self):
        options = Options()
        options.headless = True
        ua = UserAgent()
        userAgent = ua.random
        options.add_argument(f'user-agent={userAgent}')

        self.d = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    def get(self, url):
        self.d.get(url)
        return self.d.page_source

    def get_json(self, url):
        response = self.get(url)

        return json.loads(response[response.index('{'):response.index('}') + 1])
