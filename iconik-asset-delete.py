import requests
import configparser as ConfigParser
import argparse
import os
#provide an interface to run from the cli without a config file
parser = argparse.ArgumentParser(description='Create a new object in iconik with a proxy file.  Returns object ID on success')
parser.add_argument('-u','--asset-id',dest='new_id',type=str,help="iconik asset id to delete",required=True)
parser.add_argument('-a','--app-id',dest='app_id',type=str,help="iconik AppID")
parser.add_argument('-t','--token',dest='token',type=str, help="iconik App Token")
parser.add_argument('-i','--iconik-host',dest='host',type=str,help="URL for iconik domain, default is 'https://app.iconik.io'",default='https://app.iconik.io/')
cli_args = parser.parse_args()

try:
    config = ConfigParser.RawConfigParser(allow_no_value=True)
    config.read(os.path.dirname(os.path.realpath(__file__)) + "/config/config.ini")
    # define vars based on config file
    app_id = config.get('iconik','app-id')
    token = config.get('iconik','auth-token')
    url = config.get('iconik','iconik-url')
except Exception as e:
    # define vars based on cli inputs
    app_id = cli_args.app_id
    token = cli_args.token
    url = cli_args.host

new_id = cli_args.new_id
headers = {'App-ID':app_id,'Auth-Token':token}

try:
    requests.delete(url + 'API/assets/v1/assets/' + new_id +'/',headers=headers)
except Exception as e:
    print(str(e))
    exit(1)