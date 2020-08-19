#!/usr/bin/env python3

import requests
import json
import urllib
import datetime
import threading
from time import sleep
from bs4 import BeautifulSoup

memory = "memory.txt"
stopsFile = "table.txt"
token="CHANGE THIS" # bot telegram token
Turl = "https://api.telegram.org/bot"+token+"/"
busUrl = "https://www.publictransport.com.mt/appws/StopsMap/GetComingBus"
chatId="CHANGE THIS" # the chat id, may have '-' in front
poll = 200
lastId = -1

def log(message):	
	print(("["+str(datetime.datetime.now())+"]: " + message))

#not digit means its < 2
#returns true if time1 < time2
def smaller(time1, time2):
	if not(time1.isdigit()):
		return True
	elif not(time2.isdigit()):
		return False
	return int(time1) < int(time2)

def getTimes(stop):
	headers = {
		'Content-Type': 'application/json; charset=UTF-8',
		'x-api-version': '1.4.5',
		'User-Agent': 'xarabank'
	}
	r = requests.post(busUrl, data=stop, headers=headers)
	return json.loads(r.text)

def getBusTime(times, busNum):
	goods = []
	for bus in times["Stops"][0]["L"]:
		if bus["N"] == busNum and bus["AT"]:
			goods.append(bus)
	if len(goods) == 0:
		return False
	name = goods[0]["D"]
	ATs = []
	for g in goods:
		if name == g["D"]:
			ATs.append(g["AT"])
	sort = False
	while not(sort):
		sort = True
		for x in range(len(ATs)-1):
			if smaller(ATs[x], ATs[x+1]):
				continue
			sort = False
			tmp = ATs[x]
			ATs[x] = ATs[x+1]
			ATs[x+1] = tmp
	return [ATs, name]

def getUpdates(offset="-1", timeout="0"):
	global lastId
	try:
		r = requests.get(Turl+"getUpdates?offset="+str(offset)+"&timeout="+str(timeout), timeout=(poll+5))
	except requests.exceptions.Timeout:
		log("getUpdates Timeout")
		return False
	except Exception as e:
		log("telegram poll request failed:\n"+str(e))
		sleep(5)
		return False
	if r.status_code != requests.codes.ok:
		log("bad updates status code:\n"+r.text)
		return False
	updates = json.loads(r.text)
	if len(updates["result"]) == 0:#this normally triggers often when nobody sends message
		return False
	if not(updates["ok"]):
		log("result not ok:\n"+str(updates))
		return False
	lastId = getNext(updates)
	return updates

def getOrigin(surname):
	try:
		if not(surname.isalpha()):
			return None
		UA = {'User-agent': 'xarabank'}
		r = requests.get("https://forebears.io/surnames?q="+surname, headers=UA)
		parsed = BeautifulSoup(r.text, features="html.parser")
		data = []
		for div in parsed.body.find('div', attrs={'class':'search-results'}):
			matches = div.find('h6', attrs={'class':'match'}).text
			infos = div.findAll('h6', attrs={'class':'detail-title'})
			if infos is None:
				return None
			data.append(matches)
			for info in infos:
				value = info.find_next_sibling()
				if info.text == "Global Incidence":
					text = value.text
				else:
					text = value['title']
				data.append(text)
			break
		return data
	except Exception as e:
		log("exception in getOrigin:\n"+str(e))
		return False

def getMessage(updates):
	try:
		return updates["result"][0]["message"]
	except:
		log("strange updates:\n"+str(updates))
		return False

def sendText(text):
	log("sending:\n"+text)
	text = urllib.parse.quote_plus(text)
	r = requests.get(Turl+"sendMessage?chat_id="+chatId+"&text="+text)
	return r.status_code == requests.codes.ok

def readConf(setting):
	with open(memory) as mem:
		lines = mem.read().splitlines()
	for line in lines:
		sp = line.split(":")
		if sp[0] == setting:
			return ":".join(sp[1:])
	return False

def writeConf(setting, value):
	with open(memory) as mem:
		lines = mem.read().splitlines()
	new = open(memory, "w")
	for line in lines:
		sp = line.split(":")
		if sp[0] != setting:
			new.write(line+"\n")
			continue
		new.write(setting+":"+str(value)+"\n")
	new.close()
	return True

def getNames():
	names = ""
	table = open(stopsFile, "r")
	for line in table:
		split = line.split("|")
		name = split[0]
		names += name + "\n"
	return names

#reads stopsfile to get whole line about busstop info (name, json, description)
def getRecord(stopName):
	table = open(stopsFile, "r")
	for line in table:
		split = line.split("|")
		name = split[0]
		if name == stopName:
			return line
	return False

#read stopsfile to get json of busstop
def getStop(stopName):
	rec = getRecord(stopName)
	if not(rec):
		return False
	return rec.split("|")[1]

def trace(surname):
	infos = getOrigin(surname)
	if infos is None:
		sendText("No such surname")
		return
	elif infos == False:
		sendText("An error occured")
		return
	sendText(surname+": "+infos[0]+"""
Global incidence: """+infos[1]+"""
Most prevalent: """+infos[2]+"""
Highest density: """+infos[3])

def alert(stopName, busNumber):
	log("issuing time")
	stp = getStop(stopName)
	if not(stp):
		sendText("No such name: " + stopName)
		return False
	t = getBusTime(getTimes(stp), busNumber)
	timelist = ""
	if t:
		for AT in t[0]:
			timelist += AT+", "
		timelist = timelist[:-2]
	if readConf("verbose") != "yes":
		if not(t):
			sendText("No bus coming")
		else:
			sendText(timelist + " min")
		return True
	msg = "stage: "+stopName+"\nnumber: "+busNumber+"\n"
	if not(t):
		msg += "No bus coming"
	else:
		msg += "bus name: " + t[1] + "\ntime: " + timelist + " min"
	sendText(msg)
	return True

#returns string array of headlines
def getNews(keyword):
	try:
		req = requests.get("https://timesofmalta.com/articles/listing/national")
	except:
		return None
	html = BeautifulSoup(req.text, 'html.parser')
	articles = html.find('script', attrs={"id": "listing-ld"})
	if articles is None:
		return None
	articles = json.loads(articles.encode_contents())

	names = []
	for article in articles["@graph"]:
		names.append([str(article["name"]).lower(), article["keywords"].lower()])
	
	names = [name[0] for name in names if keyword.lower() in name[1]]
	return names

#send new headline if theres an update
def checkNews():
	keyword = readConf("newsword")
	if keyword == "none":
		news = getNews("")
	else:
		news = getNews(keyword)
	if news is None or len(news) == 0:
		return
	if news[0] != readConf("lastnews"):
		sendText("Update: " + news[0])
		writeConf("lastnews", news[0])

#takes a string array of headlines
def showNews(strings):
	strings = ["<" + string + ">" for string in strings]
	sendText("\n".join(strings))

def getNext(res):
	return int(res['result'][0]['update_id']) + 1

def alertWhen():
	global clocks
	clock = clocks["alert"]
	stopName = readConf("default")
	busNumber = readConf("bus")
	stp = getStop(stopName)
	t = getBusTime(getTimes(stp), busNumber)
	if not(t):
		return
	if smaller(t[0][0], clock["minutes"]) or t[0][0] == clock["minutes"]:
		clock["enabled"] = False
		return alert(stopName, busNumber)

def readMessage(message):
	global clocks

	if len(message) < 2 or message[0] != '/':
		return
	
	sp = message[1:].split(" ")
	command = sp[0].lower()
	
	loggit = True
	if command == "help" and len(sp) == 1:
		sendText("""
			[parameter] <--- optional, (paremeter) <--- must
			time [busstop name] [busnumber]: shows time for bus to pass from busstop
			news [keyword]: shows news about keyword
			list: shows bus stops
			default: shows name of default busstop
			set (setting) (value): sets a setting to specifiec value
			whatis (busstop name): shows description of busstop
			alert (minutes): sends message when default bus is arriving in less than specified time
			origin (surname): tells you from where that surname originates
			config: shows settings
			ping: pong
		""")
	elif command == "time":
		if len(sp) == 1:
			alert(readConf("default"), readConf("bus"))
		elif len(sp) == 2:
			alert(sp[1].lower(), readConf("bus"))
		elif len(sp) == 3:
			alert(sp[1].lower(), sp[2])
	elif command == "news":
		if len(sp) == 1:
			news = getNews("")
		elif len(sp) == 2:
			news = getNews(sp[1].lower())
		showNews(news)
	elif command == "list" and len(sp) == 1:
		sendText(getNames())
	elif command == "default" and len(sp) == 1:
		sendText("default: "+readConf("default"))
	elif command == "set" and len(sp) >= 3:
		if writeConf(sp[1], sp[2]):
			if sp[1] == "news":
				clocks["news"]["enabled"] = sp[2] == "yes"
			if sp[1] == "newspoll":
				clocks["news"]["poll"] = int(sp[2])
			if sp[1] == "default" and len(sp) == 4:
				writeConf("bus", sp[3])
			sendText("OK")
		else:
			sendText("FAIL")
	elif command == "whatis" and len(sp) == 2:
		rec = getRecord(sp[1])
		if not(rec):
			sendText("no such name: " + sp[1])
		else:
			rec = rec.split('|')
			sendText(rec[0] + ": " + rec[2])
	elif command == "alert" and len(sp) == 2:
		if not(sp[1].isdigit()):
			sendText("invalid argument: "+sp[1])
		else:
			clock = clocks["alert"]
			clock["enabled"] = True
			clock["tick"] = 0
			clock["minutes"] = sp[1]
			sendText("OK")
	elif command == "origin" and len(sp) == 2:
		trace(sp[1])
	elif command == "config" and len(sp) == 1:
		with open(memory) as mem:
			lines = mem.read()
		sendText(lines)
	elif command == "ping":
		sendText("pong")
	elif command == "haha":
		sendText("haha lol")
	else:
		loggit = False
	
	if loggit:
		log("command: \""+message+"\"")

def readLoop():
	while True:
		res = getUpdates(lastId, poll)
		if not(res):
			continue

		message = getMessage(res)
		if not(message):
			continue

		readMessage(message["text"])

#so that lastId is updated
log("getting lastid")
getUpdates()

#an interesting mechanism instead of multithreading
clocks = {
	"news":	{
		"enabled": readConf("news") == "yes",
		"tick": 0,
		"poll": int(readConf("newspoll")),
		"function": checkNews
	},
	"alert": {
		"enabled": False,
		"tick": 0,
		"poll": 20,
		"function": alertWhen,
		"minutes": 5
	}
}

#start the message read thread
rthread = threading.Thread(target = readLoop)
rthread.start()
log("waiting for commands")

while True:
	try:
		for clockname, clock in clocks.items():
			clock["tick"] += 1 if clock["enabled"] else 0
			if clock["tick"] < clock["poll"]:
				continue
			clock["tick"] = 0
			clock["function"]() #execute the clock function when the tick exceeds the poll
		sleep(1)
	except Exception as e:
		log("Error in main thread:\n"+str(e))
