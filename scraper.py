
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

REGERINGSURL = "https://www.regeringen.se"

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

c.execute("DROP TABLE IF EXISTS remisser;")
c.execute('''
	CREATE TABLE remisser
	(id int, date text, title text, url text, sender text);
''')
c.execute("DROP TABLE IF EXISTS svar;")
c.execute('''
	CREATE TABLE svar
	(remiss_id int, sender text, url text);
''')

try:
	for index, remiss in enumerate(Remisser):
		print(str(index) + " " + remiss.url)

		c.execute("INSERT INTO remisser VALUES (?, ?, ?, ?, ?);", (index+1, remiss.date, remiss.title, remiss.url, remiss.sender))

		# Since regeringens website can't handle long urls (HTTP 414) we need this try/catch
		# We have reported this to them.
		# The url: https://www.regeringen.se/remisser/2016/10/remiss-av-stralsakerhetsmyndighetens-rapport---regeringsuppdrag-att-utreda-effekterna-av-den-s.k.-studsvikslagens-upphavande-samt---skrivelse-med-anmalan-om-avgift-enligt-lagen-om-finansieringen-av-visst-radioaktivt-avfall/
		try:
			contents = html.unescape(urllib.request.urlopen(REGERINGSURL + remiss.url).read().decode('utf-8'))
		except Exception as e:
			continue

		contents = contents[contents.index("<main"):contents.index("</main>")]
		contents = contents[contents.index("<ul"):contents.index("</ul>")]
		remissAnswers = contents.strip().split("</li>")

		conn.commit()

		for remissAnswer in remissAnswers:
			remissAnswer = remissAnswer.strip()
			if remissAnswer == "":
				continue

			try:
				temp1 = remissAnswer[remissAnswer.index("href"):remissAnswer.index("</a>")]
				url = temp1[temp1.index("\"")+1:temp1.index("\">")]
				if temp1.find("(") == -1:
					sender = temp1[temp1.index("\">")+2:]
				else:	
					sender = temp1[temp1.index("\">")+2:temp1.index("(")]

			except Exception as e:
				print(remissAnswer)
				conn.commit()
				conn.close()
				exit()

			c.execute("INSERT INTO svar VALUES (?, ?, ?);", (index + 1, sender, url))
except Exception as e:
	print("crashed")
	print(e)

conn.commit()

conn.close()
