import time
import util.web


def rtc_version(room):
    """
    Parse the current tinychat RTC version.

    :param room: This could be a static room name, since we just need the html of any room.
    :type room: str
    :return: The current tinychat rtc version, or None on parse failure.
    :rtype: str | None
    """
    _url = 'https://tinychat.com/room/{0}'.format(room)
    response = util.web.http_get(url=_url)

    if response['content'] is not None:
        pattern = '<link rel="manifest" href="/webrtc/'
        return response['content'].split(pattern)[1].split('/manifest.json">')[0]


def get_connect_token(room):
    """
    Get the connect token and the wss server endpoint.

    :param room: The room to get the details for.
    :type room: str
    :return: The token and the wss endpoint.
    :rtype: dict | None
    """
    _url = 'https://tinychat.com/api/v1.0/room/token/{0}'.format(room)

    response = util.web.http_get(_url, json=True)
    if response['json'] is not None:
        return {
            'token': response['json']['result'],
            'endpoint': response['json']['endpoint']
        }

    return None


def user_info(account):
    """
    Get the user information related to the account name.

    :param account: The tinychat account name.
    :type account: str
    :return: A dictionary containing info about the user account.
    :rtype: dict | None
    """
    url = 'https://tinychat.com/api/v1.0/user/profile?username={0}&'.format(account)
    response = util.web.http_get(url, json=True)

    if response['json'] is not None:
        if response['json']['result'] == 'success':
            return {
                'biography': response['json']['biography'],
                'gender': response['json']['gender'],
                'location': response['json']['location'],
                'role': response['json']['role'],
                'age': response['json']['age']
            }

    return None
