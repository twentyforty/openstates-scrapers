from pupa.scrape import Jurisdiction, Organization
from .people import PRPersonScraper

# from .committees import PRCommitteeScraper
from .bills import PRBillScraper

settings = dict(SCRAPELIB_TIMEOUT=300)


class PuertoRico(Jurisdiction):
    division_id = "ocd-division/country:us/territory:pr"
    classification = "government"
    name = "Puerto Rico"
    url = "http://www.oslpr.org/"
    scrapers = {
        "people": PRPersonScraper,
        # 'committees': PRCommitteeScraper,
        "bills": PRBillScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2013 - 2016",
            "identifier": "2013-2016",
            "name": "2013-2016 Session",
        },
        {
            "_scraped_name": "2017 - 2020",
            "identifier": "2017-2020",
            "name": "2017-2020 Session",
            "start_date": "2017-01-02",
            "end_date": "2021-01-01",
        },
    ]
    ignored_scraped_sessions = ["Seleccione Cuatrenio"]

    def get_organizations(self):
        legislature_name = "Legislative Assembly of Puerto Rico"
        legislature = Organization(name=legislature_name, classification="legislature")
        yield legislature
        yield Organization("Senate", classification="upper", parent_id=legislature._id)
        yield Organization("House", classification="lower", parent_id=legislature._id)
        yield Organization(name="Office of the Governor", classification="executive")

    def get_session_list(self):
        from openstates.utils import url_xpath

        # this URL should work even for future sessions
        return url_xpath(
            "http://www.tucamarapr.org/dnncamara/web/ActividadLegislativa/TramiteLegislativo.aspx",
            '//select[@id="dnn_ctr1157_ViewWebMeasures_WebMeasures1_ddlTerm"]/option/text()',
        )
