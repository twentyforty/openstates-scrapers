import datetime as dt
import lxml
import re

from openstates.scrape import Scraper, Event
from openstates.exceptions import EmptyScrape

import pytz

urls = {
    "upper": "https://www.ilga.gov/senate/schedules/weeklyhearings.asp",
    "lower": "https://www.ilga.gov/house/schedules/weeklyhearings.asp",
}

chamber_names = {
    "upper": "Senate",
    "lower": "House",
}

# Used to extract parts of bill id
bill_re = re.compile(r"(\w+?)\s*0*(\d+)")

# Used to remove prefixes from committee name
ctty_name_re = re.compile(
    r"(hearing notice for )?(senate )?(house )?(.*)", flags=re.IGNORECASE
)


class IlEventScraper(Scraper):
    localize = pytz.timezone("America/Chicago").localize

    def scrape_page(self, url, chamber):
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        ctty_name = doc.xpath("//span[@class='heading']")[0].text_content()

        # Remove prefixes from the name like "Hearing notice for"
        ctty_name = ctty_name_re.match(ctty_name).group(4)

        tables = doc.xpath("//table[@cellpadding='3']")
        if not tables:
            self.warning(f"Empty hearing data for {url}")
            return False, False
        info = tables[0]
        rows = info.xpath(".//tr")
        metainf = {}
        for row in rows:
            tds = row.xpath(".//td")
            key = tds[0].text_content().strip()
            value = tds[1].text_content().strip()
            metainf[key] = value

        where = metainf["Location:"]

        description = f"{chamber} {ctty_name}"
        # Remove committee suffix from names
        committee_suffix = " Committee"
        if description.endswith(committee_suffix):
            description = description[: -len(committee_suffix)]
        # Add spacing around hyphens
        if "-" in description:
            descr_parts = description.split("-")
            description = " - ".join([x.strip() for x in description])

        datetime = metainf["Scheduled Date:"]
        datetime = re.sub(r"\s+", " ", datetime)
        repl = {"AM": " AM", "PM": " PM"}  # Space shim.
        for r in repl:
            datetime = datetime.replace(r, repl[r])
        datetime = self.localize(dt.datetime.strptime(datetime, "%b %d, %Y %I:%M %p"))

        event_name = f"{description}#{where}#{datetime}"
        event = Event(description, start_date=datetime, location_name=where)
        event.dedupe_key = event_name
        event.add_source(url)

        event.add_participant(ctty_name, "organization")

        bills = tables[1]
        for bill in bills.xpath(".//tr")[1:]:
            tds = bill.xpath(".//td")
            if len(tds) < 4:
                continue
            # First, let's get the bill ID:
            bill_id = tds[0].text_content()

            # Apply correct spacing to bill id
            (alpha, num) = bill_re.match(bill_id).groups()
            bill_id = f"{alpha} {num}"

            agenda_item = event.add_agenda_item(bill_id)
            agenda_item.add_bill(bill_id)

        return event, event_name

    def scrape(self):
        no_scheduled_ct = 0

        for chamber in ("upper", "lower"):
            try:
                url = urls[chamber]
            except KeyError:
                return  # Not for us.
            html = self.get(url).text
            doc = lxml.html.fromstring(html)
            doc.make_links_absolute(url)

            if doc.xpath('//div[contains(text(), "No hearings currently scheduled")]'):
                self.info(f"No hearings in {chamber}")
                no_scheduled_ct += 1
                continue

            tables = doc.xpath("//table[@width='550']")
            events = set()
            for table in tables:
                meetings = table.xpath(".//a")
                for meeting in meetings:
                    event, name = self.scrape_page(
                        meeting.attrib["href"], chamber_names[chamber]
                    )
                    if event and name:
                        if name in events:
                            self.warning(f"Duplicate event {name}")
                            continue
                        events.add(name)
                        yield event

        if no_scheduled_ct == 2:
            raise EmptyScrape
