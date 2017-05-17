"""
Description:
    This program implements a simple Twitter bot that tweets information about bills in Congress
    that are (in)directly related to cyber issues. This bot uses a MySQL database backend to
    keep track of bills, both posted and unposted (i.e., tweeted and yet to be tweeted, respectively).
    For this initial proof of concept, bill data are scraped from the official US Government
    Publishing Office website. For future versions, it would probably be better to connect to a
    less cumbersome endpoint like ProPublica.

Module:
    This module implements the driver functionality for the bot. This is the main entrypoint.

Libraries:
    This program makes use of the following libraries:
        lxml
            Stephan Richter / Infrae
            BSD License
            http://lxml.de/

        xmltodict        
            Martin Blech & contribs.    
            MIT License
            https://github.com/martinblech/xmltodict

        python-twitter    
            Mike Taylor ('bear') & contribs.
            Apache License 2.0
            https://github.com/bear/python-twitter

        requests
            Kenneth Reitz
            Apache License 2.0
            http://docs.python-requests.org/en/master

        MySQL Connector
            Oracle & affiliates
            Misc. License
            https://dev.mysql.com/doc/connector-python/en/

License:
    Copyright 2017 J. Michael Beaver

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

References:
    https://www.gpo.gov/fdsys/bulkdata/BILLSTATUS/resources/BILLSTATUS-XML_User-Guide-v1.pdf
    https://github.com/usgpo/bill-status/blob/master/BILLSTATUS-XML_User_User-Guide.md
    https://projects.propublica.org/api-docs/congress-api/endpoints/
    https://github.com/bear/python-twitter
    https://github.com/martinblech/xmltodict
    http://docs.python-requests.org/en/master
    https://dev.mysql.com/doc/connector-python/en/
    http://lxml.de/
    https://www.python.org/dev/peps/pep-0249
    https://is.gd/apishorteningreference.php
    https://www.pantz.org/software/mysql/mysqlcommands.html
    https://bitbucket.org/ned/coveragepy/commits/f8e9d62f1412
    https://www.govtrack.us/api/v2/role
    https://choosealicense.com/licenses/apache-2.0/
    http://www.mysqltutorial.org/getting-started-mysql-python-connector/
"""
from bill        import Bill
from bill_db     import BillDB
from collections import OrderedDict
from lxml        import html
import constants
import json
import logging as log
import re
import requests
import sys
import time
import twitter
import xmltodict

#-------------------------------------------------------------------------------------------------------------------------------------------------

log.basicConfig(filename='cyber_law_bot.log', 
                level=log.INFO, 
                format='%(asctime)s %(levelname)-8s %(message)s',
                datefmt='%m-%d %H:%M')

REGEX  = re.compile(r'(?P<position>Sen.|Rep.) (?P<last_name>\w+), (?P<first_name>\w+) (?P<initial>\w+.)*')
REGEX2 = re.compile(r'(?P<position>Sen.|Rep.) (?P<last_name>\w+) (?P<last_name2>\w+), (?P<first_name>\w+) (?P<initial>\w+.)*')

#-------------------------------------------------------------------------------------------------------------------------------------------------

def get_bill_urls(data):
    """Scrapes bill URLs from USGPO page.

    Args:
        data: HTML data downloaded from USGPO page.

    Returns:
        A list of URLs, one per bill (on GPO's servers).
    """
    tree  = html.fromstring(data)
    bills = tree.xpath('//div[@class="bulkdata"]/table[@class="styles3"]/tr/td//a/@href')
    bills = bills[1:-1]  # Strip out 'Parent Directory' at the beginning and the .zip archive at the end
    return [str(constants.ROOT_URL + bill) for bill in bills]

#-------------------------------------------------------------------------------------------------------------------------------------------------

def get_bill(session, bill):
    """Attempts to download a bill's XML data from GPO's server.

    Args:
        session: A requests session object.
        bill: The corresponding URL string for the bill.

    Returns:
        A Bill object with relevant information from the XML, or
        None upon failure or if bad args.

    Raises:
        BaseException: Something horribly wrong happened when downloading.
            Generally the exception results from a timeout, which is rare.
    """
    if session and bill:
        try:
            r = session.get(bill, timeout=5)
            if r.status_code == requests.codes.ok:
                return Bill(xmltodict.parse(r.text))
        except BaseException as ex:
            log.warning('Error downloading ' + bill)
            raise ex

    return None
    
#-------------------------------------------------------------------------------------------------------------------------------------------------

def is_relevant(bill):
    """Determines if a given bill meets set criteria for relevance.

    Args:
        bill: A Bill object.

    Returns:
        A boolean value. True => relevant, False => irrelevant or bad arg.
    """
    if bill:
        title = (bill.get_bill_title()).lower()
        summary  = bill.get_bill_summary()
        if summary: 
            summary = summary.lower()
        else: 
            summary = ''

        subjects = list()
        if bill.bill_subjects:
            items = bill.bill_subjects['item']
            for item in items:
                if isinstance(item, OrderedDict):
                    subjects.append(item['name'].lower())
                else:
                    subjects.append(items[item].lower())

        """
        We use ultra-lazy, ultra-greedy keyword matching here. We basically want to find
        any instance of a given KEYWORD within a bill's title, summary, or specified 
        legislative subjects (as determined by Congress). This laziness can result in some
        interesting 'false positives', but these can generally be controlled by setting
        conservative/thoughtful KEYWORDS.
        """
        for keyword in constants.KEYWORDS:
            if (keyword in title) or (keyword in summary) or (keyword in subjects):
               return True

    return False

#-------------------------------------------------------------------------------------------------------------------------------------------------

def download_bills():
    """Downloads bills from GPO's servers.

    Returns:
        A list of relevant bills, which could be empty.

    References:
        Timing from http://stackoverflow.com/a/27780763.
    """
    session = requests.Session()
    relevant_bills = list()

    start = time.time()
    for url in constants.URL_LIST:
        log.info('Connecting {}'.format(url))
        try:
            r = session.get(url, timeout=5)
        except requests.exceptions.RequestException as ex:
            log.warning(ex)
            continue  # No point in doing anything else if there was a connection error

        if r.status_code != requests.codes.ok: 
            r.raise_for_status()
        else:
            bills = get_bill_urls(r.content)
            num_bills = len(bills)
            bill_idx = 0
            for bill in bills:
                bill_idx += 1
                sys.stdout.write('Processing bill %d / %d \r' % (bill_idx, num_bills))
                sys.stdout.flush()
                b = get_bill(session, bill)
                if is_relevant(b): 
                    relevant_bills.append(b)
    end = time.time()

    hours, rem = divmod(end-start, 3600)
    minutes, seconds = divmod(rem, 60)
    log.info('Elapsed {:0>2}:{:0>2}:{:05.2f}'.format(int(hours), int(minutes), seconds))
    log.info('Found {} relevant bills!'.format(len(relevant_bills)))

    return relevant_bills

#-------------------------------------------------------------------------------------------------------------------------------------------------

def get_name(name):
    """Gets a sponsor's name using regex.

    Args:
        name: String with a name to be extracted.

    Returns:
        A dict containing the name's parts (see REGEX and REGEX2).
        None if something went wrong.
    """
    m = re.match(REGEX, name)
    if m: 
        return m.groupdict()
    else:
        m = re.match(REGEX2, name)
        if m:
            return m.groupdict()
    return None

#-------------------------------------------------------------------------------------------------------------------------------------------------

def build_tweet(row):
    """Constructs a tweet string to be sent to Twitter API.

    Args:
        row: Row of data from the database table (tuple).

    Returns:
        A tweet as a string. None if bad arg. A tweet string has
        the following general format:

            Bill <type>. <number>: ["<title>"] ([sponsor,] <introduction date>) | <short URL>

            The sponsor really is the only thing that can be omitted (e.g., bad Twitter handle).
            In exceptionally rare cases, the title may be omitted due to length.
    """
    if not row or not isinstance(row, tuple):
        return None

    bill_type = row[1] + '.'
    bill_number = str(row[2])
    name = get_name(row[3])
    title = row[4]
    short_url = row[6]
    intro_date = row[7]

    """
    We're going to try really hard to give attribution by including the
    sponsor's Twitter handle in the tweet (e.g., @JohnDoe). To do that,
    we're going to reconstruct the sponsor's name as Doe, John and try
    to lazy match with the CONGRESS_TWITTER dict constant. If we can't 
    do that, we'll try to give their position and their last name (e.g.,
    Sen. Doe). If we're too lazy or no match exists, we just give an 
    empty string as the name.
    """
    if name:
        lname = ''
        if 'last_name2' in name:  # Some people have two last names.
            lname = name['last_name'] + ' ' + name['last_name2']
        else:
            lname = name['last_name']

        temp = lname + ', ' + name['first_name']
        if temp in constants.CONGRESS_TWITTER:
            twitter_handle = constants.CONGRESS_TWITTER[temp]
        elif name['position']:
            twitter_handle = name['position'] + ' ' + lname
        else:
            twitter_handle = lname
    else:
        twitter_handle = ''

    tweet_start = 'Bill ' + bill_type + ' ' + bill_number + ': '

    if twitter_handle:
        tweet_end = ' ({0}, {1}) '.format(twitter_handle, intro_date) 
    else: 
        tweet_end = ' ({0}) '.format(intro_date) 
    tweet_end += '| ' + short_url

    """
    Since the bill title is the only thing we can really control in terms of length
    and since bill titles tend to be rather long, we're going to truncate as necessary
    to meet the TWEET_MAX_LENGTH bound. If the tweet is already too long, then we skip
    the title altogether. But that really shouldn't be an issue. (Famous last words.)
    """
    tw_title = ''
    tw_len = len(tweet_start + tweet_end)
    if tw_len < constants.TWEET_MAX_LENGTH: 
        diff = constants.TWEET_MAX_LENGTH - tw_len - 2  # -2 to account for quotation marks ("")
        if len(title) > diff:
            tw_title = '"{}..."'.format(title[:diff-3])  # -3 to account for ellipsis (...)
        else: 
            tw_title = '"{}"'.format(title)

    return str(tweet_start + tw_title + tweet_end)

#-------------------------------------------------------------------------------------------------------------------------------------------------

def main():
    """Main program driver.

    Raises:
        Exception: Critical failure in the beginning. Immediately exit.
            Elsewhere, the exception is reported and execution continues.
        BaseException: Critical failure in the beginning. Immediately exit.
        KeyboardInterrupt: Used to terminate the infinite loop.
    """
    log.info('*** START LOG ***')
    try:
        db = BillDB()
    except Exception as e:
        log.critical(e)
        log.info('*** END LOG ***')
        exit(-1)

    try:
        api = twitter.Api(consumer_key='',
                          consumer_secret='',
                          access_token_key='',
                          access_token_secret='')
    except BaseException as e:
        log.critical(e)
        log.info('*** END LOG ***')
        exit(-1)

    # This downloading should happen only once every 24 hours so GPO's servers don't get slammed.
    try:
        relevant_bills = download_bills()
        for bill in relevant_bills:
            info = bill.bill_to_dict()
            if not db.row_exists(info):
                db.insert_row(info)
    except Exception as e:
        log.warning(e)

    """
    This is probably worthy of criminal prosecution.
    This program is meant to function as a kind of quasi-daemon with minimal
    human interaction. If execution makes it to this infinite loop, we want
    to perform two basic functions:
        1) Try to shorten as many URL as possible, as necessary.
        2) Try to generate and post a tweet about a previously unposted bill.
    We sleep for one hour (3600 seconds) between each iteration, mostly
    so is.gd doesn't get mad at us. But it also keeps Twitter happy by not
    spamming them with hundreds of tweets in the span of a few seconds.
    If something bad happens during URL shortening (i.e., an exception),
    we bail out and immediately kill the program. Not a graceful recovery by
    any stretch of the imagination, but that should be a rare happenstance.
    We also exit the infinite loop after SLEEP_LIMIT (+1) hours. That's meant to 
    correspond roughly to the standard (American) work day. Ideally, change this 
    to a sleep(X hours [until 9am]) and reset times_slept = 0 to act as a 
    quasi-daemon, or kill the process and use a cron job to relaunch the 
    process every (week)day at 9am.
    """
    try:
        times_slept = 0
        log.info('Table size: {} rows'.format(db.get_table_size()))  # Merely for diagnostic purposes.
        while True:
            rows = db.rows_to_shorten()
            try:
                for row in rows:
                    db.gen_short_url(row)
            except Exception as e:
                log.critical(e)
                raise KeyboardInterrupt

            if api.VerifyCredentials():
                row = db.get_row_to_post()
                tw = build_tweet(row)
                if tw:
                    status = api.PostUpdate(tw)
                    if status:
                        log.info('Posted new tweet @ {}'.format(time.asctime(time.localtime(time.time()))))
                        log.info('\t{}'.format(tw))
                        _row = list(row[:-1])  # I apologize for this, but you can blame Python's tuples.
                        _row.append(True)
                        _row = tuple(_row)
                        new = db.tuple_to_dict(_row)
                        db.update_row(new['id'], new)

            log.info('Sleeping for one hour...')
            time.sleep(3600) 
            times_slept += 1
            if times_slept == constants.SLEEP_LIMIT:
                raise KeyboardInterrupt

    except KeyboardInterrupt:
        pass

    finally:
        db.close()

    log.info('*** END LOG ***')
        
#-------------------------------------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    main()

