import board
import digitalio
import analogio
import json
import time
import microcontroller
import gc
import re
import red_utility
from adafruit_httpserver import Server, Request, Response, POST


class ApiServer:
    
    """
    ApiServer(pool: socketpool.SocketPool, ip: str, port: int, api_key: str, logger: red_utility.Logger, debug: bool = True)
    Initializes the API server with the necessary network and hardware configurations.
    
    Parameters:
    pool (socketpool.SocketPool) - The socket pool used for network connections.
    ip (str) - The IPv4 address the server will bind to.
    port (int) - The port number the server will listen on.
    api_key (str) - The API key used for authenticating requests.
    logger (red_utility.Logger) - The logger for recording server activities and errors.
    verbose_log (bool, optional) - Flag to enable or disable verbose log (default is True).
    debug (bool, optional) - Flag to enable or disable debug mode (default is False).
    Returns:
    VOID
    """
    def __init__(self, pool, ip, port, api_key, logger, verbose_log=True, debug=False):
        self.pool = pool
        self.ipv4 = ip
        self.port = port
        self.api_key = api_key
        self.logger = logger
        self.verbose_log = verbose_log
        self.debug = debug
        
        self.poll_rate = 0
        self.last_poll_ts = time.monotonic()
        
        self.api_server = Server(self.pool, "/static", debug=self.debug)
        self.api_server.headers = {
            "X-Server": "RED PICOW API SERVER",
            "Access-Control-Allow-Origin": "*",
        }
        self.init_hardwares()
        self.load_routes()
    
    """
    ApiServer.start()
    Starts the API server, allowing it to accept connections on the configured IP address and port.
    
    Parameters:
    poll_rate (float) - The interval between polls in seconds (default is 0.2 seconds).
    
    Returns:
    VOID
    """
    def start(self, poll_rate=0.2):
        self.poll_rate = poll_rate
        self.api_server.start(self.ipv4, self.port)
    
    """
    ApiServer.poll()
    Polls the server to handle incoming requests. Restarts the server on encountering any errors.
    
    Parameters:
    VOID
    
    Returns:
    VOID
    """
    def poll(self):
        if time.monotonic() - self.last_poll_ts > self.poll_rate:
            try:
                self.api_server.poll()
                self.last_poll_ts = time.monotonic()
            except Exception as e:
                self.logger.add(f"{str(e)}","ERROR")
        
    
    """
    ApiServer.init_hardwares()
    Initializes the GPIO pins and other hardware components connected to the server.
    
    Parameters:
    VOID
    
    Returns:
    VOID
    """
    def init_hardwares(self):
        self.board_led = digitalio.DigitalInOut(board.LED)
        self.board_led.direction = digitalio.Direction.OUTPUT
        
        self.board_gp21 = digitalio.DigitalInOut(board.GP21)
        self.board_gp21.direction = digitalio.Direction.OUTPUT
        
        self.board_gp20 = digitalio.DigitalInOut(board.GP20)
        self.board_gp20.direction = digitalio.Direction.OUTPUT
        
        self.board_gp19 = digitalio.DigitalInOut(board.GP19)
        self.board_gp19.direction = digitalio.Direction.OUTPUT
        
        self.board_gp18 = digitalio.DigitalInOut(board.GP18)
        self.board_gp18.direction = digitalio.Direction.INPUT
        
        self.board_gp17 = digitalio.DigitalInOut(board.GP17)
        self.board_gp17.direction = digitalio.Direction.INPUT
        
        self.board_gp16 = digitalio.DigitalInOut(board.GP16)
        self.board_gp16.direction = digitalio.Direction.INPUT
        
        self.board_gp26_a0 = analogio.AnalogIn(board.GP26_A0)
        self.board_gp27_a1 = analogio.AnalogIn(board.GP27_A1)
        self.board_gp28_a2 = analogio.AnalogIn(board.GP28_A2)
    
    """
    ApiServer.load_routes()
    Sets up the routing for the API server, defining the behavior for each route.

    Parameters:
    VOID

    Returns:
    VOID
    """
    def load_routes(self):
        
        """
        Serves the Web GUI HTML page for the root directory(/).
        
        Parameters:
        request (Request): The incoming request object.

        Returns:
        Response: A response object with the content type set to 'text/html'.
        """
        @self.api_server.route("/")
        def root_route_func(request: Request):  # pylint: disable=unused-argument
            try:
                content = self.load_file("/page/web_gui.html")
                return Response(request, content, content_type='text/html')
            except Exception as e:
                self.logger.add(f"{str(e)}","ERROR")  
            finally:
                gc.collect()
        
        """
        Serves the Documentation HTML page for the doc directory(/doc).
        
        Parameters:
        request (Request): The incoming request object.

        Returns:
        Response: A response object with the content type set to 'text/html'.
        """
        @self.api_server.route("/doc")
        def doc_route_func(request: Request):  # pylint: disable=unused-argument
            try:
                content = self.load_file("/page/documentation.html")
                return Response(request, content, content_type='text/html')
            except Exception as e:
                self.logger.add(f"{str(e)}","ERROR")  
            finally:
                gc.collect()
        
        """
        Processes various commands received via POST requests and provides appropriate responses(/cmd).
        
        Parameters:
        request (Request): The incoming request object containing command details.

        Returns:
        Response: A JSON-formatted response detailing the result of the command execution.
        """
        @self.api_server.route("/cmd", POST)
        def cmd_route_func(request: Request):
            error_code = 1
            error_msg = "Invalid command. Please check the documentation."
            result_data = ""
            
            try:
                raw_request = request.raw_request.decode("utf8")
                if self.debug:
                    print(raw_request)
                
                if not self.auth_cmd(raw_request):
                    self.logger.add("Unauthorized Request","WARN")
                    error_msg = "Authenication Required."
                    return Response(request, self.gen_json_response(result_data,error_code,error_msg), content_type='application/json')
                
                if "$CMD{SET_BOARD_LED=ON}" in raw_request:
                    self.verbose_log and self.logger.add("$CMD{SET_BOARD_LED=ON}")
                    self.board_led.value = True
                    error_code = 0
                    error_msg = ""
                    result_data = "BOARD_LED ON"
                
                if "$CMD{SET_BOARD_LED=OFF}" in raw_request:
                    self.verbose_log and self.logger.add("$CMD{SET_BOARD_LED=OFF}")
                    self.board_led.value = False
                    error_code = 0
                    error_msg = ""
                    result_data = "BOARD_LED OFF"
                
                if "$CMD{SET_BOARD_GP21=HIGH}" in raw_request:
                    self.verbose_log and self.logger.add("$CMD{SET_BOARD_GP21=HIGH}")
                    self.board_gp21.value = True
                    error_code = 0
                    error_msg = ""
                    result_data = "BOARD_GP21 HIGH"
                
                if "$CMD{SET_BOARD_GP21=LOW}" in raw_request:
                    self.verbose_log and self.logger.add("$CMD{SET_BOARD_GP21=LOW}")
                    self.board_gp21.value = False
                    error_code = 0
                    error_msg = ""
                    result_data = "BOARD_GP21 LOW"
                    
                if "$CMD{SET_BOARD_GP20=HIGH}" in raw_request:
                    self.verbose_log and self.logger.add("$CMD{SET_BOARD_GP20=HIGH}")
                    self.board_gp20.value = True
                    error_code = 0
                    error_msg = ""
                    result_data = "BOARD_GP20 HIGH"
                
                if "$CMD{SET_BOARD_GP20=LOW}" in raw_request:
                    self.verbose_log and self.logger.add("$CMD{SET_BOARD_GP20=LOW}")
                    self.board_gp20.value = False
                    error_code = 0
                    error_msg = ""
                    result_data = "BOARD_GP20 LOW"
                    
                if "$CMD{SET_BOARD_GP19=HIGH}" in raw_request:
                    self.verbose_log and self.logger.add("$CMD{SET_BOARD_GP19=HIGH}")
                    self.board_gp19.value = True
                    error_code = 0
                    error_msg = ""
                    result_data = "BOARD_GP19 HIGH"
                
                if "$CMD{SET_BOARD_GP19=LOW}" in raw_request:
                    self.verbose_log and self.logger.add("$CMD{SET_BOARD_GP19=LOW}")
                    self.board_gp19.value = False
                    error_code = 0
                    error_msg = ""
                    result_data = "BOARD_GP19 LOW"
                
                if "$CMD{GET_SYS_INFO}" in raw_request:
                    self.verbose_log and self.logger.add("$CMD{GET_SYS_INFO}")
                    error_code = 0
                    error_msg = ""
                    result_data = self.get_sys_info()
                
                if "$CMD{GET_SYS_LOG}" in raw_request:
                    # $PARAM{LIMIT=15}, $PARAM{LEVEL=ERROR}
                    limit = int(self.get_param(raw_request, "LIMIT")) or 5
                    level = self.get_param(raw_request, 'LEVEL') or None
                    self.verbose_log and self.logger.add("$CMD{GET_SYS_LOG},$PARAM{LIMIT="+str(limit)+"},$PARAM{LEVEL="+str(level)+"}")
                    error_code = 0
                    error_msg = ""
                    result_data = self.logger.read(limit,level)
                    
                if "$CMD{CLEAR_SYS_LOG}" in raw_request:
                    if self.logger.clear():
                        error_code = 0
                        error_msg = ""
                        result_data = "System log cleared."
                    else:
                        error_msg = "Can not access log file."
                    self.logger.add("$CMD{CLEAR_SYS_LOG}")
                        
                if "$CMD{RESET_SYS}" in raw_request:
                    self.logger.add("$CMD{RESET_SYS}")
                    microcontroller.reset()
                
                return Response(request, self.gen_json_response(result_data,error_code,error_msg), content_type='application/json')
            
            except Exception as e:
                self.logger.add(f"Command Error: {str(e)}","ERROR")
                return Response(request, self.gen_json_response(result_data,1,str(e)), content_type='application/json')
            
            finally:
                gc.collect()
    
    """
    ApiServer.auth_cmd(raw_request: str)
    Authenticate the API key contained in the raw_request.
    
    Parameters:
    raw_request (str): A string containing the API key in the format $AUTH{API_KEY=your_api_key}.

    Returns:
    bool: True if the API key is valid, False otherwise.
    """
    def auth_cmd(self, raw_request):
        pattern = r"\$AUTH\{API_KEY=([^}]+)\}"
        match = re.search(pattern, raw_request)
        if match:
            extract_api_key = match.group(1)
            if extract_api_key == self.api_key:
                return True
        return False
    
    """
    ApiServer.get_param(raw_request: str, key_name: str)
    Retrieve a parameter value from a raw_request string based on the key_name.
    
    Parameters:
    raw_request (str): The request string containing parameters in the format $PARAM{key=value}.
    key_name (str): The key whose value is to be retrieved.

    Returns:
    str: The value of the parameter if found, or False if not found.
    """
    def get_param(self, raw_request, key_name):
        pattern = pattern = r'\$PARAM\{' + key_name + r'\s*=\s*([^}]*)\}'
        match = re.search(pattern, raw_request)
        if match:
            return match.group(1).strip()
        return False
    
    """
    ApiServer.load_file(filename: str)
    Load and read the contents of a specified file.

    Parameters:
    filename (str): The path to the file to be read.

    Returns:
    str: The content of the file if successful, or an empty string if an error occurs.
    """
    def load_file(self, filename):
        try:
            with open(filename, 'r') as file:
                content = file.read()
            return content
        except Exception as e:
            print('error:'+str(e))
            return ''
    
    """
    ApiServer.gen_json_response(data: dict, error_code: int = 0, error_msg: str = "")
    Generate a JSON response string with the given data and error details.

    Parameters:
    data (dict): Data to be included in the response.
    error_code (int, optional): Error code to indicate the status (default is 0 for no error).
    error_msg (str, optional): A message describing the error (default is an empty string).

    Returns:
    str: A JSON-formatted string representing the response.
    """
    def gen_json_response(self, data, error_code=0, error_msg=""):
        response = {
            "error_code" : error_code,
            "error_msg" : error_msg,
            "timestamp" : time.time(),
            "data" : data
        }
        return json.dumps(response)
    
    """
    ApiServer.get_sys_info()
    Retrieve system information including CPU temperature, frequency, available memory, and GPIO status.

    Returns:
    dict: A dictionary containing various system information metrics.
    """
    def get_sys_info(self):
        result = {
            "cpu_temp" : microcontroller.cpu.temperature,
            "cpu_freq" : microcontroller.cpu.frequency,
            "ram_free" : gc.mem_free(),
            "server_ip" : self.ipv4,
            "server_port" : self.port,
            "storage_ro" : self.logger.get_readonly(),
            "GPIO" : {
                "board.LED" : self.board_led.value,
                "board.GP21" : self.board_gp21.value,
                "board.GP20" : self.board_gp20.value,
                "board.GP19" : self.board_gp19.value,
                "board.GP18" : self.board_gp18.value,
                "board.GP17" : self.board_gp17.value,
                "board.GP16" : self.board_gp16.value,
                "board.GP26_A0" : self.board_gp26_a0.value,
                "board.GP27_A1" : self.board_gp27_a1.value,
                "board.GP28_A2" : self.board_gp28_a2.value
                
            }
            
        }
        return result
        