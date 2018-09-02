
#
#	 RemissScraper, scrapes Regeringen.se for remisser    
#    Copyright (C) 2018 DinRiksdag
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#	along with this program. If not, see <http://www.gnu.org/licenses/>.
#


# Notice, only runs on Python 3.6 or newer

import urllib.request

import json

import html

import sqlite3
conn = sqlite3.connect('scraped.db')

amount = 1000

url = f"https://www.regeringen.se/Filter/GetFilteredItems?filterType=Taxonomy&filterByType=FilterablePageBase&preFilteredCategories=2099&rootPageReference=0&page=1&pageSize={amount}&displayLimited=true&sortAlphabetically=False"

contents = urllib.request.urlopen(url).read()

jsonData = json.loads(contents)

htmlData = jsonData['Message']

htmlData = html.unescape(htmlData)

htmlData = htmlData[htmlData.index('<li'):htmlData.index('</ul')]

class Remiss(object):
	"""docstring for Remiss"""
	def __init__(self, url, title, date, sender):
		#super(Remiss, self).__init__()
		self.url = url
		self.title = title
		self.date = date
		self.sender = sender
	def __str__(self):
		return f"{self.title}\n{self.date} från {self.sender}\n{self.url}\n"
		
splitHtmlData = htmlData.strip().split('</li>')

Remisser = []

for htmlData in splitHtmlData:
	htmlData = htmlData.strip()
	if htmlData == "":
		continue

	temp1 = htmlData[htmlData.index("<a href"):htmlData.index("</a>")]
	url = temp1[temp1.index("\"")+1:temp1.index("\">")]
	title = temp1[temp1.index("\">")+2:]

	date = htmlData[htmlData.index("<time datetime=\"")+16:htmlData.index("<time datetime=\"")+26]

	htmlData2 = htmlData[htmlData.index("</time>")+6:]
	htmlData2 = htmlData2[htmlData2.index("</a>")+4:]

	try:
		sender = htmlData2[htmlData2.index("\">")+2:htmlData2.index("</a>")]
	except Exception as e:
		sender = ""

	Remisser.append(Remiss(url, title, date, sender))

c = conn.cursor()

c.execute('''
	CREATE TABLE IF NOT EXISTS remisser
	(date text, title text, url text, sender real);
''')

for remiss in Remisser:
	c.execute(f"INSERT INTO remisser VALUES ('{remiss.date}','{remiss.title}','{remiss.url}','{remiss.sender}');")

conn.commit()

conn.close()
