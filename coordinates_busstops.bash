#!/bin/bash

function send_request(){
	curl -s -A xarabank -X POST -H "x-api-version: 1.4.5" -H "Content-Type: application/json; charset=UTF-8" --data "$1" "https://www.publictransport.com.mt/appws/$2"
}

function parse_time(){
	jq -M -c ". | .Stops[] | {Id: .I,Name: .N,loc: .LOC,lat: .LA,lon: .LO,buses: [.L[] | {id: .I,num: .N,time: .AT,name: .D}]}" <<< "$1"
}

function parse_stops(){
	jq -M -c ". | {BusStop: .Stops[$2]}" <<< "$1"
}

if [ $# -eq 1 ];then
	send_request "{\"RouteShortName\":\"$1\"}" "StopsMap/GetRouteInformation"
	exit 1
fi

stops="$(send_request "{\"CurrentLat\":$1,\"CurrentLon\":$2}" "StopsMap/GetNearbyBusStops")"

length=$(jq '.Stops | length' <<< $stops)
for (( x = 0; x < $length; x++ ))
do
	parse_stops "$stops" "$x"
	if [ $x == $(($length-1)) ];then
		break
	fi
	echo "---"
done
