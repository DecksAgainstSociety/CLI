#!/usr/bin/env python2.7
"""
Requirements:
    threading
    curses
    getpass    
    requests
"""

from bot import Bot, Game

import re
import sys
import threading
import curses
import getpass


def prompt(q, pattern):
    while True:
        inp = raw_input(q)
        if re.match(pattern, inp):
            return inp

class UI(threading.Thread):
    hostname = None
    protocol = None
    session = None
    game = None
    buf = []

    def __init__(self, hostname, protocol):
        super(UI, self).__init__()
        self.hostname = hostname
        self.protocol = protocol
        self.session = self.setup(protocol, hostname)

    def refresh(self):
        self.input_screen.refresh()
        #self.hand_screen.refresh()
        self.activity_screen.refresh()

    def curses_prompt(self, question, pattern):
        self.add_activity_str(question)
        while True:
            inp = self.input_screen.getstr()
            if inp == "quit":
                curses.endwin()
                sys.exit(0)
            if re.match(pattern, inp):
                self.reset_input()
                return inp
            self.reset_input()
            self.add_activity_str("Invalid input: %s" % inp)

    def add_activity_str(self, string):
        self.buf.append(string)
        h, w = self.activity_screen.getmaxyx()
        h -= 2
        print h
        data = self.buf
        if len(data) >= h:
            data = self.buf[-1*h:]

        row = 1
        self.reset_activity()
        for line in data:
            self.activity_screen.addstr(row ,1, line)
            row += 1
        self.refresh()

    def pick_game(self):
        self.add_activity_str("Pick a game to join")
        games = self.session.get_games()
        count = 1
        for game in games:
            self.add_activity_str(" %d) %s %s %s" % (count, game['name'],
                game['players'], ['','(locked)'][game['locked']]))
            count += 1

        selection = self.curses_prompt('Which game do you want to play? ', r'[0-9]+')

        game_entry = games[int(selection)-1]
        self.add_activity_str("Joining game: %s" % game_entry['name'])

        self.game = self.session.join_game(game_entry['id'])

    def print_scoreboard(self):
        self.add_activity_str("==================================")
        self.add_activity_str("Current score:")

        self.add_activity_str("\tUser\tPoints")
        self.add_activity_str("\t----------------")
        for user in self.game.score:
            self.add_activity_str("\t%s\t%d\t%s" % (user['user']['username'], 
                user['points'], ['', '(CZAR)'][user['czar']]))
        
    def print_black(self):
        self.add_activity_str("----------------------------------")
        self.add_activity_str("Black card:")
        self.add_activity_str(self.game.black['content'])

    def update_hand(self):
        index = 1
        lines = []
        longest = 0
        for card in self.game.hand:
            if len(card['content']) > longest:
                longest = len(card['content'])

        overhead = 4
        cols = self.width/(longest+overhead)
        cols = 1

        row = 1
        self.add_activity_str("----------------------------------")
        self.add_activity_str("Your hand:")
        for i in range(0, len(self.game.hand)/cols):
            line = ""
            for j in range(0, max(cols,1)):
                if j != 0:
                    line += " "*(((self.width/cols)*j) - len(line))
                offset = j*len(self.game.hand)/cols
                try:
                    line += "%d) %s" % (i+offset, self.game.hand[i+offset]['content'])
                except:
                    pass
            self.add_activity_str(line)
            row += 1

        self.refresh()

    def print_in_play(self):
        index = 1
        lines = []
        longest = 0
        # inplay [ [{content: ..., id: 0}, {}], [{},{}] ... ]
        for pair in self.game.in_play:
            for card in pair:
                if len(card['content']) > longest:
                    longest = len(card['content'])

        blanks = len(self.game.in_play[0])
        overhead = 4
        cols = self.width/(longest+overhead)
        cols = 1

        self.add_activity_str("----------------------------------")
        self.add_activity_str("In Play:")
        for i in range(0, max(len(self.game.in_play)/cols, 1)):
            for pair in range(0, max(blanks, 1)):
                line = ""
                for j in range(0, max(cols,1)):
                    if j != 0:
                        line += " "*(((self.width/cols)*j) - len(line))
                    offset = j*len(self.game.hand)/cols
                    try:
                        line += "%d) %s" % (i+offset, 
                            self.game.in_play[i+offset][pair]['content'])
                    except:
                        pass
                self.add_activity_str(line)

        self.add_activity_str("----------------------------------")
        self.refresh()

    def play_game(self):
        try:
            while True:
                self.game.update_all()
                self.print_scoreboard()
                self.print_black()

                if not self.game.czar:
                    self.update_hand()
                    count = 0
                    while count < self.game.black['blanks']:
                        self.game.update_in_play()
                        if self.game.all_played():
                            break
                        selection = self.curses_prompt('What card do you want to play? ', r'[0-9]+')
                        num = int(selection)
                        card = self.game.hand[num]
                        if self.game.play_card(card['id']):
                            self.add_activity_str("Played card: %s" % card['content'])
                            count += 1
                        else:
                            self.add_activity_str("Failed to play card")

                self.add_activity_str("Waiting for cards to be played")
                self.game.update_all()
                self.game.all_played_wait()
                self.print_black()
                self.print_in_play()

                if self.game.czar:
                    self.add_activity_str("You are the czar, pick a winning card")
                    selection = self.curses_prompt('What card do you want to pick? ', r'[0-9]+')
                    num = int(selection)
                    cards = self.game.in_play[num]
                    if self.game.pick_card(cards[0]['id']):
                        self.add_activity_str("Picked winnning card: %s" % cards[0]['content'])
                    else:
                        self.add_activity_str("Failed to pick card")
                else:
                    self.add_activity_str("Waiting for the czar to pick")
                    self.game.update_all()
                    self.game.new_round_wait()

                win = self.session.get_last_win(self.game.game_id)
                self.add_activity_str("%s won the last round!" % win['winner']['username'])
                self.add_activity_str("\tBlack: %s" % win['black']['content'])
                self.add_activity_str("\t%s" % win['white1']['content'])
                if win['white2'] != None:
                    self.add_activity_str("%s" % win['white2']['content'])
                if win['white3'] != None:
                    self.add_activity_str("%s" % win['white3']['content'])
        except:
            self.add_activity_str("++++++++++++++++++++++++++++++++++++")
            self.add_activity_str("Game was ended")
            self.print_scoreboard()
        self.game = None


    def start_ui(self, stdscr):
        temp = curses.initscr()
        self.height, self.width = temp.getmaxyx()
        curses.endwin()

        self.input_screen = curses.newwin(3, self.width, self.height-3, 0)

        #self.hand_screen = curses.newwin(7, self.width, self.height-3-7, 0)
        #self.hand_screen.border(0)

        self.activity_screen = curses.newwin(self.height - 3 , self.width)
        self.activity_screen.border(0)
        self.activity_screen.addstr(1,1, "Activity: ")
        self.activity_row = 2

        self.reset_input()

    def run(self):
        self.refresh()
        while True:
            if self.game == None:
                self.pick_game()
                self.play_game()

            self.reset_input()

    def reset_activity(self):
        self.activity_screen.clear()
        self.activity_screen.border(0)

    def reset_input(self):
        self.input_screen.clear()
        self.input_screen.border(0)
        self.input_screen.addstr(1,1, "Input> ")
        self.refresh()

    def setup(self, protocol, hostname):
        login_or_register = prompt('Do you have an account already? (y/n) ', r'[yYnN]$')
        register = re.match(r'[nN]', login_or_register)
        session = Bot(**{
           'host':hostname,
           'protocol': protocol,
           'verify': False
        })

        logged_in = False 
        while not logged_in:
            username = raw_input('Username: ')
            password = getpass.getpass('Password: ')
            session.username = username
            if register:
                while True:
                    pass2 = getpass.getpass('Password (again): ')
                    if pass2 == password:
                        break
                    print("Passwords do not match, try again: ")
                    password = raw_input('Password: ')

            session.password=password
            if register:
                session.register()

            try:
                session.login()
                logged_in = True
            except:
                print("Failed to login, try again")

        return session

    

if __name__ == '__main__':
    hostname = 'beta.decksagainstsociety.com'
    protocol = 'https'

    if len(sys.argv) < 3:
        print "Using default protocol and host: %s://%s" % (protocol,hostname)
        print "Pass proto and host as args to change this"
        print "Usage: %s <protocol> <hostname>" % sys.argv[0]
    if len(sys.argv) == 3:
        protocol = sys.argv[1]
        hostname = sys.argv[2]
        print "New hostname"

    ui = UI(hostname, protocol)
    curses.wrapper(ui.start_ui)
    ui.start()
    
