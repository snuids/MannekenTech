import docker
import json
import requests
import time
import os
from datetime import datetime
from elasticsearch import Elasticsearch


DOCKER_STATS="docker_stats*"
ELASTIC_ADDRESS="localhost:9201"

try:
    ELASTIC_ADDRESS=os.environ["ELASTIC_ADDRESS"]
except Exception as e:
    print ('ELASTIC_ADDRESS Environment variable not set.')

print ("ELK URL %s" %(ELASTIC_ADDRESS))

try:
    DOCKER_STATS=os.environ["DOCKER_STATS"]
except Exception as e:
    print ('DOCKER_STATS Environment variable not set.')

print ("DOCKER_STATS %s" %(DOCKER_STATS))

def createIndexTemplate():
    print ("Create index template via a post request.")
    global indice,es,DOCKER_STATS

    body={"order":0,"template":DOCKER_STATS,"settings":{}
    ,"mappings":{"container":
                {"properties":{
                    "name":{"index":"not_analyzed","type":"string"}
                    ,"@timestamp":{"type":"date"}
                }}
                }}

    address="http://"+ELASTIC_ADDRESS+"/_template/dockersupervisor";

    r = requests.post(address, data=json.dumps(body))

    print ("Index template saved.")

if __name__ == '__main__':
    createIndexTemplate()
    client = docker.from_env()
    es = Elasticsearch(hosts=[ELASTIC_ADDRESS])

    while True:
        bulk_body=""
        newcpuhashtable={}
        for container in client.containers.list(all=True):
          print ("%s=>%s" %(container.status,container.id ))
          stats=container.stats(decode=True,stream=False);

          if(('cpu_stats' in stats) and ('cpu_usage' in stats['cpu_stats'])
            and ('total_usage' in stats['cpu_stats']['cpu_usage'])):
              cpuvalue=stats['cpu_stats']['cpu_usage']['total_usage']
              precpuvalue=stats['precpu_stats']['cpu_usage']['total_usage']

              cpuDelta = cpuvalue -  precpuvalue;

              if('system_cpu_usage' in stats['cpu_stats']):
                  systemvalue=stats['cpu_stats']['system_cpu_usage']
                  presystemvalue=stats['precpu_stats']['system_cpu_usage']
                  systemDelta = systemvalue - presystemvalue;

                  if (systemDelta >0):

                      RESULT_CPU_USAGE = float(cpuDelta) / float(systemDelta) * 100.0;

                      stats['cpu_percent']=RESULT_CPU_USAGE;


          bulk_body += '{ "index" : { "_index" : "%s-%s", "_type" : "container"} }\n' %(DOCKER_STATS.replace("*",""),datetime.now().strftime("%Y.%m.%d"))
          stats['@timestamp']=int(time.time())*1000
          stats['status']=container.status
          stats['name']=container.name
          bulk_body += json.dumps(stats)+'\n'

        print ("Bulk ready.")
        es.bulk(body=bulk_body,timeout='1m')
        print ("Bulk gone.")

        time.sleep(float(60))
