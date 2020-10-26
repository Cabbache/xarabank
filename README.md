# xarabank
telegram bot that provides Malta related information

### Features ###
The bot was originally made to provide bus arrival time information, but more functions have been added.

* get arrival time of a specific bus number at the specified bus stop
* get news updates from times of malta
* find from where a surname originates
* low bandwidth usage

### Usage ###
You will need to change the **token** and **chatId** variables at the beginning of xarabank.py
then run with: **python3 xarabank.py**

### What you should know ###
memory.txt holds the bot settings:

**news**: yes if you want the bot to check for news every newspoll seconds<br />
**default**: the default busstop, used so that user does not need to specify busstop<br />
**verbose**: yes if when showing arrival time, also shows bus name<br />
**bus**: default bus number<br />
**newsword**: none if you want to see news of all kinds<br />
**lastnews**: bot uses this when checking for new news<br />
**newspoll**: check news every newspoll seconds<br />

table.txt is a table for bus stops with the following columns:

* bus stop name
* bus stop JSON
* bus stop description

Each column is separated by a pipe (|), records are separated by a newline.
The bus stop JSON is used by the bot when it is checking the busstop time.
To add bus stops to the table, you will need to find their JSON by using the coordinates_busstops.bash script.
This was all made possible from reverse engineering the old tallinja app. The new app has a different api with https://meep.app/

Usage for the script: **./coordinates_busstops.bash [latitude] [longitude]**

This will provide you with a list of JSON for nearby busstops, from which you must recognize the one you are looking for.
Then in table.txt add a new record like this: bus stop name|bus stop JSON|bus stop description.

### Dependencies ###
coordinates_busstops.bash requires (install by apt):
* curl
* jq

xarabank.py requires (install by pip):
* bs4
* requests
* json
* urllib
