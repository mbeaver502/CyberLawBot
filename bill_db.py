"""
Description:
    This program implements a simple Twitter bot that tweets information about bills in Congress
    that are (in)directly related to cyber issues. This bot uses a MySQL database backend to
    keep track of bills, both posted and unposted (i.e., tweeted and yet to be tweeted, respectively).
    For this initial proof of concept, bill data are scraped from the official US Government
    Publishing Office website. For future versions, it would probably be better to connect to a
    less cumbersome endpoint like ProPublica.

Module:
    This module implements the BillDB class.

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
import requests
from dbconfig               import read_db_config
from mysql.connector        import MySQLConnection, Error
from mysql.connector.cursor import MySQLCursor

class BillDB:
    """Database connection and operations interface.
    
    This class should be used to interface with the database backend.
    Any operations that depend on data storage or retrieval should
        be achieved using this class.

    Attributes:
        dbconfig: Database connection configuration information.
        conn: MySQL database connector.
        cursor: Connector cursor object.
        session: Requests session for connecting to websites (e.g., is.gd).
        isgdquota: Used to rate limit against the is.gd API.
        ISGD_RATE_LIMIT: Constant rate limit set by the is.gd API.
    """
    ISGD_RATE_LIMIT = 200  # 200 requests / hour => 4800 requests / day

#-------------------------------------------------------------------------------------------------------------------------------------------------

    def __init__(self):
        """Inits the class.

        Raises:
            Exception: Failure to establish database connection 
                or a Requests session.
        """
        try:
            self.dbconfig  = read_db_config()
            self.conn      = MySQLConnection(**self.dbconfig)
            self.cursor    = self.conn.cursor(buffered=True)
            self.session   = requests.Session()
            self.isgdquota = 0
        except Exception as e:
            raise Exception(e)

#-------------------------------------------------------------------------------------------------------------------------------------------------

    def close(self):
        """Closes database cursor and connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

#-------------------------------------------------------------------------------------------------------------------------------------------------

    def query_fetchmany(self, query, args):
        """Fetches several rows from database based on query.

        Args:
            query: String with MySQL query.
            args: Tuple of arguments for the query.

        Returns:
            A list of database rows if they were fetched.
            If no rows were fetched, an empty list is returned.

        Raises:
            Exception: Errors in args or in query execution.
        """
        def iter_row(size=10):
            while True:
                rows = self.cursor.fetchmany(size)
                if not rows:
                    break
                for row in rows:
                    yield row

        if not isinstance(self.cursor, MySQLCursor):
            raise Exception('No database connection!')
        if not isinstance(query, basestring):
            raise Exception('Invalid query string!')
        if not isinstance(args, tuple):
            raise Exception('Invalid query args!')

        rows = []
        try:
            self.cursor.execute(query, args)
            rows = [row for row in iter_row()]
        except Error as e:
            raise Exception(e)

        return rows

#-------------------------------------------------------------------------------------------------------------------------------------------------

    def insert_row(self, info):
        """Inserts a new row into the database.

        Args:
            info: Dict containing row information.

        Returns:
            A boolean value. True means the insertion was successful.
            False means the insertion failed.

        Raises:
            Exception: Errors with args or insertion.
        """
        if not isinstance(self.cursor, MySQLCursor):
            raise Exception('No database connection!')
        if not isinstance(info, dict):
            raise Exception('Input must be a dict!')
        if (('type'      not in info) or
           ('number'     not in info) or
           ('sponsor'    not in info) or
           ('title'      not in info) or
           ('full_url'   not in info) or
           ('introduced' not in info)):
            raise Exception('Input missing data!')

        query  = 'insert into bills(type, number, sponsor, title, full_url, short_url, introduced, updated, posted) ' \
                 'values(%s, %s, %s, %s, %s, %s, %s, %s, %s)'
        args   = (
                  info['type'], 
                  info['number'], 
                  info['sponsor'],
                  info['title'],
                  info['full_url'],
                  info['short_url'] if 'short_url' in info else None,
                  info['introduced'],
                  info['updated']   if 'updated'   in info else None,
                  info['posted']    if 'posted'    in info else False
                 )

        result = False
        try:
            self.cursor.execute(query, args)
            if self.cursor.rowcount > 0:
                result = True
                self.conn.commit()
        except Error as e:
            raise Exception(e)

        return result

#-------------------------------------------------------------------------------------------------------------------------------------------------

    def row_exists(self, info):
        """Determines if a row already exists in the database.
        
        Args:
            info: Dict containing relevant row data.

        Returns:
            An integer with the row's `id` (as stored in the dabatase)
            if the row exists. None value if no row found.

        Raises:
            Exception: Error in the args or executing the query.
        """
        if not isinstance(self.cursor, MySQLCursor):
            raise Exception('No database connection!')
        if not isinstance(info, dict):
            raise Exception('Input must be a dict!')
        if (('type'      not in info) or
           ('number'     not in info)):
            raise Exception('Input missing data!')

        query = 'select id, type, number from bills where type=%s and number=%s'
        args  = (info['type'], info['number'])

        row = None
        try:
            self.cursor.execute(query, args)
            row = self.cursor.fetchone()
        except Error as e:
            raise Exception(e)

        return row[0] if row else None

#-------------------------------------------------------------------------------------------------------------------------------------------------

    def update_row(self, row_id, info):
        """Updates a row in the table.

        Args:
            row_id: Integer representing `id` in table row.
            info: Dict containing new data.

        Returns:
            A boolean value. True means successful update.
            False means there was a failure.

        Raises:
            Exception: Error in the args or the query execution.
        """
        if not isinstance(self.cursor, MySQLCursor):
            raise Exception('No database connection!')
        if not isinstance(row_id, int) or row_id < 1:
            raise Exception('Invalid row ID!')
        if not isinstance(info, dict):
            raise Exception('Input must be a dict!')

        query = """
                update bills 
                set type       = %s, 
                    number     = %s, 
                    sponsor    = %s, 
                    title      = %s, 
                    full_url   = %s, 
                    short_url  = %s, 
                    introduced = %s, 
                    updated    = %s, 
                    posted     = %s
                where id = %s
                """

        args = (
                info['type'],
                info['number'],
                info['sponsor'],
                info['title'],
                info['full_url'],
                info['short_url']   if 'short_url' in info else None,
                info['introduced'],
                info['updated']     if 'updated'   in info else None,
                info['posted']      if 'posted'    in info else False,
                row_id
               )

        try:
            self.cursor.execute(query, args)
            if self.cursor.rowcount > 0:
                self.conn.commit()
                return True
        except Error as e:
            raise Exception(e)

        return False

#-------------------------------------------------------------------------------------------------------------------------------------------------

    def has_been_posted(self, row_id):
        """Determines if a given row has `posted` set to True.

        Args:
            row_id: Integer representing `id` of a table row.

        Returns:
            The stored value in `posted` (represented as an integer).

        Raises:
            Exception: Error in the args or the query execution.
        """
        if not isinstance(self.cursor, MySQLCursor):
            raise Exception('No database connection!')
        if not isinstance(row_id, int) or row_id < 1:
            raise Exception('Invalid row ID!')

        query = 'select posted from bills where id=%s'
        args  = (row_id,)

        row = None
        try:
            self.cursor.execute(query, args)
            row = self.cursor.fetchone()
        except Error as e:
            raise Exception(e)

        return row[0] if row else False

#-------------------------------------------------------------------------------------------------------------------------------------------------

    def isgd_shorten(self, url):
        """Shortens a URL using the is.gd API.

        Args:
            url: The URL to shorten (as a string).

        Returns:
            A string of the shortened URL on successful shortening.
            None value on failure.

        Raises:
            Exception: Failure stemming from the is.gd API.
        """
        data = {'format':   'json',
                'url':      url,
                'logstats': 0}
        headers = {'user-agent': 'Mozilla/5.0 (compatible; Python Module)'}
        r = self.session.post('http://is.gd/create.php', params=data, headers=headers)

        if r.status_code == requests.codes.ok:
            d = r.json()
            if 'shorturl' in d:
                self.isgdquota += 1
                return d['shorturl']
            else:
                self.isgdquota = self.ISGD_RATE_LIMIT
                raise Exception('{0}: {1}'.format(d['errorcode'], d['errormessage']))
        return None

#-------------------------------------------------------------------------------------------------------------------------------------------------

    def gen_short_url(self, row=None):
        """Shortens a row's URL.

        Args:
            row: Tuple object representing a table row.

        Raises:
            Exception: Failure to shorten URL.
        """
        if not isinstance(self.cursor, MySQLCursor):
            raise Exception('No database connection!')
        if not isinstance(row, tuple):
            raise Exception('Input must be a tuple!')

        if row and self.isgdquota < self.ISGD_RATE_LIMIT:
            info = self.tuple_to_dict(row)
            short_url = None
            try:
                short_url = self.isgd_shorten(info['full_url'])
                info['short_url'] = short_url
            except Exception as e:
                raise Exception(e)
            finally:
                if short_url: self.update_row(info['id'], info)

#-------------------------------------------------------------------------------------------------------------------------------------------------

    def rows_to_shorten(self):
        """Returns a list of rows whose URLs need to be shortened.

        Returns:
            List of rows (in tuple representation) or empty
            list if no rows found.

        Raises:
            Exception: Failure in query execution.
        """
        query  = 'select * from bills where isnull(short_url)'
        args   = ()
        result = []

        try:
            result = self.query_fetchmany(query, args)
        except Exception as e:
            raise Exception(e)

        return result

#-------------------------------------------------------------------------------------------------------------------------------------------------

    def tuple_to_dict(self, t):
        """Converts a tuple to an appropriate dict."""
        if not isinstance(t, tuple):
            raise Exception('Input must be a tuple!')

        keys = ['id', 
                'type', 
                'number', 
                'sponsor', 
                'title', 
                'full_url', 
                'short_url', 
                'introduced', 
                'updated', 
                'posted']

        return dict(zip(keys, t))

#-------------------------------------------------------------------------------------------------------------------------------------------------

    def get_table_size(self):
        """Calculates number of rows in the database table.

        Returns:
            0 by default. Otherwise, integer representing 
            number of rows in the table.

        Raises:
            Exception: Error in query execution.
        """
        query  = 'select count(*) from bills'
        result = 0

        try:
            self.cursor.execute(query)
            result = self.cursor.fetchone()[0]
        except Error as e:
            raise Exception(e)

        return result

#-------------------------------------------------------------------------------------------------------------------------------------------------

    def get_row_to_post(self):
        """Gets a row to be tweeted out.
        
        Returns:
            A tuple containing row data from the database table.

        Raises:
            Exception: Error in query execution.
        """
        query = 'select * from bills where !isnull(short_url) and posted=0 order by introduced asc'

        row = None
        try:
            self.cursor.execute(query)
            row = self.cursor.fetchone()
        except Error as e:
            raise Exception(e)

        return row 






