"""
Description:
    This program implements a simple Twitter bot that tweets information about bills in Congress
    that are (in)directly related to cyber issues. This bot uses a MySQL database backend to
    keep track of bills, both posted and unposted (i.e., tweeted and yet to be tweeted, respectively).
    For this initial proof of concept, bill data are scraped from the official US Government
    Publishing Office website. For future versions, it would probably be better to connect to a
    less cumbersome endpoint like ProPublica.

Module:
    This module implements the database connection configuration functionality.

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
import logging as log

# There's an issue where CP will output Py3 deprecation warnings, so avoid them.
try:
    import ConfigParser as configparser
except ImportError:
    import configparser
    log.info('Using configparser instead of ConfigParser!')

def read_db_config(filename='config.ini', section='mysql'):
    """Reads database configuration from file.

    Args:
        filename: The filename as a string.
        section: The INI section with the config information as a string.

    Returns:
        A dict containing database configuration information.

    Raises:
        Exception: Failure to find file or to load all config information.
    """
    parser = configparser.ConfigParser()
    try:
        parser.read(filename)
    except:
        raise Exception('{} not found!'.format(filename))

    db = {}
    if parser.has_section(section):
        items = parser.items(section)
        for item in items:
            db[item[0]] = item[1]
    else:
        raise Exception('{0} not found in file {1}'.format(section, filename))

    return db
