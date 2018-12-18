import requests
import datetime
import json

from threading import Lock

from midea.security import security

# The Midea cloud client is by far the more obscure part of this library, and without some serious reverse engineering
# this would not have been possible. Thanks Yitsushi for the ruby implementation. This is an adaptation to Python 3

VERSION = '0.1.6'


class cloud:
    SERVER_URL = "https://mapp.appsmb.com/v1/"
    CLIENT_TYPE = 1                 # Android
    FORMAT = 2                      # JSON
    LANGUAGE = 'en_US'
    APP_ID = 1017
    SRC = 17

    def __init__(self, appKey, email, password):
        # Get this from any of the Midea based apps, you can find one on Yitsushi's github page
        self.appKey = appKey
        self.login_account = email   # Your email address for your Midea account
        self.password = password

        # A session dictionary that holds the login information of the current user
        self.session = {}

        # A list of home groups used by the API to seperate "zones"
        self.home_groups = []

        # A list of appliances associated with the account
        self.appliance_list = []

        self._api_lock = Lock()
        self._login_lock = Lock()

        # An obscure log in ID that is seperate to the email address
        self.login_id = self.get_login_id()

        self.security = security(self.appKey)
        self._retries = 0

    def api_request(self, endpoint, args):
        """
        Sends an API request to the Midea cloud service and returns the results
        or raises ValueError if there is an error
        """
        self._api_lock.acquire()
        response = {}
        try:
            # Set up the initial data payload with the global variable set
            data = {
                'appId': self.APP_ID,
                'format': self.FORMAT,
                'clientType': self.CLIENT_TYPE,
                'language': self.LANGUAGE,
                'src': self.SRC,
                'stamp': datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            }
            # Add the method parameters for the endpoint
            data.update(args)

            # Add the sessionId if there is a valid session
            if self.session:
                data['sessionId'] = self.session['sessionId']

            url = self.SERVER_URL + endpoint

            data['sign'] = self.security.sign(url, data)

            # POST the endpoint with the payload
            r = requests.post(url=url, data=data)

            response = json.loads(r.text)
        finally:
            self._api_lock.release()

        # Check for errors, raise if there are any
        if response['errorCode'] != '0':
            self.handle_api_error(int(response['errorCode']), response['msg'])
            # If you don't throw, then retry
            if(__debug__):
                print("Retrying API call: '{}'".format(endpoint))
            self._retries += 1
            if(self._retries < 3):
                return self.api_request(endpoint, args)
            else:
                raise RecursionError()

        self._retries = 0
        return response['result']

    def get_login_id(self):
        # Get the login ID from the email address
        response = self.api_request(
            "user/login/id/get", {'loginAccount': self.login_account})
        self.login_id = response['loginId']
        return self.login_id

    def login(self):
        """
        Performs a user login with the credentials supplied to the constructor
        """
        self.session = None
        self._login_lock.acquire()
        try:
            if self.session:
                return  # Don't try logging in again, someone beat this thread to it

            # Log in and store the session
            self.session = self.api_request("user/login", {
                'loginAccount': self.login_account,
                'password': self.security.encryptPassword(self.login_id, self.password)
            })

            self.security.accessToken = self.session['accessToken']
        finally:
            self._login_lock.release()

    def list(self, home_group_id=-1):
        """
        Lists all appliances associated with the account
        """

        # If a homeGroupId is not specified, use the default one
        if home_group_id == -1:
            li = self.list_homegroups()
            home_group_id = next(
                x for x in li if x['isDefault'] == '1')['id']

        response = self.api_request('appliance/list/get', {
            'homegroupId': home_group_id
        })

        self.appliance_list = response['list']
        if(__debug__):
            print("Device list: {}".format(self.appliance_list))
        return self.appliance_list

    def encode(self, data: bytearray):
        normalized = []
        for b in data:
            if b >= 128:
                b = b - 256
            normalized.append(str(b))

        string = ','.join(normalized)
        return bytearray(string.encode('ascii'))

    def decode(self, data: bytearray):
        data = [int(a) for a in data.decode('ascii').split(',')]
        for i in range(len(data)):
            if data[i] < 0:
                data[i] = data[i] + 256
        return bytearray(data)

    def appliance_transparent_send(self, id, data):
        if not self.session:
            self.login()

        if(__debug__):
            print("Sending to {}: {}".format(id, data.hex()))
        encoded = self.encode(data)
        order = self.security.aes_encrypt(encoded)
        response = self.api_request('appliance/transparent/send', {
            'order': order.hex(),
            'funId': '0000',
            'applianceId': id
        })

        reply = self.decode(self.security.aes_decrypt(
            bytearray.fromhex(response['reply'])))

        if(__debug__):
            print("Recieved from {}: {}".format(id, reply.hex()))
        return reply

    def list_homegroups(self, force_update=False):
        """
        Lists all home groups
        """

        # Get all home groups (I think the API supports multiple zones or something)
        if self.home_groups is None or force_update:
            response = self.api_request('homegroup/list/get', {})
            self.home_groups = response['list']

        return self.home_groups

    def handle_api_error(self, error_code, message: str):

        def session_restart():
            if(__debug__):
                print("Restarting session: '{}' - '{}'".format(error_code, message))
            self.session = None
            self.login()

        def throw():
            self.session = None  # Log out but don't log back in immediately
            raise ValueError(error_code, message)

        def ignore():
            if(__debug__):
                print("Error ignored: '{}' - '{}'".format(error_code, message))

        error_handlers = {
            3176: ignore,          # The asyn reply does not exist.
            3106: session_restart,  # invalidSession.
            3004: session_restart,  # value is illegal.
            9999: session_restart,  # system error.
        }

        handler = error_handlers.get(error_code, throw)
        handler()
