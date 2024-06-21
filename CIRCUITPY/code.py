import os
import gc
import time
import microcontroller
import red_utility
import red_api_server

### Configs ###
PICOW_WIFI_SSID = os.getenv("PICOW_WIFI_SSID")
PICOW_WIFI_PASSWORD = os.getenv("PICOW_WIFI_PASSWORD")
PICOW_API_KEY = os.getenv("PICOW_API_KEY")
PICOW_API_PORT = os.getenv("PICOW_API_PORT")
PICOW_API_POLL_RATE = float(os.getenv("PICOW_API_POLL_RATE"))

### Board Logics ###

# INIT Logger
logger = red_utility.Logger(filename="syslog.txt", print_log=True)
logger.add(f"System Started, Storage Readonly = {logger.get_readonly()}.")

# INIT WLAN
wlan = red_utility.Network()
wlan.conn_wifi(PICOW_WIFI_SSID, PICOW_WIFI_PASSWORD)
if not wlan.get_status():
    logger.add("Failed to connect to Wi-Fi. Retrying in 3 seconds.","WARN")
    time.sleep(3)
    wlan.conn_wifi(PICOW_WIFI_SSID, PICOW_WIFI_PASSWORD)
    if not wlan.get_status():
        logger.add("Failed to initialize WLAN. Reset in 30 seconds...","ERROR")
        time.sleep(30)
        microcontroller.reset()
wlan.sync_time(-4) # Sync localtime to EDT(GMT-4)/EST(GMT-5)
logger.add(f"IP: {wlan.get_ip()}")

# INIT API SERVER
api_server = red_api_server.ApiServer(pool=wlan.get_pool(), ip=wlan.get_ip(), port=PICOW_API_PORT, api_key=PICOW_API_KEY, logger=logger, verbose_log=True, debug=False)
api_server.start(poll_rate=PICOW_API_POLL_RATE)
logger.add(f"API Server: http://{wlan.get_ip()}:{PICOW_API_PORT}/")
gc.collect()
logger.add("Server MemFree: {} bytes".format(gc.mem_free()))

while True:
    
    try:
        api_server.poll()
        
    except Exception as e:
        logger.add(f"{str(e)}, reset in 10 seconds","ERROR")
        time.sleep(10)
        microcontroller.reset()
    
