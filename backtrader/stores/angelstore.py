from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import backtrader as bt
from smartapi import SmartConnect
import json
import getpass

class AngelStore(bt.Store):
    """
    Singleton class to manage the SmartAPI session.
    """
    _singleton = None
    _broker = None

    def __new__(cls, *args, **kwargs):
        if not cls._singleton:
            cls._singleton = super(AngelStore, cls).__new__(cls, *args, **kwargs)
        return cls._singleton

    def __init__(self, *args, **kwargs):
        super(AngelStore, self).__init__(*args, **kwargs)
        self.smartapi = None
        self._load_config()
        self.login()

    def _load_config(self):
        """
        Loads the API key from config.json.
        """
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                self.api_key = config.get('api_key')
        except FileNotFoundError:
            raise Exception("config.json not found. Please create it with your api_key.")

    def login(self, *args, **kwargs):
        """
        Logs in to the SmartAPI and creates a session.
        """
        if self.smartapi and self.smartapi.access_token:
            return

        client_id = input("Enter Angel Broking Client ID: ")
        password = getpass.getpass("Enter Angel Broking Password: ")
        totp = input("Enter Angel Broking TOTP: ")

        self.smartapi = SmartConnect(self.api_key)

        data = self.smartapi.generateSession(client_id, password, totp)

        if data['status'] and data['data']['jwtToken']:
            print("Login successful.")
            self.feed_token = self.smartapi.getfeedToken()
        else:
            raise Exception(f"Login failed: {data['message']}")

    def get_feed_token(self):
        """
        Returns the feed token for the websocket.
        """
        return self.feed_token

    def logout(self):
        """
        Logs out of the SmartAPI.
        """
        if self.smartapi and self.smartapi.access_token:
            try:
                self.smartapi.terminateSession()
                print("Logout successful.")
            except Exception as e:
                print(f"Logout failed: {e}")

    def get_session(self):
        """
        Returns the SmartAPI session object.
        """
        return self.smartapi

    def getbroker(self):
        return self._broker

    def setbroker(self, broker):
        self._broker = broker

    def getdata(self, *args, **kwargs):
        # This method is required by Backtrader, but we will handle data fetching
        # in the AngelData feed.
        return None
