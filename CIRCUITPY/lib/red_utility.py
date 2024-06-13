import os
import json
import time
import wifi
import socketpool
import ipaddress
import ssl
import adafruit_requests
import gc
import storage
import rtc
import adafruit_ntp

class Network:
    
    """
    Network()
    Initializes network configurations and manages network interactions.

    Parameters: VOID
    
    Returns: VOID
    """
    def __init__(self):
        self.pool = None
        self.ipv4 = None
        self.requests_session = None
    
    """
    Network.get_ip()
    Retrieves the current IPv4 address of the device.

    Parameters: VOID
    Returns:
    str: The current IPv4 address.
    """
    def get_ip(self):
        return str(self.ipv4)
    
    """
    Network.get_pool()
    Provides access to the socket pool used for network operations.

    Parameters: VOID
    
    Returns:
    SocketPool: The socket pool instance.
    """
    def get_pool(self):
        return self.pool
    
    """
    Network.get_status()
    Checks the connection status of the device.

    Parameters: VOID
    
    Returns:
    bool: True if the device is connected, False otherwise.
    """
    def get_status(self):
        return wifi.radio.connected
    
    """
    Network.sync_time(tz_offset: int)
    Synchronizes the device's time with an NTP server.

    Parameters:
    tz_offset (int): Timezone offset in hours from UTC.

    Returns: VOID
    """
    def sync_time(self, tz_offset=0):
        try:
            ntp = adafruit_ntp.NTP(self.pool, tz_offset=tz_offset)
            rtc.RTC().datetime = ntp.datetime
        except Exception as e:
            print('error sync_time:'+str(e))
    
    """
    Network.set_ip(ip: str, subnet: str, gateway: str)
    Sets static IP configuration for the device.

    Parameters:
    ip (str): IP address to assign to the device.
    subnet (str): Subnet mask.
    gateway (str): Gateway IP address.

    Returns: VOID
    """
    def set_ip(self, ip, subnet = str(wifi.radio.ipv4_subnet), gateway = str(wifi.radio.ipv4_gateway)):
        try:
            wifi.radio.set_ipv4_address(ipv4=ipaddress.IPv4Address(ip), netmask=ipaddress.IPv4Address(subnet), gateway=ipaddress.IPv4Address(gateway))
        except Exception as e:
            print('error:'+str(e))
    
    """
    Network.conn_wifi(ssid: str, password: str)
    Connects the device to a Wi-Fi network.

    Parameters:
    ssid (str): SSID of the Wi-Fi network.
    password (str): Password of the Wi-Fi network.

    Returns: VOID
    """
    def conn_wifi(self, ssid, password):
        try:
            wifi.radio.connect(ssid, password)
            self.pool = socketpool.SocketPool(wifi.radio)
            self.ipv4 = wifi.radio.ipv4_address
            self.requests_session = adafruit_requests.Session(self.pool, ssl.create_default_context())
        except Exception as e:
            print('error:'+str(e))
        
    """
    Network.ifconfig()
    Retrieves network configuration details.

    Parameters: VOID
    Returns:
    dict: Dictionary containing network configuration such as IP, subnet, gateway, etc.
    """
    def ifconfig(self):
        try:
            mac_address = ":".join("{:02x}".format(b) for b in wifi.radio.mac_address)
            config = {
                'ip': str(wifi.radio.ipv4_address),
                'subnet': str(wifi.radio.ipv4_subnet),
                'gateway': str(wifi.radio.ipv4_gateway),
                'hostname': str(wifi.radio.hostname),
                'mac': str(mac_address),
                'dns': str(wifi.radio.ipv4_dns),
                'tx_power': str(wifi.radio.tx_power)
            }
            return config
        except Exception as e:
            print('error:'+str(e))
            return None
    
    """
    Network.ping(hostname: str)
    Sends a ping request to the specified hostname and measures the response time.

    Parameters:
    hostname (str): The hostname or IP address to ping.

    Returns:
    float: The ping response time in milliseconds, or 0 if unreachable.
    """
    def ping(self, hostname):
        try:
            ipv4_addr = self.pool.getaddrinfo(hostname, 80)[0][4][0]
            ip = ipaddress.ip_address(ipv4_addr)
            response_time = wifi.radio.ping(ip)
            if response_time is not None:
                return response_time * 1000
            else:
                return float(0)
        except Exception as e:
            print('error:'+str(e))
            return None
    
    """
    Network.get_request(url: str, response_type: str = 'json')
    Sends an HTTP GET request to the specified URL and retrieves the response.

    Parameters:
    url (str): The URL to which the GET request is sent.
    response_type (str): Specifies the type of the response to return (e.g., 'json', 'text', 'headers', 'content', 'status_code').

    Returns:
    varies: Depending on the response_type, it returns JSON, text, headers dictionary, bytes, or status code.
    """
    def get_request(self, url, response_type='json'):
        # response_type controls return, status_code->int | json->json | text->str | headers->dict | content->bytes
        try:
            response = self.requests_session.get(url)
            if response_type == 'status_code':
                    return response.status_code
            if response.status_code == 200:
                if response_type == 'json':
                    result = response.json()
                elif response_type == 'text':
                    result = response.text
                elif response_type == 'headers':
                    result = response.headers
                elif response_type == 'content':
                    result = response.content
                else:
                    result = response.text
                return result
        except Exception as e:
            print('error:'+str(e))
            return None
        finally:
            response.close()
            del response
            gc.collect()
    
    """
    Network.post_request(url: str, data: dict, headers: dict = None, response_type: str = 'json')
    Sends an HTTP POST request to the specified URL with the given data and retrieves the response.

    Parameters:
    url (str): The URL to which the POST request is sent.
    data (dict): The data to be sent with the POST request.
    headers (dict, optional): Additional headers to be sent with the request.
    response_type (str): Specifies the type of the response to return (e.g., 'json', 'text', 'headers', 'content', 'status_code').

    Returns:
    varies: Depending on the response_type, it returns JSON, text, headers dictionary, bytes, or status code.
    """
    def post_request(self, url, data, headers=None, response_type='json'):
        # response_type controls return, status_code->int | json->json | text->str | headers->dict | content->bytes
        if headers is None:
            headers = {
                'Content-Type': 'application/json', # 'application/x-www-form-urlencoded', 'application/xml', 'text/plain'
                'Accept': 'application/json'
            }
        headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
        
        try:
            response = self.requests_session.post(url, json=data, headers=headers)
            if response_type == 'status_code':
                return response.status_code
            if response.status_code == 200:
                if response_type == 'json':
                    return response.json()
                elif response_type == 'text':
                    return response.text
                elif response_type == 'headers':
                    return response.headers
                elif response_type == 'content':
                    return response.content
                else:
                    return response.text
        except Exception as e:
            print('error:'+str(e))
            return None
        finally:
            response.close()
            gc.collect()
    
    """
    Network.scan_networks(limit: int = 10, min_rssi: int = -70)
    Scans for nearby Wi-Fi networks and returns a list of networks that exceed a minimum RSSI threshold.

    Parameters:
    limit (int): Maximum number of networks to return.
    min_rssi (int): Minimum signal strength (RSSI in dBm) required to include a network in the results.

    Returns:
    list: A list of dictionaries, each representing a Wi-Fi network with details such as SSID, RSSI, authentication mode, and channel.
    """
    def scan_networks(self, limit=10, min_rssi=-70):
        # network.rssi(Signal Strength in dBm >-50 Strong, -60 Good, -70 Fair, -80 Poor
        networks = wifi.radio.start_scanning_networks()
        network_count = 0
        available_networks = []
        for network in networks:
            if network.rssi > min_rssi:
                available_networks.append({
                    'ssid': network.ssid,
                    'rssi': network.rssi, 
                    'authmode': network.authmode,
                    'channel': network.channel
                })
                network_count += 1
            if network_count >= limit:
                break
        wifi.radio.stop_scanning_networks()
        gc.collect()
        return available_networks


class Logger:
    
    """
    Logger(filename: str = 'syslog.txt', print_log: bool = True)
    Initializes the logger system which manages application logs.

    Parameters:
    filename (str): Filename for the log file.
    print_log (bool): Flag to enable logging to console.

    Returns: VOID
    """
    def __init__(self, filename='syslog.txt', print_log=True):
        self.filename = filename
        self.print_log = print_log
        self.readonly = storage.getmount('/').readonly
        # Check if the log file exists, if not, create one
        if not self.readonly:
            try:
                with open(self.filename, 'r') as log_file:
                    pass
            except OSError:
                with open(self.filename, 'w') as log_file:
                    log_file.write("")
    
    """
    Logger.get_readonly()
    Checks if the storage is in read-only mode.

    Parameters: VOID
    Returns:
    bool: True if the storage read-only, False otherwise.
    """
    def get_readonly(self):
        return self.readonly
    
    """
    Logger.clear()
    Clears the log file.

    Parameters: VOID
    Returns:
    bool: True if the operation was successful, False otherwise.
    """
    def clear(self):
        # Remove all content of the log file
        if not self.readonly:
            with open(self.filename, 'w') as log_file:
                log_file.write("")
                return True
        return False
    
    """
    Logger.add(message: str, level: str = 'INFO', group: str = 'SYS')
    Adds a log entry to the log file.

    Parameters:
    message (str): Log message to add.
    level (str): Severity level of the log.
    group (str): Group identifier for the log.

    Returns: VOID
    """
    def add(self, message, level='INFO', group='SYS'):
        # Create a log dict
        current_time = time.localtime()
        formatted_time = "{:04}-{:02}-{:02} {:02}:{:02}:{:02}".format(
            current_time[0], current_time[1], current_time[2],
            current_time[3], current_time[4], current_time[5]
        )
        log_entry = {
            'level': level,
            'group': group,
            'sysdt': formatted_time,
            'message': message
        }
        # Convert dict to json str and append to the bottom of the log file
        if not self.readonly:
            with open(self.filename, 'a') as log_file:
                log_file.write(json.dumps(log_entry) + '\n')
                if self.print_log:
                    print(json.dumps(log_entry))
        else:
            print(json.dumps(log_entry))
            
    """
    Logger.read(limit: int = 5, level: str = None, group: str = None)
    Reads log entries from the log file.

    Parameters:
    limit (int): The maximum number of log entries to return.
    level (str): Filter logs by severity level.
    group (str): Filter logs by group identifier.

    Returns:
    list: A list of log entries, possibly empty.
    """
    def read(self, limit=5, level=None, group=None):
        # Read limit lines from the bottom (recent) of the log file
        try:
            with open(self.filename, 'r') as log_file:
                lines = log_file.readlines()
                # Get the last `limit` lines
                recent_logs = lines[::-1]  # Reverse the list to start from the bottom
                filtered_logs = []
                for line in recent_logs:
                    log_entry = json.loads(line)
                    if (level is None or log_entry['level'] == level) and (group is None or log_entry['group'] == group):
                        filtered_logs.append(log_entry)
                        if len(filtered_logs) >= limit:
                            break
                return filtered_logs
        except Exception as e:
            print('error:', str(e))
            return []
