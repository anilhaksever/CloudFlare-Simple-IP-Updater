import json
import time
from datetime import datetime
import pprint
import requests
import ipgetter



class Debugger:
    def __init__(self, enabled = True, stdout = False, fileout = None, timestamp = True):
        self.enabled = enabled
        self.stdout = stdout
        self.timestamp = timestamp
        if fileout is not None and fileout is not "" and fileout is not False:
            self.fileout = fileout

    def now(self):
        return str(datetime.now())

    def prefix(self):
        if self.timestamp:
            return self.now()

    def print(self, dataobject, title=None):
        if not self.enabled:
            return

        if title is not None:
            self.print(title)

        if self.fileout is not None:
            with open(self.fileout, "a") as out:
                if title is None:
                    out.write("\n")
                    pprint.pprint(self.prefix(), stream=out, indent=4)
                pprint.pprint(dataobject, stream=out, indent=4)
                out.truncate()
        if self.stdout is not False:
            if title is None:
                print("\n")
                pprint.pprint(self.prefix(), indent=4)
            pprint.pprint(dataobject, indent=4)

with open('config.json') as data_file:
    CONFIG = json.load(data_file)

CONFIG_ZONES = CONFIG["zones"]
CONFIG_X_AUTH_KEY = CONFIG["settings"]["X-Auth-Key"]
CONFIG_X_AUTH_EMAIL = CONFIG["settings"]["X-Auth-Email"]
CONFIG_REPEAT = CONFIG["settings"]["repeatEvery"]

debug = Debugger(enabled=CONFIG["settings"]["debugger"], stdout=CONFIG["settings"]["console_debug"], fileout=CONFIG["settings"]["file_debug"])

CF_AUTH_HEADERS = {"X-Auth-Email": CONFIG_X_AUTH_EMAIL, "X-Auth-Key": CONFIG_X_AUTH_KEY, "Content-Type": "application/json"}

r_zones = requests.get("https://api.cloudflare.com/client/v4/zones?", headers=CF_AUTH_HEADERS)

api_zones_result = r_zones.json()
api_zones = api_zones_result["result"]
#print(api_zones)

while True:
    my_ip = ipgetter.myip()
    for zone in CONFIG_ZONES:
        for api_zone in api_zones:
            if api_zone["name"] == zone["name"]:
                debug.print(zone, title="zone")
                debug.print(api_zone["name"], title="api_zone")

                r_zone_dns_records = requests.get("https://api.cloudflare.com/client/v4/zones/"+api_zone["id"]+"/dns_records?&type=A", headers=CF_AUTH_HEADERS)
                api_dns_result = r_zone_dns_records.json()
                debug.print(api_dns_result, title="\n--dns result--")
                for domain in zone["domains_to_update"]:
                    for api_dns in api_dns_result["result"]:
                        if domain["name"] == api_dns["name"]:
                            if api_dns["content"] == my_ip:
                                debug.print("fetched IP ("+api_dns["content"]+") matches with current one ("+my_ip+") passing...")
                                continue
                            payload = json.dumps({"type":zone["type"], "name": domain["name"], "content": my_ip, "proxied": domain["proxied"]})
                            debug.print(payload, "--update data--")
                            update_r = requests.put("https://api.cloudflare.com/client/v4/zones/"+api_zone["id"]+"/dns_records/"+api_dns["id"], data=payload, headers=CF_AUTH_HEADERS)
                            debug.print(update_r.json(), "--update result--")
                break
    
    print("run is over, now will sleep for :"+str(CONFIG_REPEAT)+" seconds")
    time.sleep(int(CONFIG_REPEAT))
