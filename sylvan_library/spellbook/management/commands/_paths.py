from os import path
import logging

json_zip_download_url = "http://mtgjson.com/json/AllSets-x.json.zip"
data_folder = path.abspath('spellbook/data')
json_zip_path = path.join(data_folder, 'AllSets-x.json.zip')
json_data_path = path.join(data_folder, 'AllSets-x.json')
pretty_json_path = path.join(data_folder, 'AllSets-x-pretty.json')

language_json_path = path.join(data_folder, 'languages.json')
rarity_json_path = path.join(data_folder, 'rarities.json')

log_file_path = path.abspath('spellbook.log')

logging.basicConfig(filename=log_file_path,
                    level=logging.DEBUG,
                    format='%(levelname)s %(asctime)s %(message)s')
