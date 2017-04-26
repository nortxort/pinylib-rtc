# -*- coding: utf-8 -*-
# Pinylib RTC module, based on the POC by Notnola (https://github.com/notnola/TcRTC)


import json
import time
import logging
import traceback

import websocket
# import socket
from colorama import init, Fore, Style

import config
import user
import apis.tinychat
from page import acc
from util import file_handler, string_util

__version__ = '1.0.0'

CONFIG = config
init(autoreset=True)
log = logging.getLogger(__name__)

#  Console colors.
COLOR = {
    'white': Fore.WHITE,
    'green': Fore.GREEN,
    'bright_green': Style.BRIGHT + Fore.GREEN,
    'yellow': Fore.YELLOW,
    'bright_yellow': Style.BRIGHT + Fore.YELLOW,
    'cyan': Fore.CYAN,
    'bright_cyan': Style.BRIGHT + Fore.CYAN,
    'red': Fore.RED,
    'bright_red': Style.BRIGHT + Fore.RED,
    'magenta': Fore.MAGENTA,
    'bright_magenta': Style.BRIGHT + Fore.MAGENTA
}


def write_to_log(msg, room_name):
    """ 
    Writes chat events to log.

    :param msg: the message to write to the log.
    :type msg: str
    :param room_name: the room name.
    :type room_name: str
    """
    d = time.strftime('%Y-%m-%d')
    file_name = d + '.log'
    path = config.CONFIG_PATH + room_name + '/logs/'
    file_handler.file_writer(path, file_name, msg.encode(encoding='UTF-8', errors='ignore'))


class TinychatRTCClient(object):
    def __init__(self, room, nickname='', account=None, password=None):
        self.room_name = room
        self.nickname = nickname
        self.account = account
        self.password = password
        self.client_id = 0
        self.is_client_mod = False
        self.is_client_owner = False
        self._init_time = time.time()

        self.is_connected = False
        self.users = user.Users()
        self.active_user = None
        self._ws = None
        self._req = 1

    def console_write(self, color, message):
        """ 
        Writes message to console.

        :param color: the colorama color representation.
        :param message: str the message to write.
        """
        msg_encoded = message.encode('ascii', 'ignore')
        if config.USE_24HOUR:
            ts = time.strftime('%H:%M:%S')
        else:
            ts = time.strftime('%I:%M:%S:%p')
        if config.CONSOLE_COLORS:
            msg = COLOR['white'] + '[' + ts + '] ' + Style.RESET_ALL + color + msg_encoded
        else:
            msg = '[' + ts + '] ' + msg_encoded
        try:
            print(msg)
        except UnicodeEncodeError as ue:
            log.error(ue, exc_info=True)
            if config.DEBUG_MODE:
                traceback.print_exc()

        if config.CHAT_LOGGING:
            write_to_log('[' + ts + '] ' + message, self.room_name)

    def login(self):
        """ 
        Login to tinychat.

        :return: True if logged in, else False.
        :rtype: bool
        """
        account = acc.Account(account=self.account, password=self.password)
        if self.account and self.password:
            if account.is_logged_in():
                return True
            account.login()
        return account.is_logged_in()

    def connect(self):
        """ Initialize a websocket handshake. """
        tc_header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:52.0) Gecko/20100101 Firefox/52.0',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Sec-WebSocket-Protocol': 'tc',
            'Sec-WebSocket-Extensions': 'permessage-deflate'
        }

        # It is rather annoying the way logging works in websocket.
        # Or maybe i have misunderstood how it works. How do we only log to file?
        if config.DEBUG_MODE:
            # could comment out next line to not
            # have debug info from websocket show in console.
            websocket.enableTrace(True)

        self._ws = websocket.create_connection(
            'wss://wss.tinychat.com',
            header=tc_header,
            origin='https://tinychat.com'
        )

        if self._ws.connected:
            log.info('connecting to: %s' % self.room_name)
            if self.send_join_msg():
                self.is_connected = True
                self.__callback()

    def disconnect(self):
        """ 
        Disconnect from the server.
        
        This is a bit troublesome, as it will throw an error in the __callback 
        not really sure why. It might be that i am simply closing the connection 
        in a wrong way. I did try different approaches without success.
        """
        self.is_connected = False
        self._ws.close(status=1001, reason='GoingAway')
        self._ws.shutdown()
        self._req = 1
        self._ws = None
        self.client_id = 0
        self.is_client_mod = False
        self.is_client_owner = False
        self.users.clear()

    def reconnect(self):
        """ 
        Reconnect to the server. 
        
        Again, this is a bit troublesome. It does reconnect, 
        but for some reason, writing does nothing on the reconnected connection.
        """
        if self.is_connected:
            self.disconnect()
        self.connect()

    def __callback(self):
        """ The main loop reading event messages from the server. """
        log.info('starting callback, is_connected: %s' % self.is_connected)
        while self.is_connected:

            try:
                data = self._ws.next()
                log.debug('DATA: %s' % data)
                json_data = json.loads(data)

                event = json_data['tc']

                if event == 'ping':
                    self.on_ping()

                elif event == 'closed':
                    self.on_closed(json_data['error'])

                elif event == 'joined':
                    self.on_joined(json_data['self'])
                    self.on_room_info(json_data['room'])

                elif event == 'userlist':
                    for _user in json_data['users']:
                        self.on_userlist(_user)

                elif event == 'join':
                    self.on_join(json_data)

                elif event == 'nick':
                    self.on_nick(json_data['handle'], json_data['nick'])

                elif event == 'quit':
                    self.on_quit(json_data['handle'])

                elif event == 'ban':
                    self.on_ban(json_data)

                elif event == 'unban':
                    self.on_unban(json_data)

                elif event == 'banlist':
                    self.on_banlist(json_data)

                elif event == 'msg':
                    self.on_msg(json_data['handle'], json_data['text'])

                elif event == 'pvtmsg':
                    self.on_pvtmsg(json_data['handle'], json_data['text'])

                elif event == 'publish':
                    self.on_publish(json_data['handle'])

                elif event == 'unpublish':
                    self.on_unpublish(json_data['handle'])

                elif event == 'sysmsg':
                    self.on_sysmsg(json_data['text'])

                elif event == 'yut_playlist':
                    self.on_yut_playlist(json_data)

                elif event == 'yut_play':
                    self.on_yut_play(json_data)

                elif event == 'yut_pause':
                    self.on_yut_pause(json_data)

                elif event == 'yut_stop':
                    self.on_yut_stop(json_data)

                else:
                    self.console_write(COLOR['bright_red'], 'Unknown command: %s %s' % (event, json_data))

                if config.DEBUG_MODE:
                    self.console_write(COLOR['white'], data)

            except Exception as e:
                log.error('callback error: %s' % e, exc_info=True)
                if config.DEBUG_MODE:
                    self.console_write(COLOR['bright_red'], '%s' % e)

    # Chat Events.
    def on_ping(self):
        """ The server sends this every ~30 seconds, i assume to check if the client is alive. """
        self.send_pong()

    def on_closed(self, code):
        """
        This gets sent when ever the connection gets closed by the server for what ever reason.
        
        :param code: The close code as integer.
        :type code: int
        """
        self.is_connected = False
        if code == 4:
            self.console_write(COLOR['bright_red'], 'You have been banned from the room.')
        elif code == 6:
            self.console_write(COLOR['bright_red'], 'Double account sign in.')
        elif code == 12:
            self.console_write(COLOR['bright_red'], 'You have been kicked from the room.')
        else:
            self.console_write(COLOR['white'], 'Connection was closed, code: %s' % code)

    def on_joined(self, client_info):
        """
        Received when the client have joined the room successfully.
        
        :param client_info: This contains info about the client, such as user role and so on.
        :type client_info: dict
        """
        log.info('client info: %s' % client_info)
        self.client_id = client_info['handle']
        self.is_client_mod = client_info['mod']
        self.is_client_owner = client_info['owner']
        client = self.users.add(client_info)
        client.user_level = 0
        self.console_write(COLOR['bright_green'], 'Client joined the room: %s:%s' % (client.nick, client.id))

        # Not sure if this is the right place for this.
        if self.is_client_mod:
            self.send_banlist_msg()

    def on_room_info(self, room_info):
        """
        Received when the client have joined the room successfully.
        
        :param room_info: This contains information about the room such as about, profile image and so on.
        :type room_info: dict
        """
        if config.DEBUG_MODE:
            self.console_write(COLOR['white'], '## Room Information ##')
            for k in room_info:
                self.console_write(COLOR['white'], '%s: %s' % (k, room_info[k]))

    def on_userlist(self, user_info):
        """
        Received upon joining a room. 
        
        This contains all the users present in the room when joining.
        
        :param user_info: A users information such as role.
        :type user_info: dict
        """
        if user_info['handle'] != self.client_id:
            _user = self.users.add(user_info)
            if _user.is_owner:
                _user.user_level = 1
                self.console_write(COLOR['red'], 'Joins room owner: %s:%s:%s' %
                                   (_user.nick, _user.id, _user.account))
            elif _user.is_mod:
                _user.user_level = 3
                self.console_write(COLOR['bright_red'], 'Joins moderator: %s:%s:%s' %
                                   (_user.nick, _user.id, _user.account))
            elif _user.account:
                self.console_write(COLOR['bright_yellow'], 'Joins: %s:%s:%s' %
                                   (_user.nick, _user.id, _user.account))
            else:
                self.console_write(COLOR['cyan'], 'Joins: %s:%s' % (_user.nick, _user.id))

    def on_join(self, join_info):
        """
        Received when a user joins the room.
        
        :param join_info: This contains user information such as role, account and so on.
        :type join_info: dict
        """
        _user = self.users.add(join_info)
        if _user.account:
            tc_info = apis.tinychat.user_info(_user.account)

            if tc_info is not None:
                _user.tinychat_id = tc_info['tinychat_id']
                _user.last_login = tc_info['last_active']

            if _user.is_owner:
                _user.user_level = 1
                self.console_write(COLOR['red'], 'Room owner: %s:%s:%s' %
                                   (_user.nick, _user.id, _user.account))

            elif _user.is_mod:
                _user.user_level = 3
                self.console_write(COLOR['bright_red'], 'Moderator: %s:%s:%s' %
                                   (_user.nick, _user.id, _user.account))
            else:
                self.console_write(COLOR['bright_yellow'], '%s:%s has account: %s' %
                                   (_user.nick, _user.id, _user.account))
        else:
            self.console_write(COLOR['cyan'], '%s:%s joined the room' % (_user.nick, _user.id))

    def on_nick(self, uid, nick):
        """
        Received when a user changes nick name.
        
        :param uid: The ID (handle) of the user.
        :type uid: int
        :param nick: The new nick name.
        :type nick: str
        """
        _user = self.users.search(uid)
        old_nick = _user.nick
        _user.nick = nick
        self.console_write(COLOR['bright_cyan'], '%s:%s Changed nick to: %s' % (old_nick, uid, nick))

    def on_quit(self, uid):
        """
        Received when a user leaves the room.
        
        :param uid: The ID (handle) of the user leaving.
        :type uid: int
        """
        _user = self.users.delete(uid)
        if _user is not None:
            self.console_write(COLOR['cyan'], '%s:%s Left the room.' % (_user.nick, uid))

    def on_ban(self, ban_info):
        """
        Received when the client bans someone.
        
        :param ban_info: The ban information such as, if the ban was a success or not.
        :type ban_info: dict
        """
        if ban_info['success']:
            banned_user = self.users.add_banned_user(ban_info)
            if banned_user.account:
                self.console_write(COLOR['bright_red'], '%s:%s was banned from the room.' %
                                   (banned_user.nick, banned_user.account))
            else:
                self.console_write(COLOR['bright_red'], '%s was banned from the room.' % banned_user.nick)

    def on_unban(self, unban_info):
        """
        Received when the client un-bans a user.
        
        :param unban_info: The un-ban information such as ID (handle) and if un-banned successfully.
        :type unban_info: dict
        """
        unbanned = self.users.delete_banned_user(unban_info)
        if unbanned is not None:
            self.console_write(COLOR['green'], '%s was unbanned.' % unbanned.nick)

    def on_banlist(self, banlist_info):
        if not banlist_info['success']:
            self.console_write(COLOR['bright_red'], banlist_info['reason'])
        else:
            if len(banlist_info['items']) > 0:
                for i, item in enumerate(banlist_info['items']):
                    self.users.add_banned_user(item[i])
            else:
                self.console_write(COLOR['green'], 'The banlist is empty.')

    def on_msg(self, uid, msg):
        """
        Received when a message is sent to the room.
        
        :param uid: The message sender's ID (handle).
        :type uid: int
        :param msg: The chat message.
        :type msg: str
        """
        ts = time.time()
        if uid != self.client_id:
            self.active_user = self.users.search(uid)
            # since spam could be an issue, only allow
            # one message per second to be passed on to
            # the message handler.
            if ts - self.active_user.msg_time >= 1:
                self.message_handler(msg)
            self.active_user.msg_time = ts

    def message_handler(self, msg):
        """
        A basic handler for chat messages.
        
        :param msg: The chat message.
        :type msg: str
        """
        self.console_write(COLOR['bright_green'], '%s: %s' % (self.active_user.nick, msg))

    def on_pvtmsg(self, uid, msg):
        """
        Received when a user sends the client a private message.
        
        :param uid: The ID (handle) of the private message sender.
        :type uid: int
        :param msg: The private message.
        :type msg: str
        """
        ts = time.time()
        if uid != self.client_id:
            self.active_user = self.users.search(uid)
            # since spam could be an issue, only allow
            # one message per second to be passed on to
            # the private message handler.
            if ts - self.active_user.msg_time >= 1:
                self.private_message_handler(msg)
            self.active_user.msg_time = ts

    def private_message_handler(self, private_msg):
        """
        A basic handler for private messages.
        
        :param private_msg: The private message.
        :type private_msg: str
        """
        self.console_write(COLOR['green'], 'Private message from %s: %s' % (self.active_user.nick, private_msg))

    def on_publish(self, uid):
        """
        Received when a user starts broadcasting.
        
        :param uid: The ID (handle) of the user broadcasting.
        :type uid: int
        """
        _user = self.users.search(uid)
        _user.is_broadcasting = True
        self.console_write(COLOR['yellow'], '%s:%s is broadcasting.' % (_user.nick, uid))

    def on_unpublish(self, uid):
        """
        Received when a user stops broadcasting.
        
        :param uid: The ID (handle) of the user who stops broadcasting.
        :type uid: int
        """
        _user = self.users.search(uid)
        _user.is_broadcasting = False
        self.console_write(COLOR['yellow'], '%s:%s stopped broadcasting.' % (_user.nick, uid))

    def on_sysmsg(self, msg):
        """
        System messages sent from the server to all clients (users).
        
        These messages are notifications about special events, such as ban, kick and possibly others.
        
        :param msg: The special notifications message.
        :type msg: str
        """
        self.console_write(COLOR['white'], msg)
        if 'banned' in msg and self.is_client_mod:
            self.send_banlist_msg()

    def on_yut_playlist(self, playlist_data):  # TODO: Needs more work.
        """
        Received when a request for the playlist has been made.
        
        The playlist is as, one would see if being a moderator
        and using a web browser.
        
        :param playlist_data: The data of the items in the playlist.
        :type playlist_data: dict
        """
        if not playlist_data['success']:
            self.console_write(COLOR['red'], playlist_data['reason'])
        else:
            print (playlist_data)

    def on_yut_play(self, yt_data):
        """
        Received when a youtube gets started or time searched.
        
        This also gets received when the client starts a youtube, the information is 
        however ignored in that case.
        
        :param yt_data: The event information contains info such as the ID (handle) of the user 
        starting/searching the youtube, the youtube ID, youtube time and so on.
        :type yt_data: dict
        """
        if yt_data['handle'] != self.client_id:
            _user = self.users.search(yt_data['handle'])
            if yt_data['item']['offset'] == 0:
                # the video was started from the start.
                self.console_write(COLOR['bright_magenta'], '%s started youtube video (%s)' %
                                   (_user.nick, yt_data['item']['id']))
            elif yt_data['item']['offset'] > 0:
                # the video was searched while still playing.
                self.console_write(COLOR['bright_magenta'], '%s searched the youtube video to: %s' %
                                   (_user.nick, int(round(yt_data['item']['offset']))))

    def on_yut_pause(self, yt_data):
        """
        Received when a youtube gets paused or searched while paused.
        
        This also gets received when the client pauses or searches while paused, the information is 
        however ignored in that case.
        
        :param yt_data: The event information contains info such as the ID (handle) of the user 
        pausing/searching the youtube, the youtube ID, youtube time and so on.
        :type yt_data: dict
        """
        if yt_data['handle'] != self.client_id:
            _user = self.users.search(yt_data['handle'])
            self.console_write(COLOR['bright_magenta'], '%s paused the video at %s' %
                               (_user.nick, int(round(yt_data['item']['offset']))))

    def on_yut_stop(self, yt_data):
        """
        Received when a youtube stops, e.g when its done playing.
        
        :param yt_data: The event information contains the ID of the video, the time and so on.
        :type yt_data: dict
        """
        self.console_write(COLOR['bright_magenta'], 'The youtube (%s) was stopped.' % yt_data['item']['id'])

    # Message Construction.
    def send_join_msg(self):
        """
        The initial connect message to the room.
        
        The client sends this after the websocket handshake has been established.
        
        :return: Returns True if the connect message has been sent, else False.
        :rtype: bool
        """
        if not self.nickname:
            self.nickname = string_util.create_random_string(3, 20)

        rtc_version = apis.tinychat.rtc_version(self.room_name)
        log.info('tinychat rtc version: %s' % rtc_version)
        if rtc_version is None:
            rtc_version = config.FALLBACK_RTC_VERSION
            log.info('failed to parse rtc version, using fallback: %s' % config.FALLBACK_RTC_VERSION)

        token = apis.tinychat.get_connect_token(self.room_name)
        if token is not None:
            # opera/chrome user-agent: tinychat-client-webrtc-chrome_win32-2.0.9-255
            payload = {
                'tc': 'join',
                'req': self._req,
                'useragent': 'tinychat-client-webrtc-undefined_win32-' + rtc_version,
                'token': token,
                'room': self.room_name,
                'nick': self.nickname
            }
            self.send(payload)
            return True
        else:
            self.console_write(COLOR['bright_red'], 'Token request failed, token=%s' % token)
            return False

    def send_pong(self):
        """ Send a response to a ping. """
        payload = {
            'tc': 'pong',
            'req': self._req
        }
        self.send(payload)

    def set_nick(self):
        """ Send a nick message. """
        payload = {
            'tc': 'nick',
            'req': self._req,
            'nick': self.nickname
        }
        self.send(payload)

    def send_chat_msg(self, msg):
        """ Send a chat message. """
        payload = {
            'tc': 'msg',
            'req': self._req,
            'text': msg
        }
        self.send(payload)

    def send_private_msg(self, uid, msg):
        """ Send a private message. """
        payload = {
            'tc': 'pvtmsg',
            'req': self._req,
            'text': msg,
            'handle': uid
        }
        self.send(payload)

    def send_kick_msg(self, uid):
        """ Send a kick message. """
        payload = {
            'tc': 'kick',
            'req': self._req,
            'handle': uid
        }
        self.send(payload)

    def send_ban_msg(self, uid):
        """ Send a ban message. """
        payload = {
            'tc': 'ban',
            'req': self._req,
            'handle': uid
        }
        self.send(payload)

    def send_unban_msg(self, ban_id):
        """ Send a un-ban message. """
        payload = {
            'tc': 'unban',
            'req': self._req,
            'id': ban_id
        }
        self.send(payload)

    def send_banlist_msg(self):
        """ Send a banlist request message. """
        payload = {
            'tc': 'banlist',
            'req': self._req
        }
        self.send(payload)

    # Media.
    def send_yut_playlist(self):
        """ Send a youtube playlist request. """
        payload = {
            'tc': 'yut_playlist',
            'req': self._req
        }
        self.send(payload)

    def send_yut_playlist_add(self, video_id, duration, title, image):
        """
        Add a youtube to the web browser playlist.
        
        I haven't explored this yet.
        
        :param video_id: the ID of the youtube video.
        :type video_id: str
        :param duration: The duration of the youtube video (in seconds).
        :type duration: int
        :param title: The title of the youtube video.
        :type title: str
        :param image: The thumbnail image url of the video.
        :type image: str
        """
        payload = {
            'tc': 'yut_playlist_add',
            'req': self._req,
            'item': {
                'id': video_id,
                'duration': duration,
                'title': title,
                'image': image
            }
        }
        self.send(payload)

    def send_yut_playlist_remove(self, video_id, duration, title, image):
        """
        Remove a playlist item from the web browser based playlist.
        
        I haven't explored this yet.
        
        :param video_id: The ID of the youtube video to remove.
        :type video_id: str
        :param duration: The duration of the youtube video to remove.
        :type duration: int | float
        :param title: The title of the youtube video to remove.
        :type title: str
        :param image: The thumbnail image url of the youtube video to remove.
        :type image: str
        """
        payload = {
            'tc': 'yut_playlist_remove',
            'req': self._req,
            'item': {
                'id': video_id,
                'duration': duration,
                'title': title,
                'image': image
            }
        }
        self.send(payload)

    def send_yut_playlist_mode(self, random_=False, repeat=False):
        """
        Set the mode of the web browser based playlist.
        
        I haven't explored this yet.
        
        :param random_: Setting this to True will make videos play at random i assume.
        :type random_: bool
        :param repeat: Setting this to True will make the playlist repeat itself i assume.
        :type repeat: bool
        """
        payload = {
            'tc': 'yut_playlist_mode',
            'req': self._req,
            'mode': {
                'random': random_,
                'repeat': repeat
            }
        }
        self.send(payload)

    def send_yut_play(self, video_id, duration, offset=0):
        """
        Start or search a youtube video.
        
        :param video_id: The ID of the youtube video to start or search.
        :type video_id: str
        :param duration: The duration of the video in seconds.
        :type duration: int | float
        :param offset: The offset seconds to start the video at in the case of doing a search.
        :type offset: int | float
        """
        payload = {
            'tc': 'yut_play',
            'req': self._req,
            'item': {
                'id': video_id,
                'duration': duration,
                'offset': offset
            }
        }
        self.send(payload)

    def send_yut_pause(self, video_id, duration, offset=0):
        """
        Pause, or search while a youtube video is paused .
        
        :param video_id: The ID of the youtube video to pause or search.
        :type video_id: str
        :param duration: The duration of the video in seconds.
        :type duration: int |float
        :param offset: The offset seconds to pause the video at in case of doing seach while in pause.
        :type offset: int |float
        """
        payload = {
            'tc': 'yut_pause',
            'req': self._req,
            'item': {
                'id': video_id,
                'duration': duration,
                'offset': offset
            }
        }
        self.send(payload)

    def send_yut_stop(self, video_id, duration, offset=0):
        """
        Stop a youtube video that is currently playing.
        
        As far as i see, this is not yet officially supported by tinychat.
        There simply is no button to stop a youtube with in the browser based client. (as of version 2.0.10-296)
        
        :param video_id: The ID of the youtube to stop.
        :type video_id: str
        :param duration: The duration of the youtube video in seconds.
        :type duration: int | float
        :param offset: The offset seconds when the youtube gets stopped.
        :type offset: int |float
        """
        payload = {
            'tc': 'yut_stop',
            'req': self._req,
            'item': {
                'id': video_id,
                'duration': duration,
                'offset': offset
            }
        }
        self.send(payload)

    # Broadcasting.
    def ice(self):
        # This is related to broadcasting, after this is sent, the server SHOULD respond
        # with tc: "iceservers" containing 3 stun servers. Next a tc: "sdp" is sent with a type: "offer" ,
        # the sdp payload is rather large containing a lot of info.
        # Not really sure how to get this to work at this point.
        payload = {
            'tc': 'getice',
            'req': self._req
        }
        self.send(payload)

    # Message Sender Wrap.
    def send(self, payload):
        """
        Message sender wrapper used by all methods that sends.
        
        :param payload: The object to send. This should be an object that can be serialized to json.
        :type payload: dict | object
        """
        _payload = json.dumps(payload)
        self._ws.send(_payload)
        self._req += 1
        log.debug('%s' % _payload)

    # Helper Methods.
    def get_runtime(self, as_milli=False):
        """ 
        Get the time the connection has been alive.

        :param as_milli: True return the time as milliseconds, False return seconds.
        :type as_milli: bool
        :return: Seconds or milliseconds.
        :rtype: int
        """
        up = int(time.time() - self._init_time)
        if as_milli:
            return up * 1000
        return up
