This code is the result of a **[Civic Tech](https://civictech.se) hackathon in Göteborg in September 2018** 🤓.
It was written by [Emil Hemdal](https://github.com/emilhem), Albin and [Pierre Mesure](https://github.com/PierreMesure).

# What does it do? 🖨

This is a script that scraps data from [regeringen.se](regeringen.se).
For now, it only looks for [remisser](https://sv.wikipedia.org/wiki/Remiss),
lists them and builds a list of all the organisations that have answered each remiss.

The result is saved in an SQL database.

# Why? 📕📗📘

<img src='./illustration.svg'/>

**Regeringskansliet**, the Swedish government's chancellery, has very little open data.
Theoretically, all of their documents are available publicly on [regeringen.se](regeringen.se),
but a weak search engine (which doesn't search for keywords through the content of the page or documents) and the lack of structured data (most of the documents are available as PDF with various formattings)
make it virtually impossible for journalists, researchers and activists from civil society to delve in this information and scrutinize the government's actions.

Apart from this valuable work by counterpowers, this lack of open structured data also prevents civil servants from working efficiently
and other public agencies to use the information released.

The Swedish parliament, **Riksdagen**, includes some of the government's documents on their website (bills, [SOUs](https://en.wikipedia.org/wiki/Statens_offentliga_utredningar))
but they get this as PDF from Regeringskansliet and have to parse the content to display it, making it harder for them to inform citizens.

The end result is impossible to use in a good way.
Formatting is lost, page numbers and tables get inserted in the text and no structure is preserved.
See example [here](http://www.riksdagen.se/sv/dokument-lagar/dokument/proposition/ett-klimatpolitiskt-ramverk-for-sverige_H403146/html).

# Goal 🎯

Our goal with this small script is to show how ridiculously hard it is to find simple information such as:
- which organisations does the government ask?
- which organisations answer?
- how many times have they asked each organisation and how many times do they answer?

Statistical information would already help counterpowers to say who the government is picking to help them to shape a bill.
Big interest groups? NGOs? Local associations? These are important democratic issues.

And that would only require a structured list of remisser and remisssvar.

If Regeringskansliet was also publishing remissvar's content in a structured format, techniques such as semantic analysis
could be applied to analyze the proximity of a remissvar and a bill to determine which organisations influenced most.
This is already done to study the impact of lobbying in the [EU](https://www.politico.eu/article/7-tools-on-eu-governance-brussels-lobbying-governance-open-data/)
and the [US](https://www.frontiersin.org/articles/10.3389/fdata.2018.00003/full) parliaments.

# First results 📊

The hackathon was just one day and we realised while doing it that the quality of the "data" poorer than expected:
- [regeringen.se](regeringen.se) only shows the last 495 remisser, the oldest one being from the 23/11/2016.
- we used the file names as the name of the organisation (for lack of something better) and although that worked most of the time,
a lot of names include a typo (`Stockholm universitet` instead of `Stockholms universitet`), a number (`35. Stockholms universitet`)
or something else which requires manual cleaning of the data.

However, we managed to get a shortlist of organisations sorted by which answers the most to remisser,
and we filtered it manually to show only interest groups:

# 🏆

| Rank | Organisation                | #  |
| --   | --------------------------- | -- |
| 🥇    | Svenskt näringsliv          | 34 |
| 🥇    | Sveriges advokatsamfund     | 34 |
| 🥉    | LO (with several names)     | 33 |
| 4    | Företagarna                 | 29 |
| 5    | Skogsindustrierna           | 28 |
| 6    | Naturskyddsföreningen       | 26 |
| 7    | Avfall Sverige              | 25 |
| 7    | Lantbrukarnas Riksförbund   | 25 |
| 9    | Sveriges Byggindustrier     | 23 |
| 10   | Näringslivets Regelnämnd    | 22 |
| 11   | Svensk Handel               | 21 |
| 12   | Svenska Bankföreningen      | 20 |
| 13   | Energiföretagen Sverige     | 28 |
| 14   | Småföretagarnas Riksförbund | 17 |
| 15   | Sparbankernas Riksförbund   | 13 |

You can run the script yourself to get similar results.

## What does that show us? 🧐

Nothing spectacular but we are releasing it as a snapshot of what could be done by more people, with more structured data and more time.

# How can I contribute? 🙌

Did we manage to get your attention with this small demo?
Do you want to see more insights on all the information that Regeringskansliet has but doesn't publish in a usable format?

There are 3 ways you can help:
- if you can script, fork this project and try to fetch and analyse more data from [regeringen.se](regeringen.se)!
Write some code to clean the data or to visualise it! 👩🏽‍💻
- if you can't but have a profession/occupation which would benefit from having this data available (journalist, politician, researcher),
contact the government to ask them to do it! Explain to them what you could do with it. 👨🏻‍⚕️
- ask the government to reform its [offentlighetsprincip](https://sv.wikipedia.org/wiki/Offentlighetsprincipen)
to require that any piece of public data be available online in a structured format.
Canada, the UK or France are doing it, it's time for Sweden to catch up! 🙋🏻‍♀️

And don't hesitate to contact us, we love hearing from opengov enthusiasts! ❤️
