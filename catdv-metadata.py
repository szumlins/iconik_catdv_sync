import configparser as ConfigParser
import json
import xml.etree.ElementTree as ET
import argparse
import requests
import os
import logging
import logging.handlers

#set up cli options
parser = argparse.ArgumentParser(description='Parses CatDV xml and patches iconik metadata')
parser.add_argument('-u','--iconik-id',dest='iconik_id',type=str,help="iconik asset id",required=True)
parser.add_argument('-a','--app-id',dest='app_id',type=str,help="iconik AppID")
parser.add_argument('-t','--token',dest='token',type=str, help="iconik App Token")
parser.add_argument('-x','--xml',dest='xml_path',type=str, help="path to catdv v1 xml file",required=True)
parser.add_argument('-v','--view',dest='iconik_view',type=str, help="iconik metadata view id")
parser.add_argument('-i','--iconik-host',dest='host',type=str,help="URL for iconik domain, default is 'https://app.iconik.io'",default='https://app.iconik.io/')
parser.add_argument('-c','--catdv-id',dest='catdvid',type=str,help="Unique ID from CatDV database",required=True)
parser.add_argument('--debug',dest='debug',default=False,action='store_true',help="Enable log debug mode")
cli_args = parser.parse_args()

#set up our log
logger = logging.getLogger()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler = logging.handlers.RotatingFileHandler(os.path.dirname(os.path.realpath(__file__)) + "/logs/metadata.log", maxBytes=104857600,backupCount=5)
handler.setFormatter(formatter)
logger.addHandler(handler)

if cli_args.debug is True:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)



try:
    config = ConfigParser.RawConfigParser(allow_no_value=True)
    config.read(os.path.dirname(os.path.realpath(__file__)) + "/config/config.ini")
    logger.info('Using config file ' + os.path.dirname(os.path.realpath(__file__)) + '/config/config.ini')

    # define vars based on config file
    xml_file = cli_args.xml_path
    logger.debug('XML File: ' + xml_file)
    app_id = config.get('iconik','app-id')
    logger.debug('App-ID: ' + app_id)    
    token = config.get('iconik','auth-token')
    logger.debug('Auth-Token: ' + token)    
    url = config.get('iconik','iconik-url')
    logger.debug('URL: ' + url)    

except Exception as e:
    logger.debug(str(e))
    # define vars based on cli inputs
    logger.info('Could not open config file, falling back on cli arguments')
    xml_file = cli_args.xml_path
    app_id = cli_args.app_id
    token = cli_args.token
    url = cli_args.host

#validate our vars

try:
    app_id
    if app_id == None:
        logger.error('App-ID not set')
        exit(1)
except Exception as e:
    logger.debug(str(e))
    logger.error('App-ID is not defined')
    exit(1)
try:
    token
    if token == None:
        logger.error('Auth-Token not set')
        exit(1)
except Exception as e:
    logger.debug(str(e)) 
    logger.error('Auth-Token not defined')
    exit(1)    
try:
    url
    if url == None:
        logger.error('iconik URL not set')
        exit(1)
except Exception as e:
    logger.debug(str(e))
    logger.error('iconik URL not defined')
    exit(1)    

catdv_id_field = config.get('iconik','catdv-id-field')

if config.get('iconik','view-id') is None:
    iconik_view = cli_args.iconik_view
else:
    iconik_view = config.get('iconik','view-id')

#config our headers for auth
headers = {'App-ID':app_id,'Auth-Token':token}

#load our metadata map
logger.debug('Reading metadata map')
try:
    logger.debug('Attempting to read file ' + os.path.dirname(os.path.realpath(__file__)) + '/config/metadata-map.json')
    with open(os.path.dirname(os.path.realpath(__file__)) + '/config/metadata-map.json','r') as json_file:  
        metadata_map = json.load(json_file)
except Exception as e:
    logger.debug(str(e))
    logger.error('Could not parse metadata map')
    exit(1)
#get all of the mapped fields that exist in this xml
logger.debug('Finding if mapped fields exist in CatDV metadata')
catdv_fields = []
for fields in metadata_map['field_map']:
    logger.debug('Found field ' + fields['catdv_field_id'])
    catdv_fields.append(fields['catdv_field_id'])

#parse the xml, map the fields, build a new dict
iconik_metadata = {}
logger.info('Opening CatDV XML ' + xml_file)
try:
    tree = ET.parse(xml_file)
except Exception as e:
    logger.debug(str(e))
    logging.error('Could not parse CatDV XML file ' + xml_file)
    exit(1)
root = tree.getroot()
logger.debug('Looping through mapped CatDV fields and getting values')
for clip in root:
    for tags in clip:
        if tags.tag in catdv_fields:
            logger.debug('Found field ' + tags.tag + '. Contains value ' + tags.text)
            iconik_metadata[next((item['iconik_field_id'] for item in metadata_map['field_map'] if item['catdv_field_id'] == tags.tag),None)] = tags.text

#create iconik metadata json
iconik_post_data = {
    'metadata_values':{}
}
for field,value in iconik_metadata.items():
    iconik_post_data['metadata_values'][field] = {'field_values':[{"value":value}]}

if catdv_id_field is not None:
    iconik_post_data['metadata_values'][catdv_id_field] = {'field_values':[{"value":cli_args.catdvid}]}

logger.debug(json.dumps(iconik_post_data,indent=4,sort_keys=True))

#post data to iconik
try:
    logger.info('Updating metadata for iconik asset ' + cli_args.iconik_id)
    r = requests.put(url + 'API/metadata/v1/assets/' + cli_args.iconik_id + '/assets/' + cli_args.iconik_id + '/views/' + iconik_view + '/',headers=headers,data=json.dumps(iconik_post_data,indent=4,sort_keys=True))
    logger.debug('Respose text:\n' + r.text)
    logger.info('Made call: ' + url + 'API/metadata/v1/assets/' + cli_args.iconik_id + '/assets/' + cli_args.iconik_id + '/views/' + iconik_view + '/')
    logger.info('Response Status Code: ' + str(r.status_code))
except Exception as e:
    logger.debug(str(e))
    logger.error('Error updating metadata in iconik for asset ' + cli_args.iconik_id)
    if 'errors' in r.json():
        logger.error(r.json()['errors'])
    exit(1)
