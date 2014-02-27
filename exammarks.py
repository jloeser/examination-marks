#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Author Jan Löser <jloeser@suse.de>
# Published under the GNU Public Licence 2
try:
  import sys
  import os
  import re
  import urllib
  import urllib2
  from cookielib import CookieJar
  from BeautifulSoup import BeautifulSoup
  import smtplib
  from email.mime.text import MIMEText
  from email.mime.multipart import MIMEMultipart
except ImportError as e:
  sys.stdout.write('Error: {0}\n'.format(e))
  sys.exit(1)

# set user credentials and mail settings...
USERNAME = ''
PASSWORD = ''
RECIPIENTS = []
SMTPSERVER = ''

FILENAME = 'marks'
LATEST = FILENAME + '.latest'
OLD = FILENAME + '.old'
URL = 'https://virtuohm.ohmportal.de'

if len(USERNAME) == 0 or len(PASSWORD) == 0:
    sys.stderr.write('Error: no username/password set\n')
    sys.exit(1)

if len(SMTPSERVER) == 0 or len(RECIPIENTS) == 0:
    sys.stderr.write('Error: no mail server/recipients set\n')
    sys.exit(1)

def send(subject, message, fromaddr='noreply-virtuohm@th-nuernberg.de'):
    try:
        for recipient in RECIPIENTS:
            msg = MIMEMultipart()
            msg['To'] = recipient
            msg['X-BeenThere'] = 'virtuohm'
            msg['From'] = fromaddr
            msg['Subject'] = subject
            text = MIMEText(message)
            text.add_header("Content-Disposition", "inline")
            msg.attach(text)

            s = smtplib.SMTP(SMTPSERVER)
            s.sendmail(msg['From'], [recipient], msg.as_string())
            s.quit()
    except Exception as e:
        sys.stderr.write('Error: {0}!\n'.format(e))
        return False
    return True


def get_exam_marks():
    post = urllib.urlencode({'BenName': USERNAME, 'Password': PASSWORD})
    urls = [
        URL,
        URL + '/pls/papi/papiadmin.do_login1',
        URL + '{0}',
        URL + '/pls/exammarks/student.show_noten?in_crimmo={0}',
        URL + '/pls/papi/papiadmin.dologout?in_crimmo={0}']
    jar = CookieJar()
    session = urllib2.build_opener(urllib2.HTTPCookieProcessor(jar))

    for i in range(0, len(urls)):
        data = post if i == 1 else None
        response = session.open(urls[i], data)
        if response.code != 200:
            sys.stderr.write('Error: response.code is {0}\n'.format(response.code))
            sys.exit(1)
        if i == 1:
            redirect = re.search('CONTENT="0;URL=(.+?)"', response.read()).group(1)
            crimmo = re.search('in_crimmo=(.*?)&', redirect).group(1)
            urls[2] = urls[2].format(redirect)
            urls[3] = urls[3].format(crimmo)
            urls[4] = urls[4].format(crimmo)
        if i == 3:
            with open(LATEST,'w') as f:
                f.write(response.read())
    return True

def same():
    if os.path.isfile(OLD):
        # dump session keys for comparison
        llines = [line for line in open(LATEST).read().splitlines() if line.find('in_crimmo') == -1]
        olines = [line for line in open(OLD).read().splitlines() if line.find('in_crimmo') == -1]
    os.rename(LATEST, OLD)
    return True if llines == olines else False

if __name__ == '__main__':
    # be quiet
    if '-q' in sys.argv:
        sys.stdout = open('/dev/null', 'w')
    get_exam_marks()
    if not same():
        result = ''
        # get new examination marks from HTML
        with open(OLD, 'r') as f:
            table = BeautifulSoup(f.read()).findAll('table')[2]
            for tr in table.findAll('tr')[2:]:
                tds = tr.findAll('td')
                subject = tds[0].text
                mark = tds[2].text
                result += '{0:<50} {1}\n'.format(subject, mark)
        send('New examination marks online!', result)
