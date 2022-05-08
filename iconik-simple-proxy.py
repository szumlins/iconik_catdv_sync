import configparser as ConfigParser
import requests
import json
import os
import argparse
import logging
import logging.handlers
import hashlib
import shutil

#provide an interface to run from the cli without a config file
parser = argparse.ArgumentParser(description='Create a new iconik proxy item from a path')
parser.add_argument('-p','--proxy-file',dest='proxy',type=str,help="Full path to proxy file to upload",required=True)
parser.add_argument('-o','--original-file',dest='original',type=str,help="Full path to original file to link")
parser.add_argument('-a','--app-id',dest='app_id',type=str,help="iconik AppID")
parser.add_argument('-t','--token',dest='token',type=str, help="iconik App Token")
parser.add_argument('-i','--iconik-host',dest='host',type=str,help="URL for iconik domain, default is 'https://app.iconik.io'",default='https://app.iconik.io/')
parser.add_argument('-u','--iconik-id-field',dest='iconik_id_field',type=str,help="Field ID in CatDV where iconik asset ID will reside")
parser.add_argument('-v','--iconik-url-field',dest='iconik_url_field',type=str,help="Field ID in CatDV where iconik asset link will reside")
parser.add_argument('--debug',dest='debug',default=False,action='store_true',help="Don't write files, just output metadata to console")
cli_args = parser.parse_args()

#check if log file exists
if not os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)),'logs')):
    os.makedirs(os.path.join(os.path.dirname(os.path.realpath(__file__)),'logs'))
try:
    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),'logs','proxy.log'),'x'):
        print("Creating new log file")
except FileExistsError:
    print("Found existing log file")

import mediainfo

#check if mediainfo is installed
if shutil.which('mediainfo') is None:
    print("You need to have mediainfo installed and available in your path for this script to work, exiting")
    exit(1)

#set up our log
logger = logging.getLogger()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler = logging.handlers.RotatingFileHandler(os.path.dirname(os.path.realpath(__file__)) + "/logs/proxy.log", maxBytes=104857600, backupCount=5)
handler.setFormatter(formatter)
logger.addHandler(handler)
if cli_args.debug is True:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

def generate_checksum(path):
    hasher = hashlib.md5()
    with open('myfile.jpg', 'rb') as afile:
        buf = afile.read()
        hasher.update(buf)
    return hasher.hexdigest()
    

#parse out only the filename, strip path and extension
def get_filename_for_title(path):
    return os.path.splitext(os.path.basename(path))[0]

#create the full proxy with only path as an input
def create_proxy(path):
    #try creating our placeholder
    data = {
        "analyze_status": "N/A",
        "archive_status": "NOT_ARCHIVED",
        "is_online": "false",
        "status": "ACTIVE",
        "title": get_filename_for_title(path),
        "type": "ASSET"
    }
    try:
        r = requests.post(url + 'API/assets/v1/assets/',headers=headers,data=json.dumps(data))
        logger.debug(r.text)
    except:
        logger.error('Could not connect to iconik')
        if 'errors' in r.json():
            logger.error(r.json()['errors'])
        exit(1)       
    new_id = r.json()['id']

    #try creating a proxy
    media_info = mediainfo.get_proxy_metadata(path)
    data = {}
    try:
        data["asset_id"] = new_id
    except:
        pass
    try:
        data["bit_rate"] = media_info['bit_rate']
    except:
        pass        
    try:
        data["codec"] = media_info['codec']
    except:
        pass        
    try:
        data["filename"] = os.path.basename(path)
    except:
        pass        
    try:
        data["format"] = media_info['format']
    except:
        pass        
    try:
        data["frame_rate"] = media_info['frame_rate']
    except:
        pass        
    try:
        data["is_drop_frame"] = media_info['is_drop_frame']
    except:
        pass        
    try:
        data["name"] = os.path.basename(path)
    except:
        pass        
    try:
        data["resolution"] = media_info['resolution']
    except:
        pass        
    try:    
        data["start_time_code"] = media_info['start_time_code']
    except:
        pass        
    try:
        data["status"] = "AWAITED"
    except:
        pass        
    try:
        data["storage_id"] = None
    except:
        pass        
    try:
        r = requests.post(url + 'API/files/v1/assets/' + new_id + '/proxies/',headers=headers, data=json.dumps(data))
        logger.info('Creating new proxy object ' + r.json()['id'])
        logger.debug(r.text)
    except:
        logger.error('Could not connect to iconik')
        if 'errors' in r.json():
            logger.error(r.json()['errors'])
        exit(1)
    #check if we got our resumable URL
    if 'upload_url' in r.json():
        proxy_id = r.json()['id']
        logger.info('Getting resumable upload URL')
        g = requests.post(r.json()['upload_url'],headers={'x-goog-resumable':'start','Content-Length':'0'})
        #check if we got our target URL
        if 'location' in g.headers:
            logger.info('Successfully got upload URL')
            logger.debug(g.headers)
            #upload our file
            try:
                with open(path, 'rb') as data:
                    logger.info('Starting upload of ' + path)
                    f = requests.put(g.headers['location'],headers={'x-goog-resumable':'start','Content-type':'application/octet-stream'},data=data)
                    logger.debug(f.text)
            except:
                logger.error('Upload failed!')
                #upload failed, kill what we've done
                logger.error('Deleting empty proxy ' + proxy_id)
                requests.delete(url + 'API/files/v1/assets/' + new_id + '/proxies/' + proxy_id,headers=headers)
                logger.error('Deleting empty asset ' + new_id)
                requests.delete(url + 'API/assets/v1/assets/' + new_id +'/',headers=headers)                
                exit(1)
            if f.status_code == 200:
                logger.info('Upload completed successfully')
                try:
                    data = {
                        "status":"CLOSED"
                    }
                    
                    logger.info('Setting proxy ' + proxy_id + ' to CLOSED')
                    r = requests.patch(url + "API/files/v1/assets/" + new_id + "/proxies/" + proxy_id + '/',headers=headers,data=json.dumps(data))
                    logger.debug(r.text)

                    data = {
                        "type":"ASSET"
                    }
                    logger.info('Setting asset completion for ' + new_id)
                    r = requests.patch(url + 'API/assets/v1/assets/' + new_id + '/',headers=headers,data=json.dumps(data))
                    logger.debug(r.text)
                    logger.info('Generating keyframes for asset ' + new_id)
                    r = requests.post(url + 'API/files/v1/assets/' + new_id + '/proxies/' + proxy_id + '/keyframes/',headers=headers)
                    logger.debug(r.text)
                except:
                    logger.error('Error finalizing asset')
                    requests.delete(url + 'API/assets/v1/assets/' + new_id +'/',headers=headers)
                    exit()
                logger.info('New asset ' + new_id + ' created with proxy from ' + path)
                return new_id
            else:
                logger.error('Something went wrong with proxy upload, cleaning up empty asset ' + new_id)
                requests.delete(url + 'API/assets/v1/assets/' + new_id +'/',headers=headers)
    else:
        logger.error('Could not get upload URL')

#link our high res file 
def link_isg(path):
    #attempt to generate checksum first
    try:    
        logging.info("Attempting to generate checksum for " + path)
        checksum = generate_checksum(path)
        logging.info("Checksum for " + path + " is " + checksum)
    except:
        checksum = None
        logging.error("Could not generate checksum for " + path)
    
    media_info = mediainfo.get_file_metadata(path)
    data = {
        
    }

#start the actual script
#parse our config file
try:
    config = ConfigParser.RawConfigParser(allow_no_value=True)
    config.read(os.path.dirname(os.path.realpath(__file__)) + "/config/config.ini")
    logger.info('Using config file ' + os.path.dirname(os.path.realpath(__file__)) + '/config/config.ini')
         
    # define vars based on config file
    proxy_file = cli_args.proxy
    logger.debug('Proxy File: ' + proxy_file)
    app_id = config.get('iconik','app-id')
    logger.debug('App-ID: ' + app_id)    
    token = config.get('iconik','auth-token')
    logger.debug('Auth-Token: ' + token)    
    url = config.get('iconik','iconik-url')
    logger.debug('URL: ' + url)    
    iconik_id_field = config.get('catdv','iconik-id-field')
    logger.debug('CatDV iconik ID field: ' + iconik_id_field)   
    iconik_url_field = config.get('catdv','iconik-url-field')
    logger.debug('CatDV iconik URL field: ' + iconik_url_field)    

except:
    # define vars based on cli inputs
    logger.info('Could not open config file, falling back on cli arguments')
    proxy_file = cli_args.proxy
    app_id = cli_args.app_id
    token = cli_args.token
    url = cli_args.host
    iconik_id_field = cli_args.iconik_id_field
    iconik_url_field = cli_args.iconik_url_field

#validate our vars
try:
    proxy_file
    if proxy_file == None:
        logger.error('Proxy file path not set')
        exit(1)
except:
    logger.error('Proxy file path not defined')
    exit(1)
try:
    app_id
    if app_id == None:
        logger.error('App-ID not set')
        exit(1)
except:
    logger.error('App-ID is not defined')
    exit(1)
try:
    token
    if token == None:
        logger.error('Auth-Token not set')
        exit(1)
except:
    logger.error('Auth-Token not defined')
    exit(1)    
try:
    url
    if url == None:
        logger.error('iconik URL not set')
        exit(1)
except:
    logger.error('iconik URL not defined')
    exit(1)    
try:
    iconik_id_field
    if iconik_id_field == None:
        logger.error('iconik ID field not set')
        exit(1)
except:
    logger.error('iconik ID field not defined')
    exit(1)
try:
    iconik_url_field
    if iconik_url_field == None:
        logger.error('iconik URL field not set')
        exit(1)
except:
    logger.error('iconik URL field not defined')
    exit(1)    

#config our headers for auth
headers = {'App-ID':app_id,'Auth-Token':token}

#check if file exists
if not os.path.isfile(proxy_file):
    logger.error('File ' + proxy_file + ' does not exist')
    exit(1)

#try to connect to iconik
try:
    r = requests.get(url + 'API/auth/v1/auth/token/',headers=headers)
except:
    logger.error('Could not connect to iconik')
    exit(1)

#validate auth key
if len(r.json()) == 0:
    logger.error('iconik Auth Key or Token invalid')
    exit(1)
if 'errors' in r.json():
    logger.error(r.json()['errors'])
    exit(1)

#try our job
my_id = create_proxy(proxy_file)
print ("@" + iconik_id_field + "=" + my_id)
print ("@" + iconik_url_field + "=<a href=\"https://app.iconik.io/asset/" + my_id + "/\" target=\"_new\">iconik link</a>")