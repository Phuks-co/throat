#!/usr/bin/env python3

import MySQLdb
import MySQLdb.cursors
import config
import datetime

rv = MySQLdb.connect(host=config.DB_HOST,
                         user=config.DB_USER,
                         passwd=config.DB_PASSWD,
                         db=config.DB_NAME,
                         cursorclass=MySQLdb.cursors.DictCursor,
                         use_unicode=True,
                         charset="utf8")
c = rv.cursor()

c.execute('SELECT sm.value AS creation, g.name, g.sid, COUNT(m.pid) AS posts FROM sub AS g LEFT JOIN sub_post AS m ON g.sid = m.sid LEFT JOIN sub_metadata AS sm ON sm.sid = g.sid AND sm.key = \'creation\' GROUP BY g.sid HAVING posts = 0 AND CAST(creation AS datetime) < NOW() - INTERVAL 1 DAY')
subs = c.fetchall()

for sub in subs:
    print("Deleting {0}".format(sub['name']))
    c.execute('DELETE FROM `sub_metadata` WHERE `sid`=%s', (sub['sid'],))
    c.execute('DELETE FROM `sub_stylesheet` WHERE `sid`=%s', (sub['sid'],))
    c.execute('DELETE FROM `sub_subscriber` WHERE `sid`=%s', (sub['sid'],))
    c.execute('DELETE FROM `sub_flair` WHERE `sid`=%s', (sub['sid'],))
    c.execute('DELETE FROM `sub_log` WHERE `sid`=%s', (sub['sid'],))
    c.execute('DELETE FROM `sub` WHERE `sid`=%s', (sub['sid'],))
    c.execute('INSERT INTO `site_log` (`time`, `action`, `desc`) VALUES (`%s`, `%s`, `%s`)', (datetime.datetime.utcnow(), 8, 'Deleted inactive sub ' + sub['name']))
    rv.commit()
