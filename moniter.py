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

def get_severe_erros(version):
		SQL = """
		SELECT * FROM(
			SELECT app_v, log, is_crash, COUNT(*) AS cnt
			FROM crash_log
			WHERE version = %s
			GROUP BY log
			ORDER BY cnt DESC
			) AS error_log
			WHERE cnt >= %s
		"""

		print("========================================")
		print("get_severe_erros")
		print(version)
		rows = query(CRASH_DB_NAME, SQL, (version, SEVERE_ERROR_THRESHOLD))
		for row in rows:
				print("error times", type(row))
				print(row)
		print("========================================")
		return;

def get_errors(version):
		SQL = """
			SELECT app_v, log, is_crash, COUNT(*) AS cnt
#			SELECT COUNT(*) AS cnt
			FROM crash_log
			WHERE version = %s
			GROUP BY log
			ORDER BY cnt DESC
		"""

		print("========================================")
		print("get_errors")
		print(version)
		rows = query(CRASH_DB_NAME, SQL, (version))
		for row in rows:
#				print(row)
				print "error times:", row[3]
				print "log:\n" + row[1]
				print("----------------------------------------")
		print("========================================")
		return;

def get_top_errors(version):
		SQL = """
			SELECT log, is_crash, COUNT(*) AS cnt
#			SELECT COUNT(*) AS cnt
			FROM crash_log
			WHERE version = %s
			GROUP BY log
			ORDER BY cnt DESC
			LIMIT %s
		"""

		print("========================================")
		print("get_top_errors")
		print(version)
		rows = query(CRASH_DB_NAME, SQL, (version, TOP_RECORD_NUM))
		for row in rows:
#				print(row)
				print "error times:", row[2]
				print "is crash:", row[1]
				print "log:\n" + row[0]
				print("----------------------------------------")
		print("========================================")
		return;

def get_all_latest_info(callback):
		latestVersions = get_latest_versions()
		for version in latestVersions.keys():
				callback(version)
		return;

def main(argv):
		try:
				opts, args = getopt.getopt(argv, "se")
		except getopt.GetoptError as err:
				print "exception", str(err)
				sys.exit(2)
		for opt, arg in opts:
				#print(opt, arg)
				if opt == '-s':
						get_all_latest_info(get_severe_erros)
				elif opt == '-e':
						get_all_latest_info(get_errors)


if __name__ == "__main__":
		main(sys.argv[1:])
