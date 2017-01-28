import time
import urllib2
import json
import re
import requests

from datetime import datetime


def fetch_villo():
    url = 'http://opendata.bruxelles.be/api/records/1.0/search/?dataset=stations-villo-disponibilites-en-temps-reel&rows=1000&facet=banking&facet=bonus&facet=status&facet=contract_name'

    h = urllib2.urlopen(url)
    res= h.read()
    print res;
    res=res.replace("\u0","")
    data = json.loads(res)

    timepoints=[];
    for station in data["records"]:

        onepoint={}
        onepoint["name"]=station["fields"]["name"]
        onepoint["value"]=station["fields"]["available_bikes"]
        onepoint["timestamp"]=int(time.time()*1000)
        onepoint["tags"]={}
        onepoint["tags"]["banking"]=station["fields"]["banking"]
        onepoint["tags"]["status"]=station["fields"]["status"]

        timepoints.append(onepoint)

    print "Bulk ready."
    print json.dumps(timepoints)
    r = requests.post("http://localhost:8083/api/v1/datapoints", data=json.dumps(timepoints))
    print(r.status_code, r.reason)

    print "Bulk gone."

for i in range(0,100):
    print '*'*80
    fetch_villo();
    time.sleep(30)
    print '*'*80
