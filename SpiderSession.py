import requests
from config import global_config
import util


class SpiderSession:
    """
    Session相关操作
    """

    def __init__(self):
        self.user_agent = util.get_random_useragent()
        self.local_cookie = global_config.getRaw('config', 'local_cookies')
        self.local_jec = global_config.getRaw('config', 'local_jec')
        self.local_jeh = global_config.getRaw('config', 'local_jeh')
        self.session = self._init_session()

    def _init_session(self):
        session = requests.session()
        session.headers = self.get_headers()
        return session

    def get_headers(self):
        return {"User-Agent": util.get_random_useragent(),
                "Cookie": self.local_cookie,
                "J-E-C": self.local_jec,
                "J-E-H": self.local_jeh,
                "Accept": "*/*",
                "Content-Type": "application/x-www-form-urlencoded",
                "Connection": "keep-alive"}

    def get_user_agent(self):
        return self.user_agent

    def get_session(self):
        """
        获取当前Session
        :return:
        """
        return self.session

    def get_cookies(self):
        """
        获取当前Cookies
        :return:
        """
        return self.get_session().cookies
