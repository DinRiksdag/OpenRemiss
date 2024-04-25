
from rapidfuzz import fuzz

from service.database import Database
from service.cleaner import Cleaner
from service.file_manager import FileManager
from database.consultee import Consultee

import pandas as pd

import service.wikidata as wikidata

# RESET_DB = False

# if RESET_DB:
#     Database.empty_column(Consultee, Consultee.cleaned_name)
#     Database.commit()

# popular_names = Database.get_popular_names(1)
# print(popular_names)
# print(len(popular_names))

# print('Getting all consultees...')
# all_consultees = Consultee.query.group_by(Consultee.name).filter(Consultee.cleaned_name == None).all()

# print('Starting...')
# for consultee in all_consultees:
#     if not consultee.cleaned_name:
#         consultee.cleaned_name = Cleaner.replace_by_popular(consultee.name, 99)
#         Database.commit()

RESET_WIKIDATA = True
GOV_LIST = 'tmp/government_organisations.csv'
if RESET_WIKIDATA or not FileManager.filepath_exists(GOV_LIST):
    print('Downloading names for all Swedish public sector from Wikidata...')
    pd.DataFrame(wikidata.get_government_organisations(), columns=['organisation']).to_csv(GOV_LIST, index=None)

gov_list = pd.read_csv(GOV_LIST)['organisation'].to_list()


all_consultees = Consultee.query.group_by(Consultee.name).all()
#.group_by(Consultee.name).filter(Consultee.cleaned_name == None)

print('Starting...')
for consultee in all_consultees:
    name = consultee.name
    cleaned_name = Cleaner.closest_in_list(consultee.name, gov_list, 90)

    if not cleaned_name:
        continue

    same = Consultee.query.filter(Consultee.name == name).all()
    for item in same:
        item.cleaned_name = cleaned_name

    Database.commit()
    print(f'Cleaned "{name}" {len(same)} times.')
