#! /usr/bin/env python3

import sqlite3
from datetime import datetime as dt


# TODO existence checks on table creations
# TODO create a shared cursor that can be
#      passed around instead of opening and closing one constantly
class betdb(object):

    def __init__(self):
        self.conn = sqlite3.connect("bet.db")

    def create_fight_table(self):
        curs = self.conn.cursor()
        curs.execute("SELECT name from sqlite_master where "
                     "type='table' and name=:tble",
                     {'tble': "'fights'"})
        if curs.fetchone() is None:
            curs.execute('CREATE TABLE if not exists fights(date text, time '
                         'timestamp, team1 text, team2 text, odds1'
                         ' float, odds2 float, money1 integer, '
                         'money2 integer, winner text)')
        curs.close()

    def new_fight(self, team1, team2, odds1=0, odds2=0, money1=0, money2=0, winner="None"):
        date = dt.today()
        curs = self.conn.cursor()
        curs.execute('insert into fights(date, time, team1, '
                     'team2) values (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                     date, date, team1.strip(), team2.strip(),
                     odds1, odds2, money1, money2, winner)
        curs.close()
        self.create_bettor_table(team1, team2, date)
        return date

    def get_odds(self, team1, team2):
        curs = self.conn.cursor()
        curs.execute('select top 1 * from fights where '
                     "team1=':team1' and team2=':team2' order by"
                     ' date desc', team1, team2)
        ret = curs.fetchone()
        curs.close()
        return ret

    def get_money(self, team1, team2):
        curs = self.conn.cursor()
        curs.execute('select top 1 * from fights where '
                     "team1=':team1' and team2=':team2' order by"
                     ' date desc', team1, team2)
        ret = curs.fetchone()
        curs.close()
        return ret

    def update_odds(self, team1, team2, odds1, odds2, date):
        curs = self.conn.cursor()
        curs.execute("update fights set odds1 = :od1, "
                     "odds2 = :od2 where team1 = ':tm1'"
                     " and team2 = ':tm2' and date:date",
                     {"tm1": team1.strip(), "tm2": team2.strip(),
                      "od1": odds1, "od2": odds2, "date": date})
        curs.close()

    def update_money(self, team1, team2, money1, money2, date):
        curs = self.conn.cursor()
        curs.execute('update fights set money1=:money1, '
                     "money2=:money2 where team1=':team1' "
                     " and team2=':team2' and date=:date",
                     {"team1": team1, "team2": team2,
                      "money1": money1, "money2": money2,
                      "date": date})
        curs.close()

    def update_winner(self, team1, team2, date, winner):
        curs = self.conn.cursor()
        curs.execute('update fights set winner=:win '
                     'where team1=:tm1 and team2=:tm2'
                     ' and date=:dt',
                     {"dt": date, "tm1": team1,
                      "tm2": team2, "win": winner})
        curs.close()

    def update_bet(self, team1, team2, date, team, bettor, bet):
        curs = self.conn.cursor()
        curs.execute('update fight_{}_{}_{}(team, bettor, bet)'
                     " set bet=:bet where team=':team'"
                     " and bettor=':bettor'".format(
                         team1, team2,
                         dt.strftime(date, '%m-%d-%Y-%M:%S')),
                     {'team': team, 'bettor': bettor, 'bet': bet})
        curs.close()

    def get_last_fight(self):
        day = dt.today()
        time = dt.now()
        curs = self.conn.cursor()
        curs.execute("select top 1 * from fights where date < "
                     ":date and time < :time order by date desc",
                     {"date": day, "time": time})
        curs.close()

    def bet_table_empty(self, team1, team2, date):
        ret = False
        if date is not None:
            ret = True
            curs = self.conn.cursor()
            curs.execute('select top 1 * from fight_{}_{}_{}'.format(
                         team1, team2, dt.strftime(date, '%m-%d-%Y-%M:%S')))
            if curs.fetchone() is None:
                ret = False
        return ret

    def create_bettor_table(self, team1, team2, date):
        curs = self.conn.cursor()
        curs.execute('SELECT COUNT(*) from information_schema.tables'
                     ' where table_name=fight_{}_{}_{}'.format(
                         team1, team2, dt.strftime(date, '%m-%d-%Y-%M:%S')))
        if curs.fetchone() is None:
            curs.execute('create table fight_{}_{}_{} '
                         '(team text, bettor text, bet integer)'
                         ''.format(team1, team2,
                                   dt.strftime(date, '%m-%d-%Y-%M:%S')))
        curs.close()

    def insert_bettors(self, team1, team2, date, bets):
        curs = self.conn.cursor()
        for team, bet_table in bets.items():
            insert_bets = []
            for bet in bet_table:
                insert_bets.append(tuple(team, bet['bettor'], bet['bet']))
            curs.executemany('insert into fight_{}_{}_{}(team, bettor, bet)'
                             ' values(?, ?, ?)'.format(
                                 team1, team2,
                                 dt.strftime(date, '%m-%d-%Y-%M:%S')), insert_bets)
        curs.close()
