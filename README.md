Cyber Law Bot (see me on Twitter: [@CyberLawBot](https://twitter.com/CyberLawBot)!)

A Python 2.7+ bot that tweets bills in Congress (in)directly related to cyber issues.

By [J. Michael Beaver](https://www.twitter.com/OldDiogenes)

# Introduction
This program implements a simple Twitter bot that tweets information about bills in Congress that are (in)directly related to cyber issues. This bot uses a MySQL database backend to keep track of bills, both posted and unposted (i.e., tweeted and yet to be tweeted, respectively). For this initial proof of concept, bill data are scraped from the official [US Government Publishing Office website](https://www.gpo.gov/fdsys/bulkdata/BILLSTATUS). For future versions, it would probably be better to connect to a less cumbersome endpoint like ProPublica.

# How It Works
## Basic Idea
1. Attempt to establish a connection to its local MySQL database. If connection fails, there's a hard termination.
2. Attempt to establish a connection to Twitter via its API. If connection fails, there's a hard termination.
3. Scrape the US GPO website and saves relevant bills into the database (see [bill_db.py](bill_db.py) for more information).
4. Attempt to shorten as many URLs as possible using the [is.gd API](https://is.gd/apishorteningreference.php).
5. Choose a bill and generate a tweet for it.
6. Post the tweet and update the database.
7. Sleep for an hour.
8. Goto Step 4.

Steps 4-8 are in an infinite loop. Currently that loop breaks (raising `KeyboardInterrupt`) after `SLEEP_LIMIT+1` loops (see [constants.py](constants.py)).

The bot is meant to operate as a kind of quasi-daemon with minimal or no human interaction. Ideally, after looping `SLEEP_LIMIT+1` times, the script would exit and be reinvoked at ~9am the following day. Alternatively, you could update it to sleep for X hours until ~9am the following day.

## Run the Code
Open a terminal and run:
```
$ python engine.py
```

All information is logged to [cyber_law_bot.log](cyber_law_bot.log).

## Database Structure
The database is assumed to be 'cyber_law_bot'. You can change that in [confing.ini](config.ini).
There should be a table in the database called 'bills'. Again, you can change that in [confing.ini](config.ini).

The table should have the following format:
```
+------------+------------------+------+-----+---------+----------------+
| Field      | Type             | Null | Key | Default | Extra          |
+------------+------------------+------+-----+---------+----------------+
| id         | int(10) unsigned | NO   | PRI | NULL    | auto_increment | <-- Unique id for reach row
| type       | varchar(10)      | NO   |     | NULL    |                | <-- Bill type (e.g., 'S', 'HR', etc.)
| number     | int(11)          | NO   |     | NULL    |                | <-- Bill number (e.g., 999)
| sponsor    | varchar(256)     | NO   |     | NULL    |                | <-- Bill sponsor (e.g., Sen. Smith, John [D-AL])
| title      | varchar(2048)    | NO   |     | NULL    |                | <-- Bill title (e.g., "An Act to XYZ")
| full_url   | varchar(2048)    | NO   |     | NULL    |                | <-- Full www.congress.gov URL
| short_url  | varchar(1024)    | YES  |     | NULL    |                | <-- Shortened is.gd URL
| introduced | date             | YES  |     | NULL    |                | <-- Introduction date (YYYY-MM-DD)
| updated    | date             | YES  |     | NULL    |                | <-- Last update date (_not_ used)
| posted     | tinyint(1)       | NO   |     | 0       |                | <-- Boolean (0 = False, 1 = True)
+------------+------------------+------+-----+---------+----------------+
```

## Known Issues
* The exception handling is atrocious. I apologize.
    * Some exceptions can lead to hard, non-graceful termination.
* The [engine](engine.py) relies heavily on scraping the [US GPO Bulk Data](https://github.com/usgpo/bill-status/blob/master/BILLSTATUS-XML_User_User-Guide.md) pages. That can be problematic for a few reasons:
    * Scraping can be slow. Granted, it takes ~11 minutes now for ~4500 bills, but imagine if Congress went into overdrive!
    * If you start and stop execution, you can slam GPO's servers. That's not very nice.
    * There's probably a better endpoint out there that more consistently gathers these data and collects them in nice formats (e.g., JSON). [ProPublica](https://projects.propublica.org/api-docs/congress-api/endpoints/) may be one source.
* There are some hardcoded constants (see [constants.py](constants.py)) that would need to be updated periodically.
    * For example: `CONGRESS = '115'` <-- 115th Congress, but next year will be 116th Congress
    * If some of these constants aren't updated, things will break.
* It would be nice to post a tweet when a bill is _updated_ (i.e., new action taken). That was the intent behind the `updated` field in the database table.

# Documentation
All documentation is in the modules or in the `doc` directory. Use [pydoc](https://docs.python.org/2/library/pydoc.html) to see the documentation:

```
$ pydoc <module>
```

# Libraries
This program makes use of the following libraries.
* lxml
    * Stephan Richter / Infrae
    * BSD License
    * Web: [http://lxml.de/](http://lxml.de/)

* xmltodict        
    * Martin Blech & contribs.    
    * MIT License
    * Web: [Github](https://github.com/martinblech/xmltodict)

* python-twitter    
    * Mike Taylor ('bear') & contribs.
    * Apache License 2.0
    * Web: [Github](https://github.com/bear/python-twitter)

* requests
    * Kenneth Reitz
    * Apache License 2.0
    * Web: [http://docs.python-requests.org/en/master](http://docs.python-requests.org/en/master)

* MySQL Connector
    * Oracle & affiliates
    * Misc. License
    * Web: [https://dev.mysql.com/doc/connector-python/en/](https://dev.mysql.com/doc/connector-python/en/)


# License:
```
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
```

# References 
* [US GPO Manual](https://www.gpo.gov/fdsys/bulkdata/BILLSTATUS/resources/BILLSTATUS-XML_User-Guide-v1.pdf)
* [US GPO Github](https://github.com/usgpo/bill-status)
* [ProPublica](https://projects.propublica.org/api-docs/congress-api/endpoints/)
* [python-twitter](https://github.com/bear/python-twitter)
* [xmltodict](https://github.com/martinblech/xmltodict)
* [requests](http://docs.python-requests.org/en/master)
* [MySQL Connector](https://dev.mysql.com/doc/connector-python/en/)
* [lxml](http://lxml.de/)
* [Python Database API Spec](https://www.python.org/dev/peps/pep-0249)
* [is.gd API](https://is.gd/apishorteningreference.php)
* [MySQL Commands](https://www.pantz.org/software/mysql/mysqlcommands.html)
* [MySQL with Python Tutorial](http://www.mysqltutorial.org/getting-started-mysql-python-connector/)
* [ConfigParser Issue](https://bitbucket.org/ned/coveragepy/commits/f8e9d62f1412)
* [GovTrack API](https://www.govtrack.us/api/v2/role)
* [Apache License](https://choosealicense.com/licenses/apache-2.0/)