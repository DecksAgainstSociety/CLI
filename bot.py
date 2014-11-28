#!/usr/bin/env python2.7

import requests
import json
import re
import time

from random import randint

import logging

logging.basicConfig(level=30)
logger = logging.getLogger(__name__) 
logger.setLevel('ERROR')


def gen_pepper(length):
    chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    pepper = ''
    for i in range(0,length):
        rand = randint(0,len(chars)-1)
        pepper += chars[rand]

    #return 'abcd'
    return pepper

class Bot:
    host = 'beta.decksagainstsociety.com'
    protocol = 'https'
    verify = False
    user_prefix = 'game-bot-'
    user_prefix = 'bot-'
    pepper_length = 4

    session = None
    running = True

    def __init__(self, host = 'beta.decksagainstsociety.com', protocol='https', 
            user_prefix='game-bot-', pepper_length=5, auth_user=None, 
            auth_pass=None, verify=True, username=None):

        self.host = host 
        self.protocol = protocol
        self.user_prefix = user_prefix
        self.pepper_length = pepper_length

        self.base_url = self.get_base_url()

        self.session = requests.Session()
        self.session.verify = verify

        self.auth_user = auth_user
        self.auth_pass = auth_pass
        if self.auth_user:
            if self.auth_pass is None:
                self.auth_pass = raw_input('Basic auth password: ')
            self.session.auth = (self.auth_user, self.auth_pass)

        if username is None:
            self.username = self.user_prefix + gen_pepper(self.pepper_length)
        else:
            self.username = username

        self.password = 'botpassword'

        self.logger = logging.getLogger(self.username) 
        self.logger.addHandler(logging.FileHandler('logs/'+self.username+'.log'))
        self.logger.setLevel(30)

        self.init_connection()

    def get_base_url(self):
        return self.protocol+"://"+self.host+"/"

    def init_connection(self):
        self.logger.info('Connecting to: '+self.base_url)

        r = self._get(self.base_url)
        if r.status_code == 401:
            self.logger.critical('Unauthorized, try a new password')

    def build_url(self, url):
        url = url.replace(self.base_url,'')
        return self.base_url + url

    def _get(self, url):
        url = self.build_url(url)
        r = self.session.get(url)
        self.logger.debug('GET: '+url)
        return r

    def _post(self, url, data):
        url = self.build_url(url)
        try:
            data['csrfmiddlewaretoken'] = self.session.cookies['csrftoken']
        except KeyError:
            pass
        r = self.session.post(url, data=data)
        self.logger.debug('POST: %s data: %s', url, data)
        return r

    def register(self):
        url = 'user/register'
        # Content-Type: application/x-www-form-urlencoded
        # username=asdf&password1=asdf&password2=asdf&email=&agree=on&submit=Register
        data = {
            'username': self.username,
            'password1': self.password,
            'password2': self.password,
            'agree': True
        }
        self.logger.info("Registering user: %s", self.username)
        self._post(url, data)

    def login(self):
        url = 'user/login'
        # Content-Type: application/x-www-form-urlencoded
        # username=asdf&password=asdf
        data = {
            'username':  self.username,
            'password': self.password,
        }
        self.logger.info("Logging in as: "+self.username)
        r = self._post(url, data)
        self.logger.debug("Logged in url: %s", r.url)
        if r.url == self.build_url('accounts/accept_update'):
            self.accept()
            return self.login()
        if 'Invalid login' in r.text:
            raise Exception("Failed to login as "+self.username)
        self.logger.info("Logged in!")

    def accept(self):
        url = 'accounts/accept_update'
        # Content-Type: application/x-www-form-urlencoded
        # username=asdf&password=asdf
        data = {
            'agree':  True,
        }
        self.logger.info('Accepting terms')
        r = self._post(url, data)
        if 'You mut accept the terms' in r.text:
            raise Exception("An error occured accepting the terms")
        self.logger.info("Terms Accepted!")

    def create_game(self):
        url = 'game/newgame'
        data = {
            'name': gen_pepper(10),
            'password1': None,
            'password2': None,
            'play_to': 10,
            'max_players': 10,
            'max_cards': 10,
            'expansions': [1,3,4,5]
        }
        self.logger.info('Creating new game %s' % data['name'])
        r = self._post(url, data)

    def get_games(self):
        response = self._get('game/api/listgames')
        try:
            games = json.loads(response.text)
        except ValueError:
            self.logger.error("Invalid data: " + response.text)
            raise Exception("Invalid data returned from server")

        return games

    def get_hand(self):
        response = self._get('game/api/hand')
        try:
            hand = json.loads(response.text)
        except ValueError:
            self.logger.error("Invalid data: " + response.text)
            raise Exception("Invalid data returned from server")

        return hand 

    def get_score(self, game_id):
        response = self._get('game/api/score/'+str(game_id))
        try:
            data = json.loads(response.text)
        except ValueError:
            self.logger.info("Invalid data: " + response.text)
            raise Exception("Invalid data returned from server")

        return data 

    def get_in_play(self, game_id):
        response = self._get('game/api/inplay/'+str(game_id))
        try:
            data = json.loads(response.text)
        except ValueError:
            self.logger.info("Invalid data: " + response.text)
            raise Exception("Invalid data returned from server")

        return data 

    def get_last_win(self, game_id):
        response = self._get('game/api/lastwin/'+str(game_id))
        try:
            data = json.loads(response.text)
        except ValueError:
            raise Exception("Invalid data returned from server")
        return data 

    def get_black(self, game_id):
        response = self._get('game/api/black/'+str(game_id))
        try:
            data = json.loads(response.text)
        except ValueError:
            raise Exception("Invalid data returned from server")

        return data 

    def re_join_game(self, game_id):
        r = self._get('game/play/'+str(game_id))
        
        match = re.search(r'channel\s*=\s*"(?P<channel>[^"]+)', r.text)
        if match:
            channel = match.group(1)
        else:
            channel = None
        game = Game(self, game_id, channel)
        return game

    def join_game(self, game_id):
        r = self._get('game/joingame/'+str(game_id))
        
        match = re.search(r'channel\s*=\s*"(?P<channel>[^"]+)', r.text)
        if match:
            channel = match.group(1)
        else:
            channel = None
        game = Game(self, game_id, channel)
        return game

    def play_card(self, game_id, card_id):
        return self._card('game/api/playcard', game_id, card_id)

    def pick_card(self, game_id, card_id):
        return self._card('game/api/pickcard', game_id, card_id)

    def _card(self, url, game_id, card_id):
        data = {
            'game': game_id,
            'card': card_id,
        }
        return self._post(url, data)

class Game(object):
    in_play = []
    hand = []
    czar = False
    game_id = 0
    bot = None
    channel = None
    black = None

    def __init__(self, bot, game_id, channel=None):
        self.game_id = game_id
        self.bot = bot

        self.channel = channel

        self.logger = bot.logger
        self.logger.setLevel(20)

        self.update_hand()
        self.update_score()
        self.update_in_play()
        self.running = False
        self.picked = False

    def update_all(self):
        self.update_score()
        self.update_hand()
        self.update_in_play()
        

    def update_score(self):
        self.score = self.bot.get_score(self.game_id) 

    def update_hand(self):
        hand = self.bot.get_hand() 

        self.czar = hand['czar']
        self.hand = hand['hand']

        self.logger.debug('Hand is: '+str(self.hand))

    def update_in_play(self):
        inplay = self.bot.get_in_play(self.game_id) 
        self.in_play = inplay['cards']
        self.logger.debug('Inplay is: %s' % self.in_play)

        self.black = self.bot.get_black(self.game_id) 
        self.logger.debug('Black card is: %s' % self.black)

    def play_random_card(self):
        if len(self.hand) == 0:
            self.update_hand()
        rand = randint(0, max(len(self.hand)-1, 0))
        card = self.hand[rand]
        return self.play_card(card['id'])

    def play_card(self, card_id):
        r = self.bot.play_card(self.game_id, card_id) 
        if r.status_code != 200:
            return False
        return True

    def pick_random_card(self):
        if len(self.in_play) == 0:
            self.update_in_play()
        rand = randint(0, max(len(self.in_play)-1, 0))
        cards = self.in_play[rand]
        return self.pick_card(cards[0]['id'])

    def pick_card(self, card_id):
        r = self.bot.pick_card(self.game_id, card_id) 
        if r.status_code != 200:
            return False
        return True

    def new_round_wait(self):
        black = self.black
        while self.black['id'] == black['id']:
            self.update_in_play()
            time.sleep(2)
        return True

    def all_played_wait(self):
        while not self.all_played():
            self.update_in_play()
            time.sleep(2)
        return True

    def all_played(self):
        try:
            return not isinstance(self.in_play[0][0], bool)
        except Exception:
            return False

    def stop(self):
        self.running = False

    def play_game(self):
        self.running = True
        black_id = self.black['id']
        black_time = time.time()
        while self.running:
            self.logger.info("Starting round")
            try:
                self.update_hand()
                self.update_score()
                self.update_in_play()
            except Exception:
                self.running = False
                continue

            # Hack in new round
            if self.black['id'] != black_id or black_time - time.time() > 6:
                black_time = time.time()
                self.picked = False

            self.logger.info("Data updated")
            if self.czar:
                self.logger.info("I'm the czar")
                if self.all_played():
                    self.logger.info("Picking a random card")
                    self.pick_random_card()
            else:
                self.logger.info("I'm playing cards")
                if not self.picked and not self.all_played():
                    self.logger.info("Now picking cards")
                    for i in range(0, self.black['blanks']):
                        while not self.play_random_card():
                            time.sleep(1)
                    self.picked = True

            time.sleep(2)


####################################################################
####################################################################

def usage(message=None):
    if message:
        print message
    print """
Usage: python2.7 bot.py [options]
options:
    -[p,-protocol]    The connection protocol. 
                        default: https
    -[v,-verify]      Verify the ssl certificate. 
                        default: True
    -[h,-host]        The host to connect to. 
                        default: beta.decksagainstsociety.com
    -[n,-user-prefix] The bot username prefix. 
                        default: game-bot-
    -[l,-pepper-len]  The bot username suffix length. 
                        default: 5
    -[a,-auth-user]   Basic HTTP auth username. 
                        default: bot
    -[g,-game-id]     Game id to join
    --username        The bot username. The bot will not generate a random name
                      if this is specified.
                        default: {user-prefix}{random pepper}
    --count           The number of bots to run at a time.
                        default: 1
    --single          Have the bot(s) run a single game (no options needed)

Example: 
    $ python2.6 --protocol=https --host=beta.decksagainstsociety.com \
    --verify=False --auth-user=bot --count=30 --single
"""
    sys.exit(1)

def parse_args(argv):
    kwargs = {
        'protocol': 'https',
        'verify': True,
        'host': 'beta.decksagainstsociety.com',
        'user_prefix': 'game-bot-',
        'pepper_length': 3,
        'auth_user': None,
        'game_id': None,
        'username': None,
        'count': 1,
        'single': False,
    }
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'pgvhnlag', [
            'protocol=', 'verify=', 'host=', 'user-prefix=', 
            'pepper-len=', 'auth-user=', 'username=', 'count=', 'single',
            'game-id=']) 
    except getopt.GetoptError as err:
        usage(err)
        sys.exit(2)

    for o, a in opts:
        if o == '--help':
            usage()
        if o == 'h' or o == '--host':
            kwargs['host'] = a
        if o == 'p' or o == '--protocol':
            kwargs['protocol'] = a
        if o == 'g' or o == '--game-id':
            kwargs['game_id'] = a
        if o == 'v' or o == '--verify':
            if a == 'True' or a == 't' or a == 'y':
                kwargs['verify'] = True 
            if a == 'False' or a == 'f' or a == 'n':
                kwargs['verify'] = False 
        if o == 'n' or o == '--user-prefix':
            kwargs['user_prefix'] = a 
        if o == 'l' or o == '--pepper-len':
            kwargs['pepper_len'] = a 
        if o == 'a' or o == '--auth-user':
            kwargs['auth_user'] = a 
        if o == 'u' or o == '--username':
            kwargs['username'] = a 
        if o == '--count':
            kwargs['count'] = a 
        if o == '--single':
            kwargs['single'] = True 
    return kwargs

def join_game(bot, game_id=None):
    games = bot.get_games()
    my_game = None
    bot.logger.debug("Games: "+str(games))
    if game_id is not None:
        return bot.join_game(game_id)
        
    for game in games:
        # Find the fist open game that is not full
        if game['in_game']:
            my_game = bot.re_join_game(game['id'])
        else:
            players, max_players = game['players'].split('/')
            if int(players) < int(max_players) and not game['locked']:
                logger.info("Joining game: "+game['name']+\
                    " ("+str(game['id'])+")")
                my_game = bot.join_game(game['id'])
                bot.logger.info('Joined game: %d' % game['id'])
                bot.logger.info('Joined game: %d' % my_game.game_id)

    return my_game

def start_bot(bot, single_game=False, game_id=None):
    try:
        bot.login()
        bot.logger.info('Logged in')
    except Exception:
        try:
            bot.register()
            bot.logger.info('Registered new user')
            bot.login()
            bot.logger.info('Logged in')
        except Exception as e:
            logger.error("Failed to register user: "+str(e))

    while bot.running:
        my_game = join_game(bot, game_id=game_id)
        if my_game is None:
            time.sleep(10)
            continue
            bot.logger.info("No games found, creating new one!")
            rand = randint(0,10)
            bot.logger.info("sleeping for: %d", rand)
            time.sleep(rand)
            my_game = join_game(bot)
            if my_game is None:
                bot.create_game()
                my_game = join_game(bot)

        bot.logger.info("Playing a game!")
        if my_game is not None:
            my_game.play_game()


        if single_game:
            bot.running = False
        time.sleep(4)

def die_in_a_fire(signum, frame):
    signal.signal(signal.SIGINT, die_in_a_fire)
    print "DYING IN A HORRIBLE FIRE!"
    sys.exit(1)

bots = []
threads = []
if __name__ == '__main__':
    import os
    import sys
    import getopt
    import threading
    import signal

    kwargs = parse_args(sys.argv)
    count = kwargs.pop('count',1)
    single = kwargs.pop('single',False)
    game_id = kwargs.pop('game_id', None)
    if kwargs.get('auth_user', None) is not None:
        kwargs['auth_pass'] = raw_input('Basic auth password: ')

    signal.signal(signal.SIGINT, die_in_a_fire)

    # Remove the username if we have more than one bot
    if count > 1:
        kwargs.pop('username')

    for i in range(0, int(count)):
        print "Starting bot number "+str(i)
        bot = Bot(**kwargs)
        bots.append(bot)
        t = threading.Thread(target=start_bot, args=(bot, single, game_id))
        threads.append(t)
        t.daemon = True
        print "Starting thread for bot "+str(i)
        t.start()
        print "bot "+str(i)+" is started"
        time.sleep(1)


    for thread in threads:
        thread.join()
