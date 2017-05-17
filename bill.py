"""
Description:
    This program implements a simple Twitter bot that tweets information about bills in Congress
    that are (in)directly related to cyber issues. This bot uses a MySQL database backend to
    keep track of bills, both posted and unposted (i.e., tweeted and yet to be tweeted, respectively).
    For this initial proof of concept, bill data are scraped from the official US Government
    Publishing Office website. For future versions, it would probably be better to connect to a
    less cumbersome endpoint like ProPublica.

Module:
    This module implements the Bill class.

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
import constants

class Bill:
    """Object representing a bill in Congress.
    
    This class acts as a convenient container for all relevant
    information for the database. Bills to be stored in the
    database should first be processed through this class (or,
    more accurately, an instance of this class.)

    Attributes:
        bill: Essentially the root from the XML data.
        bill_sponsors: The XML containing the sponsors.
        bill_cosponsors: Same as sponsors, but cosponsors if they exist. Not used.
        bill_type: The type of bill (e.g., S or HR).
        bill_number: The bill's number (e.g., 999).
        bill_titles: The XML containing the bill's titles (sometimes more than one).
        bill_intro: The bill's introduction date (YYYY-MM-DD).
        bill_actions: The XML containing the actions on the bill by Congress. Not used.
        bill_committees: The XML containing the Congressional committees affected. Not used.
        # bill_subject: The bill's primary subject, as defined by Congress. Not used.
        bill_subjects: The bill's legislative subjects, as defined by Congress.
        bill_policy_area: The bill's policy area, as defined by Congress. Not used.
        bill_url: The bill's URL on www.congress.gov. Constructed by the class on init.
    """
#-------------------------------------------------------------------------------------------------------------------------------------------------

    def __init__(self, doc):
        """Inits the class.
        
        Args:
            doc: Dict containing XML information for the bill.
        """
        self.bill          = doc['billStatus']['bill']
        self.bill_sponsors = self.bill['sponsors']['item']
        if self.bill['cosponsors'] is not None:
            self.bill_cosponsors = self.bill['cosponsors']['item']
        self.bill_type        = self.bill['billType']
        self.bill_number      = self.bill['billNumber']
        self.bill_titles      = self.bill['titles']['item']
        self.bill_intro       = self.bill['introducedDate']
        self.bill_actions     = self.bill['actions']
        self.bill_summaries   = self.bill['summaries']['billSummaries']
        self.bill_committees  = self.bill['committees']
        #self.bill_subject     = self.bill['primarySubject']
        self.bill_subjects    = self.bill['subjects']['billSubjects']['legislativeSubjects']
        self.bill_policy_area = self.bill['policyArea']
        self.bill_url         = self._build_url()

#-------------------------------------------------------------------------------------------------------------------------------------------------

    def __repr__(self):
        """Representation for printing purposes.

        Returns:
            A string that can be printed:
                <sponsor> - <type>. <number> - "<title>" (introduced <date>)
        """
        if not isinstance(self.bill_sponsors, list):
            b_sponsor = self.bill_sponsors['fullName']
        else:
            b_sponsor = self.bill_sponsors[0]['fullName']

        b_title = self.get_bill_title()

        return b_sponsor        + ' - '  + \
               self.bill_type   + '. '   + \
               self.bill_number + ' - "' + \
               b_title          + '" '   + \
               '(introduced '   + \
               self.bill_intro  + ')'

#-------------------------------------------------------------------------------------------------------------------------------------------------

    def _build_url(self):
        """Constructs the www.congress.gov URL for a bill."""
        _url = constants.CONGRESS_URL

        if constants.CONGRESS[-1] == '1': 
            _url += constants.CONGRESS + 'st'
        elif constants.CONGRESS[-1] == '2': 
            _url += constants.CONGRESS + 'nd'
        elif constants.CONGRESS[-1] == '3': 
            _url += constants.CONGRESS + 'rd'
        else:                     
            _url += constants.CONGRESS + 'th'
        _url += '-congress/'

        _url += constants.BILL_TYPES_PATH[self.bill_type] + '/'
        _url += str(self.bill_number)
        return _url

#-------------------------------------------------------------------------------------------------------------------------------------------------

    def get_bill_summary(self):
        """Gets a bill's summary data (from XML).

        Returns:
            A summary as a string. None if no summaries found.
        """
        if self.bill_summaries:
            if not isinstance(self.bill_summaries, list):
                if not isinstance(self.bill_summaries['item'], list):
                    return self.bill_summaries['item']['text']
                return self.bill_summaries['item'][-1]['text']
        return None

#-------------------------------------------------------------------------------------------------------------------------------------------------

    def get_bill_title(self):
        """Gets the bill's title from the XML."""
        if not isinstance(self.bill_titles, list): 
            return self.bill_titles['title']
        else: 
            return self.bill_titles[0]['title']

#-------------------------------------------------------------------------------------------------------------------------------------------------

    def bill_to_dict(self):
        """Converts a Bill object to a dict.

        Returns:
            A dict representation of a Bill object.
        """
        result = {
                  'type': self.bill_type,
                  'number': self.bill_number,
                  'sponsor': None,
                  'title': self.get_bill_title(),
                  'full_url': self.bill_url,
                  'short_url': None,
                  'introduced': self.bill_intro,
                  'updated': None,
                  'posted': False
                 }

        if not isinstance(self.bill_sponsors, list):
            result['sponsor'] = self.bill_sponsors['fullName']
        else:
            result['sponsor'] = self.bill_sponsors[0]['fullName']

        return result            