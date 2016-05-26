#!/usr/bin/env python
# coding:utf-8
import MySQLdb
import sys
import getopt
import ConfigParser
import os
import re
import datetime
from contextlib import closing
import smtplib
from email.MIMEMultipart import MIMEMultipart
# from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
# import email.Encoders as encoders

########################################
DB_CONF = "db.conf"
VERSION_SECTION = "Version"
ERROR_SECTION = "Error"
########################################
QUERY_CONF = "query.conf"
SEVERE_ERROR_SECTION = "SevereError"
DISPLAY_OPTION_SECTION = "DisplayOption"
########################################
configParser = ConfigParser.ConfigParser()

configParser.read(QUERY_CONF)
SEVERE_ERROR_THRESHOLD = configParser.getint(SEVERE_ERROR_SECTION, 'threshold')
TOP_RECORD_NUM = configParser.getint(DISPLAY_OPTION_SECTION, 'top_record_num')
########################################


def query(db_section, sql, params=None):
    def connect_db(host, port, user, passwd, db_name):
        return MySQLdb.connect(host=host,
                               port=port,
                               user=user,
                               passwd=passwd,
                               db=db_name)

    configParser = ConfigParser.ConfigParser()
    configParser.read(DB_CONF)
    host = configParser.get(db_section, 'host')
    port = configParser.getint(db_section, 'port')
    user = configParser.get(db_section, 'user')
    passwd = configParser.get(db_section, 'passwd')
    db_name = configParser.get(db_section, 'db_name')

    with closing(connect_db(host, port, user, passwd, db_name)) as db:
        with closing(db.cursor()) as cursor:
            cursor.execute(sql, params)

            rows = []
            row = cursor.fetchone()
            while row is not None:
                # print(row)
                rows.append(row)
                row = cursor.fetchone()

            return rows


def get_all_versions():
    SQL = """
    SELECT v.created_at, CONCAT(v.v1, ".", MAX(v.v2), ".", v.v3) AS version
    FROM version v, version_resources vr
    WHERE v.id = vr.version_id
    AND v.is_publish = 1
    GROUP BY v.created_at
    """
    rows = query(VERSION_SECTION, SQL)

    all_versions = []
    for row in rows:
        created_time = str(row[0])
        version = str(row[1])
        all_versions.append((created_time, version))

    sorted(all_versions, key=lambda created_time: all_versions[0])
    return all_versions


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
    rows = query(VERSION_SECTION, SQL)

    lang2Version = {}
    latestVersions = {}
    for row in rows:
        v1 = str(row[0])
        v2 = str(row[1])
        v3 = str(row[2])
        version = v1 + "." + v2 + "." + v3
        lang2Version[row[3]] = version
        latestVersions[version] = True

    print gen_version_report(lang2Version)
    return latestVersions, lang2Version


def gen_version_report(lang2Version):
    report = "========================================\n"
    report = report + "Latest version of each language:\n"
    report = report + "========================================\n"
    report = report + "Language\tLatest Version\n"
    report = report + "----------------------------------------\n"
    for k, v in lang2Version.items():
        report = report + str(k) + '\t\t' + str(v) + '\n'
        # report = report + "========================================\n"
    return report


def get_latest_time(version):
    SQL = """
    SELECT MAX(time)
    FROM crash_log
    WHERE version = %s
    """
    params = (version)
    return query(ERROR_SECTION, SQL, params)


def get_error_number(version, args={}):
    is_crash = args.get('is_crash')
    SQL = """
    SELECT COUNT(*)
    FROM crash_log
    WHERE version = %s
    AND is_crash = %s
    """
    params = (version, is_crash)
    return query(ERROR_SECTION, SQL, params)


def gen_error_num_report(version, *args):
    # first column in the first row of query result
    error_num = (get_error_number(version, {'is_crash': 0}))[0][0]
    crash_num = (get_error_number(version, {'is_crash': 1}))[0][0]
    report = "%s\t%d\t%d\n" % (version, error_num, crash_num)
    print "%s\t%d\t%d\n" % (version, error_num, crash_num)
    return report


def timestamp_to_string(timestamp):
    return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d'
                                                               ' %H:%M:%S')


def get_avg_error_num(error_num, start_timestamp, end_timestamp):
    timestamp_diff = end_timestamp - start_timestamp
    avg_num_per_sec = error_num * 1.0 / timestamp_diff
    avg_num_per_min = avg_num_per_sec * 60
    avg_num_per_hour = avg_num_per_min * 60
    avg_num_per_day = avg_num_per_hour * 24
    return avg_num_per_day, avg_num_per_hour, avg_num_per_min, avg_num_per_sec


def gen_all_error_report():
    all_versions = get_all_versions()

    report = "\n========================================\n"
    report = report + "Total error/crash number of each version:\n"
    report = report + "========================================\n"
    report = report + """CreatedTime\tEndTime\tVersion\tError\tCrash\t\
    CrashPerDay\tCrashPerHour\n"""

    for version_info in all_versions:
        created_timestamp = int(version_info[0])
        created_time = timestamp_to_string(created_timestamp)
        version = version_info[1]
        error_num = (get_error_number(version, {'is_crash': 0}))[0][0]
        crash_num = (get_error_number(version, {'is_crash': 1}))[0][0]
        if crash_num > 0:
            latest_timestamp = (get_latest_time(version))[0][0]
            latest_time = timestamp_to_string(latest_timestamp)
            crash_per_day, crash_per_hour, _, _ \
                = get_avg_error_num(crash_num,
                                    created_timestamp,
                                    latest_timestamp)
            crash_per_day = int(round(crash_per_day))
            crash_per_hour = int(round(crash_per_hour))
            report = report \
                + "%s\t%s\t%s\t%d\t%d\t%d\t%d\n" % (created_time,
                                                    latest_time,
                                                    version,
                                                    error_num,
                                                    crash_num,
                                                    crash_per_day,
                                                    crash_per_hour)
            print "%s\t%s\t%s\t%d\t%d\t%d\t%d" % \
                (created_time, latest_time, version, error_num,
                 crash_num, crash_per_day, crash_per_hour)

    return report


def get_severe_errors(version, *args):
    filter_error(version, {'threshold': SEVERE_ERROR_THRESHOLD})


def get_errors(version, *args):
    filter_error(version)


def get_top_errors(version, *args):
    filter_error(version, {'limit': TOP_RECORD_NUM})


def filter_error(version, args={}):
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
        WHERE_PHRASE = WHERE_PHRASE + " AND is_crash=%s "
        paramsList.append(is_crash)

    GROUP_PHRASE = " GROUP BY log "
    ORDER_PHRASE = " ORDER BY cnt DESC "
    LIMIT_PHRASE = ""
    if limit:
        LIMIT_PHRASE = " LIMIT %s "
        paramsList.append(limit)

    SQL = SELECT_PHRASE + FROM_PHRASE + WHERE_PHRASE + GROUP_PHRASE \
        + ORDER_PHRASE + LIMIT_PHRASE

    if threshold:
        SQL = "SELECT * FROM (" + SQL + ") AS error_logs WHERE cnt >= %s "
        paramsList.append(threshold)

    print("========================================")
    print "version:", version
    rows = query(ERROR_SECTION, SQL, tuple(paramsList))
    print gen_error_info_report(rows)
    print("========================================")

    return rows


def gen_error_info_report(rows):
    merged_rows = {}
    for row in rows:
        msg = re.sub('\[.*\]\:', '', row[0])
        times = row[1]
        if msg in merged_rows.keys():
            merged_rows[msg] += times
        else:
            merged_rows[msg] = times

    report = "\n"
    num = 1
    for error_msg, error_times in sorted(merged_rows.iteritems(),
                                         key=lambda (k, v): (v, k),
                                         reverse=True):
        report = report + "Top. %d\n" % num
        report = report + "Error times:" + str(error_times) + "\n"
        report = report + "Error log:\n" + error_msg + "\n"
        report = report + "----------------------------------------\n"
        num = num + 1
    return report


def sync_crash(version, *args):
    CRASH_CONF = "crash.conf"
    REMOTE_SESSION = "Remote"
    LOCAL_SESSION = "Local"

    configParser = ConfigParser.ConfigParser()
    configParser.read(CRASH_CONF)

    host = configParser.get(REMOTE_SESSION, 'host')
    port = configParser.getint(REMOTE_SESSION, 'port')
    user = configParser.get(REMOTE_SESSION, 'user')
    remote_dir_root = configParser.get(REMOTE_SESSION, 'crash_log')
    crash_log_root = configParser.get(LOCAL_SESSION, 'crash_log')
    dump_file_root = configParser.get(LOCAL_SESSION, 'dump_file')
    symbol_root = configParser.get(LOCAL_SESSION, 'symbol')

    cmd = "./rsync-crash.sh %s %s %s %s %s %s %s %s " % (version,
                                                         host,
                                                         port,
                                                         user,
                                                         remote_dir_root,
                                                         crash_log_root,
                                                         dump_file_root,
                                                         symbol_root)
    os.system(cmd)


def get_info_of_version(version, callback, params=None):
    assert version
    callback(version, params)


def get_all_latest_info(callback, params=None):
    latestVersions, _ = get_latest_versions()
    for version in latestVersions.keys():
        get_info_of_version(version, callback, params)


def send_mail():
    MAIL_CONF = "mail.conf"
    MAIL_SESSION = "Mail"

    configParser = ConfigParser.ConfigParser()
    configParser.read(MAIL_CONF)
    sender_name = configParser.get(MAIL_SESSION, 'sender_name')
    sender = configParser.get(MAIL_SESSION, 'sender')
    subscribers = configParser.get(MAIL_SESSION, 'subscribers').split()
    subject = configParser.get(MAIL_SESSION, 'subject')
    content = configParser.get(MAIL_SESSION, 'content')

    message = MIMEMultipart('alternative')
    message['From'] = "%s <%s>" % (sender_name, sender)
    message['Subject'] = subject

    latestVersions, lang2Version = get_latest_versions()
    report = gen_version_report(lang2Version)

    report = report + "\n========================================\n"
    report = report + "Total error/crash number of each version:\n"
    report = report + "========================================\n"
    report = report + "Version\tError\tCrash\n"

    for version in latestVersions.keys():
        report = report + gen_error_num_report(version)

    # report = report + "\n" + gen_all_error_report()

    report = report + "\n========================================\n"
    report = report + "Top 10 error log of each version:\n"
    report = report + "========================================\n"

    for version in latestVersions.keys():
        report = report + "----------------------------------------\n"
        report = report + "Version: %s\n" % version
        report = report + "----------------------------------------\n"
        rows = filter_error(version, {'limit': TOP_RECORD_NUM,
                                      'is_crash': 0})
        report = report + gen_error_info_report(rows)

    content = content + "\n" + report

    content = MIMEText(content, "plain", "utf-8")
    message.attach(content)
    for i, subscriber in enumerate(subscribers):
        print i, subscriber

        message['To'] = subscriber

        try:
            smtpObj = smtplib.SMTP('localhost')
            smtpObj.sendmail(sender, subscriber, message.as_string())
            print "Successfully sent email to ", subscriber
            smtpObj.quit()
        except smtplib.SMTPException:
            print "Error: unable to send email to ", subscriber


rules = (
    (('-M', '--mail'), send_mail),
)


def handle_opts(opts):
    callback = None
    version = None
    params = {}

    for opt, arg in opts:
        for match_opts, apply_rule in rules:
            if opt in match_opts:
                return apply_rule()

        if opt in ('-v', '--version'):
            version = arg
        elif opt in ('-s', '--severe'):
            callback = get_severe_errors
        elif opt in ('-e', '--error'):
            callback = get_errors
        elif opt in ('-E', '--error-report'):
            print gen_all_error_report()
            sys.exit(0)
        elif opt in ('-f', '--filter'):
            callback = filter_error
            params['keyword'] = arg
        elif opt in ('-c', '--iscrash'):
            callback = filter_error
            params['is_crash'] = arg
        elif opt in ('-l', '--limit'):
            callback = filter_error
            params['limit'] = int(arg)
        elif opt in ('-t', '--threshold'):
            callback = filter_error
            params['threshold'] = int(arg)
        elif opt in ('-C', '--syncrash'):
            callback = sync_crash
        elif opt in ('-T', '--top'):
            callback = get_top_errors
        elif opt in ('-n', '--num'):
            params = None
            callback = gen_error_num_report

    assert callback
    if version:
        get_info_of_version(version, callback, params)
    else:
        get_all_latest_info(callback, params)


def main(argv):
    try:
        opts, args = getopt.getopt(argv, "seEv:f:c:l:t:CMTn", ['severe',
                                                               'error',
                                                               'error-report',
                                                               'version=',
                                                               'filter=',
                                                               'iscrash=',
                                                               'limit=',
                                                               'threshold=',
                                                               'syncrash',
                                                               'mail',
                                                               'top',
                                                               'num'])
    except getopt.GetoptError as err:
        sys.stderr.write(str(err))
        sys.exit(2)

    handle_opts(opts)


if __name__ == "__main__":
    main(sys.argv[1:])
