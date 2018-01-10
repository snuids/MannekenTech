import docker
import json
import requests
import time
import os
import threading

from datetime import datetime
from elasticsearch import Elasticsearch

VERSION="0.4.5"
DOCKER_STATS="docker_stats*"            #Index template for container statistics
DOCKER_EVENTS="docker_events*"          #Index template for events
ELASTIC_ADDRESS="localhost:9200"        #Elastic host address
POLLING_SPEED=10                        #Polling speed in seconds for container statistics

try:
    ELASTIC_ADDRESS=os.environ["ELASTIC_ADDRESS"]
except Exception as e:
    print ('ELASTIC_ADDRESS Environment variable not set.')

try:
    DOCKER_STATS=os.environ["DOCKER_STATS"]
except Exception as e:
    print ('DOCKER_STATS Environment variable not set.')

try:
    DOCKER_EVENTS=os.environ["DOCKER_EVENTS"]
except Exception as e:
    print ('DOCKER_EVENTS Environment variable not set.')

try:
    POLLING_SPEED=os.environ["POLLING_SPEED"]
except Exception as e:
    print ('POLLING_SPEED Environment variable not set.')
    
print ("*"*40)
print ("* VERSION:         %s" %(VERSION))
print ("* DOCKER_STATS:    %s" %(DOCKER_STATS))
print ("* DOCKER_EVENTS:   %s" %(DOCKER_EVENTS))
print ("* ELASTIC_ADDRESS: %s" %(ELASTIC_ADDRESS))
print ("* POLLING_SPEED:   %s" %(POLLING_SPEED))
print ("*"*40)

def createIndexTemplate():
    print ("Create index templates via post requests.")
    global indice,es,DOCKER_STATS

    map1=json.loads("""{"container":{"properties":{"@timestamp":{"type":"date"},"blkio_stats":{"properties":{"io_service_bytes_recursive":{"properties":{"major":{"type":"long"},"minor":{"type":"long"},"op":{"type":"keyword"},"value":{"type":"long"}}},"io_serviced_recursive":{"properties":{"major":{"type":"long"},"minor":{"type":"long"},"op":{"type":"keyword"},"value":{"type":"long"}}}}},"cpu_percent":{"type":"float"},"cpu_stats":{"properties":{"cpu_usage":{"properties":{"percpu_usage":{"type":"long"},"total_usage":{"type":"long"},"usage_in_kernelmode":{"type":"long"},"usage_in_usermode":{"type":"long"}}},"online_cpus":{"type":"long"},"system_cpu_usage":{"type":"long"},"throttling_data":{"properties":{"periods":{"type":"long"},"throttled_periods":{"type":"long"},"throttled_time":{"type":"long"}}}}},"id":{"type":"keyword"},"memory_stats":{"properties":{"limit":{"type":"long"},"max_usage":{"type":"long"},"stats":{"properties":{"active_anon":{"type":"long"},"active_file":{"type":"long"},"cache":{"type":"long"},"dirty":{"type":"long"},"hierarchical_memory_limit":{"type":"long"},"hierarchical_memsw_limit":{"type":"long"},"inactive_anon":{"type":"long"},"inactive_file":{"type":"long"},"mapped_file":{"type":"long"},"pgfault":{"type":"long"},"pgmajfault":{"type":"long"},"pgpgin":{"type":"long"},"pgpgout":{"type":"long"},"rss":{"type":"long"},"rss_huge":{"type":"long"},"total_active_anon":{"type":"long"},"total_active_file":{"type":"long"},"total_cache":{"type":"long"},"total_dirty":{"type":"long"},"total_inactive_anon":{"type":"long"},"total_inactive_file":{"type":"long"},"total_mapped_file":{"type":"long"},"total_pgfault":{"type":"long"},"total_pgmajfault":{"type":"long"},"total_pgpgin":{"type":"long"},"total_pgpgout":{"type":"long"},"total_rss":{"type":"long"},"total_rss_huge":{"type":"long"},"total_unevictable":{"type":"long"},"total_writeback":{"type":"long"},"unevictable":{"type":"long"},"writeback":{"type":"long"}}},"usage":{"type":"long"}}},"name":{"type":"keyword"},"networks":{"properties":{"eth0":{"properties":{"rx_bytes":{"type":"long"},"rx_dropped":{"type":"long"},"rx_errors":{"type":"long"},"rx_packets":{"type":"long"},"tx_bytes":{"type":"long"},"tx_dropped":{"type":"long"},"tx_errors":{"type":"long"},"tx_packets":{"type":"long"}}}}},"num_procs":{"type":"long"},"pids_stats":{"properties":{"current":{"type":"long"}}},"precpu_stats":{"properties":{"cpu_usage":{"properties":{"percpu_usage":{"type":"long"},"total_usage":{"type":"long"},"usage_in_kernelmode":{"type":"long"},"usage_in_usermode":{"type":"long"}}},"online_cpus":{"type":"long"},"system_cpu_usage":{"type":"long"},"throttling_data":{"properties":{"periods":{"type":"long"},"throttled_periods":{"type":"long"},"throttled_time":{"type":"long"}}}}},"preread":{"type":"date"},"read":{"type":"date"},"status":{"type":"keyword"},"storage_stats":{"type":"object"}}}}""")

    body={"order":0,"template":DOCKER_STATS,"settings":{}
    ,"mappings":map1}

    address="http://"+ELASTIC_ADDRESS+"/_template/dockersupervisorcontainer";
    print("Posting to:"+address)
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    r = requests.post(address, data=json.dumps(body),headers=headers)
    print(r)

    map2=json.loads("""{"event":{"properties":{"@timestamp":{"type":"date"},"Action":{"type":"keyword"},"Actor":{"properties":{"Attributes":{"properties":{"com":{"properties":{"docker":{"properties":{"compose":{"properties":{"config-hash":{"type":"keyword"},"container-number":{"type":"keyword"},"oneoff":{"type":"keyword"},"project":{"type":"keyword"},"service":{"type":"keyword"},"version":{"type":"keyword"}}}}}}},"container":{"type":"keyword"},"exitCode":{"type":"keyword"},"image":{"type":"keyword"},"name":{"type":"keyword"},"signal":{"type":"keyword"},"type":{"type":"keyword"}}},"ID":{"type":"keyword"}}},"Type":{"type":"keyword"},"from":{"type":"keyword"},"id":{"type":"keyword"},"scope":{"type":"keyword"},"status":{"type":"keyword"},"time":{"type":"long"},"timeNano":{"type":"long"}}}}""")

    body={"order":0,"template":DOCKER_EVENTS,"settings":{}
    ,"mappings":map2}

    address="http://"+ELASTIC_ADDRESS+"/_template/dockersupervisorevent";
    print("Posting to:"+address)
    r = requests.post(address, data=json.dumps(body),headers=headers)
    print(r)
    print ("Index templates saved.")

def worker():
    """thread worker function"""
    global event_bulk_body,lock
    print ('Worker Thread Starting')
    print("*="*20)
    
    while True:
        try:
            for event in client.events():
                lock.acquire()
                try:
                    event1 = event.decode('utf-8')

                    for event2 in event1.split("\n"):
                        if "{" in event2:
                            event_bulk_body += '{ "index" : { "_index" : "%s-%s", "_type" : "event"} }\n' %(DOCKER_EVENTS.replace("*",""),datetime.now().strftime("%Y.%m"))
                            event3=json.loads(event2)
                            event3['@timestamp']=int(time.time())*1000
                            event_bulk_body += json.dumps(event3)+'\n'
                except Exception as e:
                    print("Unable to read events.")
                    print(e)

                lock.release()
        except Exception as e:
            print("Unable to read stats")
            print(e)
    print("Worker Thread finished.")
    
event_bulk_body=""
lock = threading.Lock()

if __name__ == '__main__':
    createIndexTemplate()
    client = docker.from_env()
    es = Elasticsearch(hosts=[ELASTIC_ADDRESS])

    t = threading.Thread(target=worker)    
    t.start()

    while True:
        bulk_body=""
        newcpuhashtable={}

        try:
            for container in client.containers.list(all=True):
                print ("%s=>%s" %(container.status,container.id ))
                stats=container.stats(decode=True,stream=False);

                if(('cpu_stats' in stats) and ('cpu_usage' in stats['cpu_stats'])
                and ('total_usage' in stats['cpu_stats']['cpu_usage'])):
                    cpuvalue=stats['cpu_stats']['cpu_usage']['total_usage']
                    precpuvalue=stats['precpu_stats']['cpu_usage']['total_usage']

                    cpuDelta = cpuvalue -  precpuvalue;

                    if('system_cpu_usage' in stats['cpu_stats']) and ('system_cpu_usage' in stats['precpu_stats']):
                        systemvalue=stats['cpu_stats']['system_cpu_usage']
                        presystemvalue=stats['precpu_stats']['system_cpu_usage']
                        systemDelta = systemvalue - presystemvalue;

                        if (systemDelta >0):

                            RESULT_CPU_USAGE = float(cpuDelta) / float(systemDelta) * 100.0;

                            stats['cpu_percent']=RESULT_CPU_USAGE;

                bulk_body += '{ "index" : { "_index" : "%s-%s", "_type" : "container"} }\n' %(DOCKER_STATS.replace("*",""),datetime.now().strftime("%Y.%m"))
                stats['@timestamp']=int(time.time())*1000
                stats['status']=container.status
                stats['name']=container.name
                bulk_body += json.dumps(stats)+'\n'

        except Exception as e:
            print("Unable to read container values.")
            print(e)


        print ("Bulk ready.")
        lock.acquire()
        bulk_body+=event_bulk_body
        event_bulk_body=""
        lock.release()
        print ("Bulk size: %d bytes" % len(bulk_body))

        if(len(bulk_body)>0 ):        
            try:
                es.bulk(body=bulk_body,timeout='1m')
            except Exception as e2:
                print("Unable to read container values.")
                print(e2)
            
        print ("Bulk gone.")

        time.sleep(float(POLLING_SPEED))
