import __fix
import MySQLdb
import MySQLdb.cursors
import config
import requests

rv = MySQLdb.connect(host=config.DB_HOST,
                     user=config.DB_USER,
                     passwd=config.DB_PASSWD,
                     db=config.DB_NAME,
                     cursorclass=MySQLdb.cursors.DictCursor,
                     use_unicode=True,
                     charset="utf8")
c = rv.cursor()
c.execute('SELECT * FROM mining_leaderboard')
users = c.fetchall()

for user in users:
    print("Updating for ", user['username'])
    hr = requests.get('https://api.coin-hive.com/user/balance?name={0}&secret={1}'.format(user['username'], config.COIN_HIVE_SECRET)).json()
    if hr['success']:
        c.execute('UPDATE mining_leaderboard SET `score`=%s WHERE `username`=%s', (hr['balance'], user['username']))

rv.commit()
