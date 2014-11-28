About
=====
This repository contains code for both the Decks bot and the CLI interface.

Bot
=====
The bot was originally designed for load testing purposes, but ended up
becoming incredibly useful as a library for interacting with the website. The
CLI interface relies heavily on the modules included in the `bot.py` file.

The bot has many different options available to it. It can run several bots at
once, run only a single instance, it can create games, register new bot users,
and join existing games. The default behaviour is to join the first available 
open (non password protected) game.

CLI
====


Setup
-----

To setup your env to run the command line bot, you will need to install
the following python modules through pip or easy-install

* requests
* curses

and you need to have ncurses installed on your system.

Play
-----

```
$ python2.7 play.py
Using default protocol and host: https://beta.decksagainstsociety.com
Pass proto and host as args to change this
Usage: ./play.py <protocol> <hostname>
Do you have an account already? (y/n) y
Username: admin
Password: 
```

Then the ncurses interface will start up asking you to select a game to play

you can type `quit` at any time to exit the interface
