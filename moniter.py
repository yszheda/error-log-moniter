#coding:utf-8
import MySQLdb
import sys, getopt
import ConfigParser
from contextlib import closing

########################################
DB_CONF = "db.conf"
CONNECT_SECTION = "Connect"
DB_SECTION = "Database"
########################################
QUERY_CONF = "query.conf"
SEVERE_ERROR_SECTION = "SevereError"
DISPLAY_OPTION_SECTION = "DisplayOption"
########################################

configParser = ConfigParser.ConfigParser()

configParser.read(DB_CONF)
HOST = configParser.get(CONNECT_SECTION, 'host')
PORT = configParser.getint(CONNECT_SECTION, 'port')
USER = configParser.get(CONNECT_SECTION, 'user')
PASSWD = configParser.get(CONNECT_SECTION, 'passwd')
VERSION_DB_NAME = configParser.get(DB_SECTION, 'version')
CRASH_DB_NAME = configParser.get(DB_SECTION, 'error')

configParser.read(QUERY_CONF)
SEVERE_ERROR_THRESHOLD = configParser.getint(SEVERE_ERROR_SECTION, 'threshold')
TOP_RECORD_NUM = configParser.getint(DISPLAY_OPTION_SECTION, 'top_record_num')

########################################
def query(db_name, sql, params = None):
		def connect_db():
				return MySQLdb.connect(host = HOST,
								port = PORT,
								user = USER,
								passwd = PASSWD,
								db = db_name)

		with closing(connect_db()) as db:
				with closing(db.cursor()) as cursor:
						cursor.execute(sql, params)

						rows = []
						row = cursor.fetchone()
						while row is not None:
								#print(row)
								rows.append(row)
								row = cursor.fetchone()
						return rows;

def get_latest_versions():
		SQL = """
				SELECT v.v1, MAX(v.v2), v.v3, vr.lang, vr.created_at
				FROM version v, version_resources vr
				WHERE v.id = vr.version_id
				AND vr.created_at
				IN (SELECT MAX( created_at ) 
						FROM version_resources
						GROUP BY lang)
				GROUP BY vr.lang
		"""

		rows = query(VERSION_DB_NAME, SQL)

		lang2Version = {}
		latestVersions = {}
		for row in rows:
			v1 = str(row[0])
			v2 = str(row[1])
			v3 = str(row[2])
			version = v1 + "." + v2 + "." + v3
			lang2Version[row[3]] = version
			latestVersions[version] = True

		for k, v in lang2Version.items():
				print k, ':', v

		return latestVersions;

def get_severe_errors(version, *args):
		filter_error(version, { 'threshold': SEVERE_ERROR_THRESHOLD })

def get_errors(version, *args):
		filter_error(version)

def get_top_errors(version, *args):
		filter_error(version, { 'limit': TOP_RECORD_NUM })

def filter_error(version, args = {}):
		keyword = args.get('keyword')
		is_crash = args.get('is_crash')
		limit = args.get('limit')
		threshold = args.get('threshold')

		SELECT_PHRASE = " SELECT log, COUNT(*) AS cnt "
		FROM_PHRASE = " FROM crash_log "
		WHERE_PHRASE = " WHERE version = %s "
		params = (version, )
		paramsList = list(params)
		if keyword:
				WHERE_PHRASE = WHERE_PHRASE + " AND log LIKE '%%'%s'%%' "
				paramsList.append(keyword)
		if is_crash:
				WHERE_PHRASE = WHERE_PHRASE + " AND is_crash=%d "
				paramsList.append(is_crash)
		GROUP_PHRASE = " GROUP BY log "
		ORDER_PHRASE = " ORDER BY cnt DESC "
		LIMIT_PHRASE = ""
		if limit:
			LIMIT_PHRASE = " LIMIT %s "
			paramsList.append(limit)

		SQL = SELECT_PHRASE + FROM_PHRASE + WHERE_PHRASE + GROUP_PHRASE + ORDER_PHRASE + LIMIT_PHRASE
		if threshold:
				SQL = "SELECT * FROM (" + SQL + ") AS error_logs WHERE cnt >= %s "
				paramsList.append(threshold)

		print("========================================")
		print "version:", version
		rows = query(CRASH_DB_NAME, SQL, tuple(paramsList))
		for row in rows:
#				print(row)
				print "error times:", row[1]
				print "log:\n" + row[0]
				print("----------------------------------------")
		print("========================================")
		return;

########################################
def get_info_of_version(version, callback, params = None):
		assert version != None
		callback(version, params)

def get_all_latest_info(callback, params = None):
		latestVersions = get_latest_versions()
		for version in latestVersions.keys():
				get_info_of_version(version, callback, params)
		return;
########################################

def main(argv):
		callback = None
		version = None
		params = {}
		try:
				opts, args = getopt.getopt(argv, "sev:f:", ['severe',
						'error',
						'version=',
						'filter='])
		except getopt.GetoptError as err:
				sys.stderr.write(str(err))
				sys.exit(2)
		for opt, arg in opts:
				#print(opt, arg)
				if opt in ('-v', '--version'):
						version = arg
				elif opt in ('-s', '--severe'):
						callback = get_severe_errors
				elif opt in ('-e', '--error'):
						callback = get_errors
				elif opt in ('-f', '--filter'):
						callback = filter_error
						params['keyword'] = arg
		assert callback != None
		if version:
				get_info_of_version(version, callback, params)
		else:
				get_all_latest_info(callback, params)


if __name__ == "__main__":
		main(sys.argv[1:])
