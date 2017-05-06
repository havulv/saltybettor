#! /usr/bin/env python3

import re
import sqlite3
from datetime import datetime as dt


# TODO existence checks on table creations
# TODO create a shared cursor that can be
#      passed around instead of opening and closing one constantly
class betdb(object):

    def __init__(self):
        self.conn = sqlite3.connect("bet.db")

    def __del__(self):
        self.conn.close()

    def _clean(self, string):
        return re.sub('[^0-9a-zA-Z]+', '_', string)

    def create_fight_table(self):
        curs = self.conn.cursor()
        curs.execute("SELECT name from sqlite_master where "
                     "type='table' and name=:tble",
                     {'tble': "'fights'"})
        if curs.fetchone() is None:
            curs.execute('CREATE TABLE if not exists fights(date text, time '
                         'timestamp, team1 text, team2 text, odds1'
                         ' real, odds2 real, money1 integer, '
                         'money2 integer, winner text)')
            self.conn.commit()

    def new_fight(self, team1, team2, odds1=0, odds2=0, money1=0, money2=0, winner="None"):
        date = dt.today()
        curs = self.conn.cursor()
        curs.execute('insert into fights(date, time, team1, '
                     'team2, odds1, odds2, money1, money2, winner) '
                     'values (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                     (date, date, team1.strip(), team2.strip(),
                      odds1, odds2, money1, money2, winner))
        self.conn.commit()
        self._create_bettor_table(team1, team2, date)
        return date

    def get_odds(self, team1, team2):
        curs = self.conn.cursor()
        curs.execute('select odds1, odds2 from fights where '
                     "team1=:tm1 and team2=:tm2 order by"
                     ' date desc', {'tm1': team1, 'tm2': team2})
        ret = curs.fetchone()
        return ret if ret is not None else [None, None]

    def get_money(self, team1, team2):
        curs = self.conn.cursor()
        curs.execute('select money1, money2 from fights where '
                     "team1=:tm1 and team2=:tm2 order by"
                     ' date desc', {'tm1': team1, 'tm2': team2})
        ret = curs.fetchone()
        return ret if ret is not None else [None, None]

    def get_all_fighters(self):
        ''' Returns a set of all recorded fighters '''
        curs = self.conn.cursor()
        curs.execute("select team1, team2 from fights")
        ret = curs.fetchall()
        return set([i for j in ret for i in j]) if ret is not None else ret

    def get_all_winners(self):
        ''' Returns a dictionary of all recorded fighters and their wins'''
        curs = self.conn.cursor()
        curs.execute("select winner from fights")
        ret = curs.fetchall()
        if ret is not None:
            ret = [i for j in curs.fetchall() for i in j]
            ret = {i: ret.count(i) for i in set(ret)}
        return ret

    def get_all_losers(self):
        ''' Returns a dictionary of all recorded fighters and their losses'''
        curs = self.conn.cursor()
        curs.execute("select team1, team2, winner from fights")
        ret = curs.fetchall()
        if ret is not None:
            ret = [i[0] if i[1] == i[2] else i[1] for i in ret]
            ret = {i: ret.count(i) for i in set(ret)}
        return ret

    # The assumption on the return value is that the other dude has odds of 1
    def get_all_odds(self):
        ''' Returns a list of all recorded fights and their odds'''
        curs = self.conn.cursor()
        curs.execute("select team1, team2, odds1, odds2 from fights")
        ret = curs.fetchall()
        if ret is not None:
            ret = [(i[0], i[2], i[1]) if i[3] == 1
                   else (i[1], i[3], i[0]) for i in ret]
        return ret

    # Quicker than the individual methods, which are more specific
    def get_all_fights(self):
        ''' Returns the teams, odds, and winner '''
        curs = self.conn.cursor()
        curs.execute("select team1, team2, odds1, odds2, winner "
                     "from fights")
        ret = curs.fetchall()
        return ret

    def get_all_bet_tables(self):
        ''' Returns every bet table for every fight or None'''
        fights = {}
        curs = self.conn.cursor()
        curs.execute("select date, team1, team2 from fights")
        ret = curs.fetchall()
        if ret is not None:
            for fight in ret:
                bet_fights = {}
                curs.execute("select team, bettor, bet from "
                             "bet_{}_{}_{}".format(
                                 self._clean(ret[1].strip()),
                                 self._clean(ret[2].strip()),
                                 dt.strftime(ret[0], '%m_%d_%Y_%M')))
                bet_ret = curs.fetchall()
                if bet_ret is not None:
                    for team, bettor, bet in bet_ret:
                        if team not in bet_fights.keys():
                            bet_fights[team] = []
                        else:
                            bet_fights[team].append((bettor, bet))
                fights[ret[0]] = bet_fights
        return ret

    def get_last_fight(self):
        day = dt.today()
        time = dt.now()
        curs = self.conn.cursor()
        curs.execute("select date, time, team1, team2, odds1, odds2, "
                     "money1, money2, winner from fights where date <"
                     " :date and time < :time order by date desc",
                     {"date": day, "time": time})
        ret = curs.fetchone()
        return ret if ret is not None else [None for i in range(9)]

    def update_odds(self, team1, team2, odds1, odds2, date):
        curs = self.conn.cursor()
        curs.execute("update fights set odds1 = :od1, "
                     "odds2 = :od2 where team1 = :tm1"
                     " and team2 = :tm2 and date=:date",
                     {"tm1": team1.strip(), "tm2": team2.strip(),
                      "od1": odds1, "od2": odds2, "date": date})
        self.conn.commit()

    def update_money(self, team1, team2, money1, money2, date):
        curs = self.conn.cursor()
        curs.execute('update fights set money1=:money1, '
                     "money2=:money2 where team1=:team1 "
                     " and team2=:team2 and date=:date",
                     {"team1": team1, "team2": team2,
                      "money1": money1, "money2": money2,
                      "date": date})
        self.conn.commit()

    def update_winner(self, team1, team2, date, winner):
        curs = self.conn.cursor()
        curs.execute('update fights set winner=:win '
                     'where team1=:tm1 and team2=:tm2'
                     ' and date=:dt',
                     {"dt": date, "tm1": team1,
                      "tm2": team2, "win": winner})
        self.conn.commit()

    def update_bet(self, team1, team2, date, team, bettor, bet):
        curs = self.conn.cursor()
        curs.execute('update bet_{}_{}_{}(team, bettor, bet)'
                     " set bet=:bet where team=':team'"
                     " and bettor=':bettor'".format(
                         team1, team2,
                         dt.strftime(date, '%m-%d-%Y-%M:%S')),
                     {'team': team, 'bettor': bettor, 'bet': bet})
        self.conn.commit()

    def bet_table_empty(self, team1, team2, date):
        ret = False
        if date is not None:
            ret = True
            curs = self.conn.cursor()
            curs.execute('select team from bet_{}_{}_{}'.format(
                         self._clean(team1), self._clean(team2),
                         dt.strftime(date, '%m_%d_%Y_%M')))
            if curs.fetchone() is None:
                ret = False
        return ret

    def _create_bettor_table(self, team1, team2, date):
        curs = self.conn.cursor()
        curs.execute('SELECT name from sqlite_master'
                     ' where type=\'table\' and name=\'bet_{}_{}_{}\''.format(
                         self._clean(team1.strip()),
                         self._clean(team2.strip()),
                         dt.strftime(date, '%m_%d_%Y_%M')))
        if curs.fetchone() is None:
            curs.execute('create table if not exists bet_{}_{}_{}'
                         '(team text, bettor text, bet integer) '
                         ''.format(self._clean(team1.strip()),
                                   self._clean(team2.strip()),
                                   dt.strftime(date, '%m_%d_%Y_%M')))
            self.conn.commit()

    def insert_bettors(self, team1, team2, date, bets):
        curs = self.conn.cursor()
        for team, bet_table in bets.items():
            insert_bets = []
            for bet in bet_table:
                insert_bets.append(tuple(team, bet['bettor'], bet['bet']))
            curs.executemany('insert into bet_{}_{}_{}(team, bettor, bet)'
                             ' values(?, ?, ?)'.format(
                                 self._clean(team1.strip()),
                                 self._clean(team2.strip()),
                                 dt.strftime(date, '%m_%d_%Y_%M')), insert_bets)
            self.conn.commit()
