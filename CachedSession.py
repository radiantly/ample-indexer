from requests import Session
from requests.compat import urljoin

# This class was supposed to cache requests, but then I realized that I couldn't
# work with cached requests anyway. Atm, this class is the exact same as the
# actual requests.Session, but supports url prefixing and counts the total
# number of requests sent.
class CachedSession(Session):
    def __init__(self, prefix_url=None, *args, **kwargs):
        super(CachedSession, self).__init__(*args, **kwargs)
        self.prefix_url = prefix_url
        self.request_count = 0

    def request(self, method, url, *args, **kwargs):
        url = urljoin(self.prefix_url, url)
        self.request_count += 1
        return super(CachedSession, self).request(method, url, *args, **kwargs)

    def setCookies(self, cookies):
        for cookie in cookies:
            self.cookies.set(cookie["name"], cookie["value"])
        return self
