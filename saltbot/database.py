#! /usr/bin/env python3

from datetime import datetime as dt
import psycopg2
import time
import re


digit_map = {
    0: 'zero',
    1: 'one',
    2: 'two',
    3: 'three',
    4: 'four',
    5: 'five',
    6: 'six',
    7: 'seven',
    8: 'eight',
    9: 'nine',
}


# TODO existence checks on table creations
# TODO create a shared cursor that can be
#      passed around instead of opening and closing one constantly
class Access(object):

    def __init__(self, dbname):
        self.dbase = psycopg2
        self.dbname = dbname
        try:
            self.conn = self.dbase.connect(dbname=self.dbname, user="saltbot",
                                           host="localhost")
        except psycopg2.OperationalError as e:
            if "does not exist" in ''.join(e.args):
                first_conn = self.dbase.connect(dbname="postgres", user="saltbot",
                                                host="localhost")
                first_conn.set_session(autocommit=True)
                cur = first_conn.cursor()
                cur.execute('CREATE DATABASE ' + self.dbname)
                cur.close()
                first_conn.close()
                self.conn = self.dbase.connect(dbname=self.dbname, user="saltbot",
                                               host="localhost")
            else:
                raise e

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()


class Betdb(object):

    def __init__(self, dbname=None):
        if dbname is not None:
            self.dbname = 'testing'
        else:
            self.dbname = 'saltydb'

    def clean_string(func):
        def _clean(self, *args, **kwargs):
            cargs = []
            for arg in args:
                if isinstance(arg, str):
                    cargs.append(re.sub('[^0-9a-zA-Z]+', '_', arg))
                else:
                    cargs.append(arg)

            ckwargs = {}
            for k, v in kwargs.items():
                if isinstance(v, str):
                    ckwargs[k] = re.sub('[^0-9a-zA-Z]+', '_', v)
                    if re.match('^[0-9]', ckwargs[k]):
                        ckwargs[k] = digit_map(ckwargs[k][0]) + ckwargs[k][1:]
                else:
                    ckwargs[k] = v
            return func(self, *args, **kwargs)
        return _clean

    def create_fight_table(self):
        with Access(self.dbname) as conn:
            curs = conn.cursor()
            curs.execute("SELECT table_name from information_schema.tables where "
                         "table_schema='public' and table_name='fights'")
            if curs.fetchone() is None:
                curs.execute('CREATE TABLE if not exists fights(time '
                             'timestamp, p1 text, p2 text, m1 integer, '
                             'm2 integer, status text, winner integer)')
                conn.commit()

    @clean_string
    def new_fight(self, ftime, first_player, second_player, money1, money2, status, winner):
        with Access(self.dbname) as conn:
            curs = conn.cursor()
            curs.execute(
                'insert into fights(time, p1, p2, m1, m2, winner) '
                'values (%s, %s, %s, %s, %s, %s, %s)',
                (dt.utcfromtimestamp(ftime), first_player.strip(), second_player.strip(),
                 money1, money2, status, winner))
            conn.commit()
        return int(ftime.total_seconds())

    @clean_string
    def record_fight(self, ftime, first_player, second_player,
                     money1=0, money2=0, status='Open', winner=0):
        with Access(self.dbname) as conn:
            curs = conn.cursor()
            curs.execute(
                'select m1, m2, status, winner from fights'
                ' where p1=%(p1)s and p2=%(p2)s and time=%(time)s',
                {'p1': first_player, 'p2': second_player, 'time': dt.utcfromtimestamp(ftime)})
            current = curs.fetchone()
            if current is None:
                curs.execute(
                    'insert into fights(time, p1, p2, m1, m2, status, winner) '
                    'values (%s, %s, %s, %s, %s, %s, %s)',
                    (dt.utcfromtimestamp(ftime), first_player.strip(), second_player.strip(),
                     money1, money2, status, winner))
            else:
                money1 = money1 if money1 is not None else current[0]
                money2 = money2 if money2 is not None else current[1]
                status = status if status is not None else current[2]
                winner = winner if winner is not None else current[3]

                curs.execute('update fights set m1=%(m1)s, m2=%(m2)s, '
                             'status=%(status)s, winner=%(winner)s where '
                             'time=%(time)s and p1=%(p1)s and p2=%(p2)s',
                             {'time': dt.utcfromtimestamp(ftime), 'status': status, 'p1': first_player,
                              'p2': second_player, 'm1': money1, 'm2': money2,
                              'status': status, 'winner': winner})
            conn.commit()

    @clean_string
    def get_odds(self, p1, p2):
        ret = None
        with Access("saltydb") as conn:
            curs = conn.cursor()
            curs.execute('select m1, m2 from fights where '
                         "p1=%(tm1)s and p2=%(tm2)s order by"
                         ' time desc', {'tm1': p1, 'tm2': p2})
            ret = curs.fetchone()

        odd1, odd2 = None, None
        if ret is not None:
            odd1 = ret[0] / (ret[0] + ret[1])
            odd2 = ret[1] / (ret[0] + ret[1])
        return (odd1, odd2)

    @clean_string
    def get_money(self, p1, p2):
        ret = [None, None]
        with Access("saltydb") as conn:
            curs = conn.cursor()
            curs.execute('select m1, m2 from fights where '
                         "p1=%(tm1)s and p2=%(tm2)s order by"
                         ' time desc', {'tm1': p1, 'tm2': p2})
            ret = curs.fetchone()
        return ret

    @clean_string
    def get_winner(self, p1, p2):
        ret = [None, None]
        with Access("saltydb") as conn:
            curs = conn.cursor()
            curs.execute('select winner, status from fights where'
                         ' p1=%(tm1)s and p2=%(tm2)s'
                         ' order by time desc',
                         {"tm1": p1, "tm2": p2})
            ret = curs.fetchone()
        return ret

    def get_all_fighters(self):
        ''' Returns a set of all recorded fighters '''
        ret = None
        with Access("saltydb") as conn:
            curs = conn.cursor()
            curs.execute("select p1, p2 from fights")
            ret = curs.fetchall()
        return set([i for j in ret for i in j]) if ret is not None else ret

    def get_all_winners(self):
        ''' Returns a dictionary of all recorded fighters and their wins'''
        ret = None
        with Access("saltydb") as conn:
            curs = conn.cursor()
            curs.execute("select p1, p2, winner from fights")
            ret = curs.fetchall()
            if ret is not None:
                ret = {[p1, p2][win] for p1, p2, win in ret if win > 0}
        return ret

    def get_all_losers(self):
        ''' Returns a dictionary of all recorded fighters and their losses'''
        ret = None
        with Access("saltydb") as conn:
            curs = conn.cursor()
            curs.execute("select p1, p2, winner from fights")
            ret = curs.fetchall()
            if ret is not None:
                ret = {[p1, p2][win - 1] for p1, p2, win in ret if win > 0}
        return ret

    def get_all_fights(self):
        ''' Returns the teams, totals, and winner '''
        ret = None
        with Access("saltydb") as conn:
            curs = conn.cursor()
            curs.execute("select time, p1, p2, m1, m2, status, winner "
                         "from fights")
            ret = curs.fetchall()
        return ret

    def get_last_fight(self):
        ftime = int(time.time())
        with Access("saltydb") as conn:
            curs = conn.cursor()
            curs.execute("select time, p1, p2, money1, money2, "
                         "winner from fights where "
                         "time < %(time)s order by time desc",
                         {"time": dt.utcfromtimestamp(ftime)})
            ret = curs.fetchone()
        return ret if ret is not None else [None for i in range(9)]

    @clean_string
    def create_bettor_table(self):
        with Access("saltydb") as conn:
            curs = conn.cursor()
            curs.execute("SELECT table_name from information_schema.tables where "
                         "table_schema='public' and table_name='bettors'")
            if curs.fetchone() is None:
                curs.execute('CREATE TABLE if not exists bettors'
                             '(bettor text, origin timestamp)')
                conn.commit()

    @clean_string
    def create_bettor(self, bettor_name, timestamp):
        with Access("saltydb") as conn:
            curs = conn.cursor()
            curs.execute("SELECT table_name from information_schema.tables"
                         " where table_schema='public' and table_name='bettors'")
            if curs.fetchone() is None:
                curs.execute('create table if not exists bettors'
                             '(bettor text, origin timestamp)')
                conn.commit()
            curs.execute("insert into bettors(bettor, origin) "
                         "values (%s %s)", (bettor_name, dt.utcfromtimestamp(timestamp)))
            conn.commit()

            curs.execute("SELECT table_name from information_schema.tables "
                         "where table_schema='public' and table_name={}".format(bettor_name))
            if curs.fetchone() is None:
                curs.execute('create table if not exists {}'
                             '(fighttime timestamp, balance bigint, '
                             'beton integer, wager integer, rank integer)'
                             ''.format(bettor_name))
            conn.commit()

    @clean_string
    def record_bettor(self, bettor_name, ftime, bal, beton=0, wager=0, rank=0):
        self.create_table(bettor_name, ftime)
        with Access("saltydb") as conn:
            curs = conn.cursor()
            curs.execute('SELECT balance, beton, wager, rank from {}'
                         ' where fighttime=%(ftime)s'.format(bettor_name),
                         {'ftime': dt.utcfromtimestamp(ftime)})
            if curs.fetchone() is not None:
                curs.execute("update {} set balance=%(bal)s, beton=%(bt)s, "
                             "wager=%(wag)s, rank=%(rn)s where fighttime=%(ftime)s",
                             {'bal': bal, 'bt': beton,
                              'wag': wager, 'rn': rank, 'ftime': dt.utcfromtimestamp(ftime)})
            else:
                curs.execute("insert into {}(fighttime, balance, beton, wager, rank) "
                             "values (%s %s %s %s %s)".format(bettor_name),
                             (dt.utcfromtimestamp(ftime), bal, beton, wager, rank))
            conn.commit()

    @clean_string
    def record_bettors(self, bettors, fighttime):
        ''' Assumes that the bettors table exists '''
        with Access("saltydb") as conn:
            curs = conn.cursor()
            curs.execute("SELECT bettor from bettors")
            if curs.fetchone() is None:
                curs.execute('create table if not exists bettors'
                             '(bettor text, origin timestamp)')
                existing = [None]
            else:
                existing = curs.fetchall()

            for bettor, info in bettors.items():
                if bettor not in existing:
                    curs.execute('create table if not exists {} '
                                 '(fighttime timestamp, balance bigint, '
                                 'beton integer, wager integer, rank integer, '
                                 'ranking integer)'
                                 ''.format(bettor))
                    conn.commit()
                curs.execute('SELECT balance, beton, wager, rank from {}'
                             ' where fighttime=%(ftime)s'.format(bettor),
                             {'ftime': dt.utcfromtimestamp(fighttime)})
                if curs.fetchone() is not None:
                    curs.execute("update {} set balance=%(bal)s, beton=%(bt)s, "
                                 "wager=%(wag)s, rank=%(rn)s, ranking=%(rn)s,"
                                 " where fighttime=%(ftime)s".format(bettor),
                                 {'bal': info['balance'], 'bt': info['bet'],
                                  'wag': info['wager'], 'rn': info['rank'],
                                  'ftime': dt.utcfromtimestamp(fighttime),
                                  'rnk': info['ranking']})
                else:
                    curs.execute('insert into {}(fighttime, balance, beton, '
                                 'wager, rank) values(%s, %s, %s, %s, %s, %s)'
                                 ''.format(bettor),
                                 (dt.utcfromtimestamp(fighttime),
                                  info['balance'], info['bet'], info['wager'],
                                  info['rank'], info['ranking']))

            conn.commit()
