import random

from bs4 import BeautifulSoup


def validate_account_type(account):
    if account.lower() not in ('demo', 'live'):
        raise ValueError(f'invalid account type - {account}')

    return account.lower()


class Trading212Rest:
    base_url = 'https://www.trading212.com'

    date_format = r'%Y-%m-%dT%H:%M:%S.000'

    candle_periods = {
        1: 'ONE_MINUTE', 5: 'FIVE_MINUTES', 10: 'TEN_MINUTES', 15: 'FIFTEEN_MINUTES',
        30: 'THIRTY_MINUTES', 60: 'ONE_HOUR', 240: 'FOUR_HOURS', 1440: 'ONE_DAY',
        10080: 'ONE_WEEK', 0: 'ONE_MONTH'
    }

    def __init__(self, account='demo'):
        self._account_id = None
        self._account_type = validate_account_type(account)
        self._account_trading_type = None
        self._application_name = None
        self._application_version = None

    def get_rest_url(self, api_endpoint: str = '') -> str:
        return '/'.join([f'https://{self._account_type}.trading212.com', api_endpoint.strip('/')])

    def get_rest_headers(self) -> dict:
        return {
            'Host': f'{self._account_type}.trading212.com',
            'Origin': f'https://{self._account_type}.trading212.com',
            'Referer': f'https://{self._account_type}.trading212.com/',
            'X-Trader-Client': f'application={self._application_name}, '
            f'version={self._application_version}, '
            f'accountId={self._account_id}'
        }

    def _account(self, session):
        api_url = self.get_rest_url('/rest/v2/account')
        r = session.get(api_url, headers=self.get_rest_headers())

        r.raise_for_status()
        return r.json()

    def _account_session(self, session):
        cookies = session.cookies.get_dict()

        if cookies.get('TRADING212_SESSION_DEMO', False):
            session_cookie = cookies['TRADING212_SESSION_DEMO']

        elif cookies.get('TRADING212_SESSION_LIVE', False):
            session_cookie = cookies['TRADING212_SESSION_LIVE']

        else:
            raise ValueError('unable to find session cookie')

        form_data = {
            'rememberMeCookie': cookies['LOGIN_TOKEN'],
            'sessionCookie': session_cookie,
            'customerSessionCookie': cookies['CUSTOMER_SESSION'],
            'rand': random.randrange(1400000000, 1500000000)
        }

        headers = {
            'Host': 'www.trading212.com',
            'Origin': 'https://www.trading212.com',
            'Referer': 'https://www.trading212.com/',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
        }

        r = session.post(
            url=self.get_rest_url(),
            data=form_data,
            headers=headers
        )

        r.raise_for_status()
        return r.text

    @classmethod
    def _authenticate(cls, session, username, password):
        api_url = cls.base_url + '/en/authenticate'

        form_data = {
            'login[username]': username, 'login[password]': password,
            'login[rememberMe]': 1, 'login[_token]': cls._get_login_token(session),
            'login[twoFactorAuthCode]': '', 'login[twoFactorBackupCode]': '',
            'login[twoFactorAuthRememberDevice]': ''
        }

        headers = {
            'Host': 'www.trading212.com',
            'Origin': 'https://www.trading212.com',
            'Referer': 'https://www.trading212.com/en/login',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
        }

        r = session.post(
            url=api_url,
            data=form_data,
            headers=headers
        )

        r.raise_for_status()
        return r.json()

    @classmethod
    def _get_login_token(cls, session):
        api_url = cls.base_url + '/en/login'

        r = session.get(url=api_url)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, 'html5lib')

        if e := soup.find('input', attrs={'name': 'login[_token]'}):
            return e['value']

        raise ValueError('unable to find login token')

    def _batch_rest(self, session, **kwargs):
        api_url = self.get_rest_url('/charting/rest/batch')

        r = session.post(
            url=api_url,
            headers=self.get_rest_headers(),
            json=kwargs
        )

        r.raise_for_status()
        return r.json()

    def _batch_v2(self, session, **kwargs):
        api_url = self.get_rest_url('/charting/v2/batch')

        r = session.post(
            api_url,
            headers=self.get_rest_headers(),
            json=kwargs
        )

        r.raise_for_status()
        return r.json()

    def _candles(self, session, instrument, period, **kwargs):
        api_url = self.get_rest_url('/charting/rest/v2/candles')

        if period not in self.candle_periods:
            raise ValueError(f'invalid period - {period}')

        payload = {
            'instCode': instrument,
            'periodType': self.candle_periods[period],
            'limit': kwargs.get('limit', 500),
            'withFakes': kwargs.get('fakes', False)
        }

        r = session.post(
            url=api_url,
            headers=self.get_rest_headers(),
            json=[payload]
        )

        r.raise_for_status()
        return r.json()

    def _init_info(self, session):
        api_url = self.get_rest_url('/rest/v3/init-info')
        r = session.get(url=api_url, headers=self.get_rest_headers())

        r.raise_for_status()
        return r.json()

    def _instrument_settings(self, session, instruments):
        api_url = self.get_rest_url('/rest/v2/account/instruments/settings')

        r = session.post(
            url=api_url,
            headers=self.get_rest_headers(),
            json=instruments
        )

        r.raise_for_status()
        return r.json()

    def _notifications(self, session):
        api_url = self.get_rest_url('/rest/v2/notifications')
        r = session.get(url=api_url, headers=self.get_rest_headers())

        r.raise_for_status()
        return r.json()

    def _price_increments(self, session, instrument_codes):
        api_url = self.get_rest_url('/rest/v2/instruments/price-increments')
        params = {'instrumentCodes': instrument_codes}

        r = session.get(
            url=api_url,
            headers=self.get_rest_headers(),
            params=params
        )

        r.raise_for_status()
        return r.json()

    def _price_alerts(self, session):
        api_url = self.get_rest_url('/rest/v2/price-alerts')
        r = session.get(api_url, headers=self.get_rest_headers())

        r.raise_for_status()
        return r.json()

    def _switch(self, session, account_id):
        api_url = self.get_rest_url('/rest/v2/account/switch')
        payload = {'accountId': account_id}

        r = session.post(
            api_url,
            headers=self.get_rest_headers(),
            json=payload
        )

        self.get_session.cache_clear()

        r.raise_for_status()
        return r.json()