import os
import re
import pytz
import operator
import itertools
import datetime
import lxml
from utils import LXMLMixin
from openstates.scrape import Scraper, Bill, VoteEvent
from .actions import CACategorizer

SPONSOR_TYPES = {
    "LEAD_AUTHOR": "author",
    "COAUTHOR": "coauthor",
    "PRINCIPAL_COAUTHOR": "principal coauthor",
}


# Committee codes used in action chamber text.
committee_data_upper = [
    (
        "Standing Committee on Governance and Finance",
        "CS73",
        ["GOV. & F.", "Gov. & F."],
    ),
    (
        "Standing Committee on Energy, Utilities and Communications",
        "CS71",
        ["E., U., & C."],
    ),
    ("Standing Committee on Education", "CS44", ["ED."]),
    ("Standing Committee on Appropriations", "CS61", ["APPR."]),
    ("Standing Committee on Labor and Industrial Relations", "CS51", ["L. & I.R."]),
    (
        "Standing Committee on Elections and Constitutional Amendments",
        "CS45",
        ["E. & C.A."],
    ),
    ("Standing Committee on Environmental Quality", "CS64", ["E.Q."]),
    ("Standing Committee on Natural Resources And Water", "CS55", ["N.R. & W."]),
    ("Standing Committee on Public Employment and Retirement", "CS56", ["P.E. & R."]),
    ("Standing Committee on Governmental Organization", "CS48", ["G.O."]),
    ("Standing Committee on Insurance", "CS70", ["INS."]),
    ("Standing Committee on Public Safety", "CS72", ["PUB. S."]),
    ("Standing Committee on Judiciary", "CS53", ["JUD."]),
    ("Standing Committee on Health", "CS60", ["HEALTH"]),
    ("Standing Committee on Transportation and Housing", "CS59", ["T. & H."]),
    (
        "Standing Committee on Business, Professions and Economic Development",
        "CS42",
        ["B., P. & E.D."],
    ),
    ("Standing Committee on Agriculture", "CS40", ["AGRI."]),
    ("Standing Committee on Banking and Financial Institutions", "CS69", ["B. & F.I."]),
    ("Standing Committee on Veterans Affairs", "CS66", ["V.A."]),
    ("Standing Committee on Budget and Fiscal Review", "CS62", ["B. & F.R."]),
    ("Standing Committee on Human Services", "CS74", ["HUM. S.", "HUMAN S."]),
    ("Standing Committee on Rules", "CS58", ["RLS."]),
    (
        "Extraordinary Committee on Transportation and Infrastructure Development",
        "CS67",
        ["T. & I.D."],
    ),
]

committee_data_lower = [
    ("Standing Committee on Rules", "CX20", ["RLS."]),
    ("Standing Committee on Revenue and Taxation", "CX19", ["REV. & TAX"]),
    ("Standing Committee on Natural Resources", "CX16", ["NAT. RES."]),
    ("Standing Committee on Appropriations", "CX25", ["APPR."]),
    ("Standing Committee on Insurance", "CX28", ["INS."]),
    ("Standing Committee on Utilities and Commerce", "CX23", ["U. & C."]),
    ("Standing Committee on Education", "CX03", ["ED."]),
    ("Standing Committee on Public Safety", "CX18", ["PUB. S."]),
    ("Standing Committee on Elections and Redistricting", "CX04", ["E. & R."]),
    ("Standing Committee on Judiciary", "CX13", ["JUD."]),
    ("Standing Committee on Higher Education", "CX09", ["HIGHER ED."]),
    ("Standing Committee on Health", "CX08", ["HEALTH"]),
    ("Standing Committee on Human Services", "CX11", ["HUM. S.", "HUMAN S."]),
    (
        "Standing Committee on Arts, Entertainment, Sports, Tourism, and Internet Media",
        "CX37",
        ["A., E., S., T., & I.M."],
    ),
    ("Standing Committee on Transportation", "CX22", ["TRANS."]),
    (
        "Standing Committee on Business, Professions and Consumer Protection",
        "CX33",
        ["B., P., & C.P.", "B. & P."],
    ),
    ("Standing Committee on Water, Parks and Wildlife", "CX24", ["W., P., & W."]),
    ("Standing Committee on Local Government", "CX15", ["L. GOV.", "L. Gov."]),
    ("Standing Committee on Aging and Long Term Care", "CX31", ["AGING & L.T.C."]),
    ("Standing Committee on Labor and Employment", "CX14", ["L. & E."]),
    ("Standing Committee on Governmental Organization", "CX07", ["G.O."]),
    (
        "Standing Committee on Public Employees, Retirement and Social Security",
        "CX17",
        ["P.E., R., & S.S."],
    ),
    ("Standing Committee on Veterans Affairs", "CX38", ["V.A."]),
    ("Standing Committee on Housing and Community Development", "CX10", ["H. & C.D."]),
    (
        "Standing Committee on Environmental Safety and Toxic Materials",
        "CX05",
        ["E.S. & T.M."],
    ),
    ("Standing Committee on Agriculture", "CX01", ["AGRI."]),
    ("Standing Committee on Banking and Finance", "CX27", ["B. & F."]),
    (
        "Standing Committee on Jobs, Economic Development and the Economy",
        "CX34",
        ["J., E.D., & E."],
    ),
    (
        "Standing Committee on Accountability and Administrative Review",
        "CX02",
        ["A. & A.R."],
    ),
    ("Standing Committee on Budget", "CX29", ["BUDGET"]),
    ("Standing Committee on Privacy and Consumer Protection", "CX32", ["P. & C.P."]),
    ("Extraordinary Committee on Finance", "CX35", ["FINANCE"]),
    (
        "Extraordinary Committee on Public Health and Developmental Services",
        "CX30",
        ["P.H. & D.S."],
    ),
]

committee_data_both = committee_data_upper + committee_data_lower


def slugify(s):
    return re.sub(r"[ ,.]", "", s)


def get_committee_code_data():
    return dict((t[1], t[0]) for t in committee_data_both)


def get_committee_abbr_data():
    _committee_abbr_to_name_upper = {}
    _committee_abbr_to_name_lower = {}
    for name, code, abbrs in committee_data_upper:
        for abbr in abbrs:
            _committee_abbr_to_name_upper[slugify(abbr).lower()] = name

    for name, code, abbrs in committee_data_lower:
        for abbr in abbrs:
            _committee_abbr_to_name_lower[slugify(abbr).lower()] = name

    committee_data = {
        "upper": _committee_abbr_to_name_upper,
        "lower": _committee_abbr_to_name_lower,
    }

    return committee_data


def get_committee_name_regex():
    # Builds a list of all committee abbreviations.
    _committee_abbrs = map(operator.itemgetter(2), committee_data_both)
    _committee_abbrs = itertools.chain.from_iterable(_committee_abbrs)
    _committee_abbrs = sorted(_committee_abbrs, reverse=True, key=len)

    _committee_abbr_regex = [
        "%s" % r"[\s,]*".join(abbr.replace(",", "").split(" "))
        for abbr in _committee_abbrs
    ]
    _committee_abbr_regex = re.compile("(%s)" % "|".join(_committee_abbr_regex))

    return _committee_abbr_regex


class CABillScraper(Scraper, LXMLMixin):
    categorizer = CACategorizer()

    _tz = pytz.timezone("US/Pacific")

    base_url = 'https://leginfo.legislature.ca.gov/faces'


    def clean_id(self, s):
        s = s.replace('-', ' ')
        return s

    def clean_title(self, s):
        # replace smart quote characters
        s = s.replace("\xe2\u20ac\u201c", "-")

        # Cesar Chavez e
        s = s.replace("\xc3\xa9", "\u00E9")
        # Cesar Chavez a
        s = s.replace("\xc3\xa1", "\u00E1")
        s = s.replace("\xe2\u20ac\u201c", "\u2013")

        s = re.sub(r"[\u2018\u2019]", "'", s)
        s = re.sub(r"[\u201C\u201D]", '"', s)
        s = re.sub("\u00e2\u20ac\u2122", "'", s)
        s = re.sub(r"\xe2\u20ac\u02dc", "'", s)
        return s


    def get_bill_type(self, bill_id):
        bill_types = {
            "lower": {
                "AB": "bill",
                "ACA": "constitutional amendment",
                "ACR": "concurrent resolution",
                "AJR": "joint resolution",
                "HR": "resolution",
            },
            "upper": {
                "SB": "bill",
                "SCA": "constitutional amendment",
                "SCR": "concurrent resolution",
                "SJR": "joint resolution",
                "SR": "resolution",
            },
        }

        for chamber, type_list in bill_types.items():
            for abbr, bill_type in type_list.items():
                if bill_id.upper().startswith(abbr):
                    return (chamber, bill_type)
       
    def committee_code_to_name(
        self, code, committee_code_to_name=get_committee_code_data()
    ):
        """Need to map committee codes to names.
        """
        return committee_code_to_name[code]

    def committee_abbr_to_name(
        self,
        chamber,
        abbr,
        committee_abbr_to_name=get_committee_abbr_data(),
        slugify=slugify,
    ):
        abbr = slugify(abbr).lower()
        try:
            return committee_abbr_to_name[chamber][slugify(abbr)]
        except KeyError:
            try:
                other_chamber = {"upper": "lower", "lower": "upper"}[chamber]
            except KeyError:
                raise KeyError
            return committee_abbr_to_name[other_chamber][slugify(abbr)]

    def scrape(self, chamber=None, session=None):
        if session is None:
            session = self.jurisdiction.legislative_sessions[-1]["identifier"]
            self.info("no session specified, using %s", session)
        chambers = [chamber] if chamber is not None else ["upper", "lower"]

        bill_types = {
            "lower": {
                "AB": "bill",
                "ACA": "constitutional amendment",
                "ACR": "concurrent resolution",
                "AJR": "joint resolution",
                "HR": "resolution",
            },
            "upper": {
                "SB": "bill",
                "SCA": "constitutional amendment",
                "SCR": "concurrent resolution",
                "SJR": "joint resolution",
                "SR": "resolution",
            },
        }

        # for chamber in chambers:
            # for abbr, type_ in bill_types[chamber].items():
            #     yield from self.scrape_bill_type(chamber, session, type_, abbr)

        # todo: be nice to break this up by type, but adv search results paginate
        url = 'http://leginfo.legislature.ca.gov/faces/billSearchClient.xhtml?session_year={}&house=Both&author=All&lawCode=All'.format(session)
        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        for row in page.xpath('//table[@id="bill_results"]/tbody/tr/td[1]/a/@href'):
            yield from self.scrape_bill(row, session)

    def scrape_bill(self, url, session):
        # CA links to the text first, we want the status page first:
        url = url.replace('billNavClient', 'billStatusClient')
        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        bill_id = page.xpath('//span[@id="measureNum"]/text()')[0]
        bill_id = self.clean_id(bill_id)

        chamber, bill_type = self.get_bill_type(bill_id)

        title = page.xpath('//div[@id="bill_title"]/h2/text()')[1].strip()

        bill = Bill(
            bill_id,
            title=title,
            chamber=chamber,
            classification=bill_type,
            legislative_session=session,
        )

        internal_id = page.xpath('//input[@id="bid"]/@value')[0]

        abstract = page.xpath('//span[@id="statusTitle"]/text()')[0].strip()
        bill.add_abstract(abstract, "summary")

        self.scrape_actions(bill, chamber, internal_id)
        self.scrape_sponsors(bill, page)
        self.scrape_cosponsors(bill, page)
        self.scrape_versions(bill, internal_id, page)
        yield from self.scrape_votes(bill, internal_id)

        thirtyfirst = page.xpath('//span[@id="day"]/text()')[0].strip()
        bill.extras['thirty_first_day'] = thirtyfirst

        bill.add_source(url)

        yield bill

    def scrape_actions(self, bill, chamber, internal_id):
        url = '{}/billHistoryClient.xhtml?bill_id={}'.format(self.base_url, internal_id)
        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)

        current_chamber = chamber
        for row in page.xpath('//table[@id="billhistory"]/tbody/tr'):
            action_date = row.xpath('td[1]/text()')[0].strip()
            action_text = row.xpath('td[2]/text()')[0].strip()

            when = datetime.datetime.strptime(action_date, "%m/%d/%y")
            when = self._tz.localize(when)

            if 'in senate' in action_text.lower():
                current_chamber = 'upper'
            elif 'in assembly' in action_text.lower():
                current_chamber = 'lower'
            elif 'by the governor' in action_text.lower():
                current_chamber = 'executive'

            bill.add_action(
                action_text,
                chamber=current_chamber,
                date=when,
                classification=self.categorizer.categorize(action_text)['classification']
            )


    def scrape_sponsors(self, bill, page):
        sponsors_line = page.xpath('//span[@id="leadAuthors"]/text()')[0].strip()
        if sponsors_line == '-':
            return
        
        sponsors = sponsors_line.split(',')
        for sponsor in sponsors:
            self.add_sponsor(bill, sponsor, primary=True)
    
    def scrape_cosponsors(self, bill, page):
        xpaths = [
            '//span[@id="leadAuthors"]/text()',
            '//span[@id="coAuthors"]/text()'
        ]

        for xpath in xpaths:
            sponsors_line = page.xpath('//span[@id="leadAuthors"]/text()')[0].strip()
            if sponsors_line == '-':
                continue  

            sponsors = sponsors_line.split(',')
            for sponsor in sponsors:
                self.add_sponsor(bill, sponsor, primary=False)

        # if both principal coauthors and coauthors are -, just return
        return

    def scrape_versions(self, bill, internal_id, page):
        for row in page.xpath('//select[@id="version"]/option'):
            version_id = row.xpath('@value')[0]
            version_name = row.xpath('text()')[0]

            # note, there's no way to GET a text/html url for the specific version,
            # you have to do a POST request w/ their form.
            
            # the pdf url is actually a JS redirect that submits a form.
            # so if you want to download the files programatically you'll have to write your own logic.

            # see http://leginfo.legislature.ca.gov/faces/feedbackDetail.xhtml?primaryFeedbackId=prim1603215435573

            pdf_url = '{}/billPdf.xhtml?bill_id={}&version={}'

            bill.add_version_link(
                version_name,
                pdf_url.format(self.base_url, internal_id, version_id),
                media_type="application/pdf"
            )

    def scrape_votes(self, bill, internal_id):
        url = '{}/billVotesClient.xhtml?bill_id={}'.format(self.base_url, internal_id)
        page = self.get(url).content
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        
        for row in page.xpath('//div[@class="status"]'):
            vote_date = row.xpath('.//span[contains(@id, ":voteDate")]/text()')[0].strip()
            vote_date = datetime.datetime.strptime(vote_date, "%m/%d/%y")
            vote_date = self._tz.localize(vote_date)
            
            
            vote_res = row.xpath('.//span[contains(@id, ":result")]/text()')[0].strip()
            vote_loc = row.xpath('.//span[contains(@id, ":location")]/text()')[0].strip()

            vote_chamber = 'lower' if ('assembly' in vote_loc.lower() or 'asm' in vote_loc.lower()) else 'upper'

            vote_motion = row.xpath('.//span[contains(@id, ":motion")]/text()')[0].strip()

            # lxml doesn't support ends-with here instead of contains, so be cautious of
            # :ayes vs :ayesLeg
            vote_yes = int(row.xpath('.//span[contains(@id, ":ayes")]/text()')[0].strip())
            vote_no = int(row.xpath('.//span[contains(@id, ":noes")]/text()')[0].strip())
            vote_other = int(row.xpath('.//span[contains(@id, ":nvr")]/text()')[0].strip())

            vote = VoteEvent(
                chamber=vote_chamber,
                start_date=vote_date,
                motion_text=vote_motion,
                result="pass" if 'pass' in vote_res.lower() else "fail",
                classification="passage",
                bill=bill,
            )
            vote.set_count("yes", vote_yes)
            vote.set_count("no", vote_no)
            vote.set_count("other", vote_other)
            vote.add_source(url)

            ayes = row.xpath('.//span[contains(@id, ":ayesLeg")]/text()')
            self.parse_vote_row(vote, ayes, 'yes')
            noes = row.xpath('.//span[contains(@id, ":noesLeg")]/text()')
            self.parse_vote_row(vote, noes, 'no')
            nots = row.xpath('.//span[contains(@id, ":nvrLeg")]/text()')
            self.parse_vote_row(vote, nots, 'not voting')

            yield vote

    def parse_vote_row(self, vote, row, vote_val):
        if row:
            rolls = row[0].strip()
            if rolls != '':
                for rollcall in rolls.split(','):
                    vote.vote(vote_val, rollcall.strip())


    def add_sponsor(self, bill, sponsor, primary=False):
        chamber = None
        sponsor = sponsor.strip()

        # TODO: can we have a from org in sponsor?
        if sponsor.endswith('(A)'):
            chamber = 'lower'
            sponsor = sponsor.replace('(A)', '').strip()
        elif sponsor.endswith('(S)'):
            chamber = 'upper'
            sponsor = sponsor.replace('(A)', '').strip()

        bill.add_sponsorship(
            sponsor,
            entity_type="person",
            classification="primary" if primary else "cosponsor",
            primary=primary,
        )