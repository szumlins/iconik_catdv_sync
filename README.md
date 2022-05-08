# CatDV to iconik synchronizer

This package contains 3 scripts coupled with Worker Node actions that will allow you to synchronize your CatDV asset proxies to Cantemo's iconik platform with metadata

## Prerequisites

    - Mac or Linux OS only (sorry, no Windows)
    - >=CatDV Worker Node 8.0
    - >=Python 3
    - pip
    - virtualenv
    - MediaInfo binary installed
    

## Installing

Make sure you have virtualenv installed on your system.  First ensure you have pip installed (https://pip.pypa.io/en/stable/installing/).  Then install virtualenv:
```
pip install virtualenv
```
Next, clone this package to the location you wish to install and run create a virtualenv and install the requirements 
```
cd /path/to/my/catdv-iconik-sync/
git clone https://github.com/szumlins/iconik_catdv_sync
virtualenv .
source bin/activate .
pip install -r requirements.txt
```

You should now have all packages required to run the scripts.

## Configuration

There are two configuration files that you must first create for these scripts to work.  The first is your config.ini file, the second is a metadata map configuration that tells the tool which fields in CatDV equate to which fields in iconik

### config.ini
| key | description |
| -------------- | ------------------------------------------------------------------------ |
| app-id | This is the AppID created in iconik to allow API use |
| auth-token | This is the Auth-Token created in iconik to allow API use |
| iconik-url | This is the url to the iconik domain |
| view-id | This is the view your AppID has rights to write into |
| catdv-id-field | This is the field in iconik where we will store the unique CatDV item ID | 

### metadata-map.json

This file contains a formatted json key:value pair with your iconik field ID and the equivalent CatDV field ID.  Here is an example file:

```
{
    "field_map" : [
        {"iconik_field_id":"Department","catdv_field_id":"USER11"},
        {"iconik_field_id":"Keywords","catdv_field_id":"USER10"},
        {"iconik_field_id":"Producer","catdv_field_id":"USER1"},
        {"iconik_field_id":"Readyforweb","catdv_field_id":"USER12"},
        {"iconik_field_id":"description","catdv_field_id":"NOTES"}
    ]
}
```
Simple put a list of dicts with the appropriate mapping and save

### Worker node configuration

There are three separate actions you need to create in worker node.  Here are the raw XML files that you can import and then modify by hand.  First is the action to create a new item in iconik, including proxy upload.  It is important that you properly configure you CatDV server to have a new metadata view with the following fields:
    - Single Checkbox "Sync to iconik"
    - Read-only plain text field "iconik ID"
    - HTML Field "iconik Link"
    - Multi-Checkbox "Remove", values "Delete from iconik" and "Confirm"

You will need to take note of which fields these are to update your actions.  

In the example actions below, replace all variables in curly braces {} with their appropriate values.

Create new iconik sync item action
```
<?xml version='1.0' encoding='UTF-8' standalone='yes'?>
<!DOCTYPE workerConfig>

<workerConfig>
  <watch skipRest="true" active="true" visible="true">
    <serverWatch isBatch="false" singleShot="false" period="10" onlineOnly="true" complexClips="true" triggerPoll="true" triggerNotif="false" rememberTasks="false" sinceLastScan="false">
      <queryTerm attr="501" id="{Sync to iconik field ID}" fielddef="1063" op="1" params="true" or="false" not="false" case="false"/>
      <queryTerm attr="501" id="{iconik ID field ID}" fielddef="1068" op="4" or="false" not="false" case="true"/>
    </serverWatch>
    <job name="Create new iconik sync item" importer="none" publish="true" publishNew="false" priority="2" mostAtATime="0" mainProcess="false" timeout="7200" preserveRoot="true" openEarly="true" checkXML="true" metaclipMode="filename" timeOfDayTC="true" deleteEmptyDirs="false" useMediaStores="false" downloadRemote="false" mediaRef="original">
      <step action="xml1" path="{temporary path to store XML}/$N.xml"/>
      <step action="exec" path="{path where catdv-iconik-sync is installed}/bin/python {path where catdv-iconik-sync is installed}/iconik-simple-proxy.py -p {path to your CatDV path based proxy root}/$N.mp4" parseOutput="true" ignoreExitStatus="false"/>
      <step action="exec" path="{path where catdv-iconik-sync is installed}/bin/python {path where catdv-iconik-sync is installed}/catdv-metadata.py  -x {temporary path to store XML}/$N.xml -c $I -u ${{iconik ID field ID}}" parseOutput="false" ignoreExitStatus="false"/>
      <step action="set" field="{Sync to iconik field ID}" altID="{Sync to iconik field ID}" value="false"/>
      <step action="publish"/>
      <step action="delete" path="{temporary path to store XML}/$N.xml" other="true"/>
    </job>
  </watch>
</workerConfig>
```
Remove from iconik action
```
<?xml version='1.0' encoding='UTF-8' standalone='yes'?>
<!DOCTYPE workerConfig>

<workerConfig>
  <watch skipRest="true" active="true" visible="true">
    <serverWatch isBatch="false" singleShot="false" period="10" onlineOnly="false" triggerPoll="true" triggerNotif="false" rememberTasks="false" sinceLastScan="false">
      <queryTerm attr="501" id="{Remove field ID}" fielddef="1071" op="8" params="Delete from iconik, Confirm" or="false" not="false" case="false"/>
    </serverWatch>
    <job name="Remove from iconik" importer="none" publish="true" publishNew="false" priority="2" mostAtATime="0" mainProcess="false" timeout="7200" preserveRoot="true" openEarly="true" checkXML="true" metaclipMode="filename" timeOfDayTC="true" deleteEmptyDirs="false" useMediaStores="false" downloadRemote="false" mediaRef="original">
      <step action="exec" path="{path where catdv-iconik-sync is installed}/bin/python {path where catdv-iconik-sync is installed}/iconik-asset-delete.py -u ${{iconik ID field ID}}" parseOutput="false" ignoreExitStatus="false"/>
      <step action="set" field="{Remove field ID}" altID="{Remove field ID}"/>
      <step action="set" field="{Sync to iconik field ID}" altID="{Sync to iconik field ID}"/>
      <step action="set" field="{iconik ID field ID}" altID="{iconik ID field ID}"/>
      <step action="set" field="{iconik Link field ID}" altID="{iconik Link field ID}"/>
      <step action="publish"/>
    </job>
  </watch>
</workerConfig>
```
Update metadata action
```
<?xml version='1.0' encoding='UTF-8' standalone='yes'?>
<!DOCTYPE workerConfig>

<workerConfig>
  <watch skipRest="true" active="true" visible="true">
    <serverWatch isBatch="false" singleShot="false" period="10" onlineOnly="true" complexClips="true" triggerPoll="true" triggerNotif="false" rememberTasks="false" sinceLastScan="false">
      <queryTerm attr="501" id="{Sync to iconik field ID}" fielddef="1063" op="1" params="true" or="false" not="false" case="false"/>
      <queryTerm attr="501" id="{iconik ID field ID}" fielddef="1068" op="4" or="false" not="false" case="true"/>
    </serverWatch>
    <job name="Update iconik sync item" importer="none" publish="true" publishNew="false" priority="2" mostAtATime="0" mainProcess="false" timeout="7200" preserveRoot="true" openEarly="true" checkXML="true" metaclipMode="filename" timeOfDayTC="true" deleteEmptyDirs="false" useMediaStores="false" downloadRemote="false" mediaRef="original">
      <step action="xml1" path="{temporary path to store XML}/$N.xml"/>
      <step action="exec" path="{path where catdv-iconik-sync is installed}/bin/python {path where catdv-iconik-sync is installed}/catdv-metadata.py  -x {temporary path to store XML}/$N.xml -c $I -u ${{iconik ID field ID}}" parseOutput="false" ignoreExitStatus="false"/>
      <step action="set" field="{Sync to iconik field ID}" altID="{Sync to iconik field ID}" value="false"/>
      <step action="publish"/>
      <step action="delete" path="{temporary path to store XML}/$N.xml" other="true"/>
    </job>
  </watch>
</workerConfig>
```

## Troubleshooting

In your install directory, there will be a logs folder.  One for the proxy/upload script and one for metadata updates.  If you are getting errors or Worker is not completing its tasks/failing, check the appropriate log for the appropriate action.  The delete script has no log.




