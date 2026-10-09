import json
import re
import shlex
from datetime import datetime

import requests
from bs4 import BeautifulSoup


class MailChimpAPIError(Exception):
    pass


class MailChimpStatusError(MailChimpAPIError):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message

        super().__init__(
            f"Mailchimp gaf status {status_code}: {message}"
        )


class MailChimpClient:
    REPORTS_URL = (
        "https://us1.admin.mailchimp.com/"
        "reports/get-campaign-data"
    )

    ADVANCED_REPORT_URL = (
        "https://us1.admin.mailchimp.com/"
        "i/reports/advanced/"
    )

    POLL_POPUP_URL = (
        "https://us1.admin.mailchimp.com/"
        "reports/poll-popup-data"
    )

    PAGE_DATA_URL = (
        "https://us1.admin.mailchimp.com/"
        "autolyse/index.php/twirp/"
        "mailchimp.appshell.v1.PageDataService/"
        "GetPageData"
    )

    def get_page_data(self):
        payload = {
            "appConfig": {},
            "ixpFlagsCachedAt": 1791491323752,
        }

        headers = {
            "content-type": "application/json",
            "accept": "application/json",
            "origin": "https://us1.admin.mailchimp.com",
            "referer": "https://us1.admin.mailchimp.com/",
        }

        response = self.session.post(
            self.PAGE_DATA_URL,
            json=payload,
            headers=headers,
            timeout=30,
            allow_redirects=False,
        )

        return {
            "status_code": response.status_code,
            "content_type": response.headers.get(
                "content-type"
            ),
            "location": response.headers.get(
                "location"
            ),
            "text": response.text[:1000],
        }

    def __init__(self, cookie):
        self.session = requests.Session()

        self.session.headers.update(
            {
                "accept": (
                    "text/html,application/xhtml+xml,"
                    "application/json;q=0.9,*/*;q=0.8"
                ),
                "user-agent": (
                    "Mozilla/5.0 "
                    "(Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/140.0 Safari/537.36"
                ),
                "cookie": cookie,
            }
        )

    def _check_response(self, response):
        if response.status_code != 200:
            raise MailChimpStatusError(
                response.status_code,
                response.text[:500],
            )

    def get_reports_page(
        self,
        page=1,
        per_page=100,
    ):
        params = {
            "page": page,
            "per_page": per_page,
            "asc": "true",
            "filters[list]": "1626598",
            "group_connected_campaigns": "false",
            "campaign_list_location": "reports",
            "filters[bucket]": "recent",
        }

        response = self.session.get(
            self.REPORTS_URL,
            params=params,
            timeout=30,
        )

        self._check_response(response)

        try:
            return response.json()
        except ValueError as exc:
            raise MailChimpAPIError(
                "Mailchimp gaf geen JSON terug.\n"
                f"Status: {response.status_code}\n"
                f"URL: {response.url}\n"
                f"Content-Type: {response.headers.get('content-type')}\n"
                f"Eerste 300 tekens: {response.text[:300]}"
            ) from exc

    def get_reports(self):
        first_page = self.get_reports_page(
            page=1,
            per_page=100,
        )

        items = list(first_page.get("items", []))
        count = first_page.get("count", len(items))

        total_pages = (count + 99) // 100

        for page in range(2, total_pages + 1):
            response = self.get_reports_page(
                page=page,
                per_page=100,
            )

            items.extend(
                response.get("items", [])
            )

        return items

    def get_poll(self, report_id):
        response = self.session.get(
            self.ADVANCED_REPORT_URL,
            params={"id": report_id},
            timeout=30,
        )

        self._check_response(response)

        if len(response.text) < 100:
            raise MailChimpAPIError(
                "Mailchimp-reportpagina is leeg. "
                "Mogelijk is de sessiecookie verlopen."
            )

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        poll = {
            "poll_id": None,
            "options": [],
        }

        heading = soup.find(
            id="poll-results-heading"
        )

        poll_table = (
            heading.find_next("table")
            if heading
            else None
        )

        if poll_table is None:
            tables = soup.find_all("table")

            if len(tables) >= 2:
                poll_table = tables[1]
            elif len(tables) == 1:
                poll_table = tables[0]

        if poll_table is None:
            return poll

        for row in poll_table.find_all("tr"):
            cells = row.find_all("td")

            if len(cells) < 2:
                continue

            link = cells[0].find("a")

            if not link:
                continue

            onclick = link.get(
                "onclick",
                "",
            )

            option_match = re.search(
                r"option_id=(\d+)",
                onclick,
            )

            poll_match = re.search(
                r"poll_id=(\d+)",
                onclick,
            )

            if not option_match:
                continue

            if poll_match and not poll["poll_id"]:
                poll["poll_id"] = (
                    poll_match.group(1)
                )

            votes_text = (
                cells[1]
                .get_text(strip=True)
            )

            try:
                votes = int(votes_text)
            except ValueError:
                votes = 0

            poll["options"].append(
                {
                    "id": option_match.group(1),
                    "value": link.get_text(
                        strip=True
                    ),
                    "votes": votes,
                }
            )

        return poll

    def get_gebarometer_results(self, report_id):
        poll = self.get_poll(report_id)

        results = {
            "poll_id": poll["poll_id"],
            "ja_ja": 0,
            "ja_nee": 0,
            "nee": 0,
            "twijfel": 0,
            "total_votes": 0,
        }

        for option in poll["options"]:
            label = option["value"].strip()
            votes = option["votes"]

            if label.startswith(
                "JA ik ken dit gebaar - JA"
            ):
                results["ja_ja"] = votes

            elif label.startswith(
                "JA ik ken dit gebaar - NEE"
            ):
                results["ja_nee"] = votes

            elif label.startswith(
                "NEE ik ken dit gebaar"
            ):
                results["nee"] = votes

            elif label.startswith(
                "Ik twijfel"
            ):
                results["twijfel"] = votes

        results["total_votes"] = (
            results["ja_ja"]
            + results["ja_nee"]
            + results["nee"]
            + results["twijfel"]
        )

        return results

    def _parse_contacts(self, raw_text):
        fixed = re.sub(
            r"([{,])\s*([a-zA-Z0-9_]+)\s*:",
            r'\1"\2":',
            raw_text,
        )

        fixed = fixed.replace(
            "'",
            '"',
        )

        fixed = re.sub(
            r"<.*?>",
            "",
            fixed,
        )

        try:
            payload = json.loads(fixed)
        except json.JSONDecodeError as exc:
            raise MailChimpAPIError(
                "Kon Mailchimp-contactgegevens "
                "niet verwerken."
            ) from exc

        contacts = []

        for record in payload.get(
            "data",
            [],
        ):
            try:
                province = (
                    record[5]
                    .get("v", "")
                    .strip()
                )
            except (IndexError, AttributeError):
                province = ""

            contacts.append(
                {
                    "province": province,
                }
            )

        return contacts

    def get_poll_contacts(
        self,
        poll_id,
        option_id,
    ):
        params = {
            "poll_id": str(poll_id),
            "option_id": str(option_id),
        }

        data = (
            "q=select%20bulk_check%2C%20email_link%2C"
            "%20merge1%2C%20merge2%2C%20merge4%2C"
            "%20merge3%2C%20rating%2C"
            "%20last_update_time%2C%20optin_time"
            "%20from%20recipients"
            "%20limit%20200%20offset%200"
        )

        headers = {
            "content-type": (
                "application/"
                "x-www-form-urlencoded"
            ),
        }

        response = self.session.post(
            self.POLL_POPUP_URL,
            params=params,
            data=data,
            headers=headers,
            timeout=30,
        )

        self._check_response(response)

        return self._parse_contacts(
            response.text
        )
    @classmethod
    def from_curl_file(cls, file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()

        cookie = None
        headers = {}

        for line in lines:
            stripped = line.strip()

            if stripped.endswith("\\"):
                stripped = stripped[:-1].rstrip()

            if stripped.startswith("-b "):
                parts = shlex.split(stripped)
                cookie = parts[1]

            elif stripped.startswith("-H "):
                try:
                    parts = shlex.split(stripped)
                except ValueError:
                    continue

                if len(parts) < 2:
                    continue

                header = parts[1]

                if ":" not in header:
                    continue

                name, value = header.split(":", 1)

                name = name.strip()
                value = value.strip()

                if name.lower() == "cookie":
                    continue

                headers[name] = value

        if not cookie:
            raise MailChimpAPIError(
                "Geen cookie gevonden in de cURL-request."
            )

        client = cls(cookie)
        client.session.headers.update(headers)

        return client

    def test_advanced_report(self, report_id):
        url = (
            "https://us1.admin.mailchimp.com/"
            "i/reports/advanced/"
        )

        headers = {
            "accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,image/avif,"
                "image/webp,image/apng,*/*;q=0.8"
            ),
            "accept-language": (
                "nl-BE,nl-NL;q=0.9,nl;q=0.8,"
                "en-US;q=0.7,en;q=0.6"
            ),
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "referer": (
                "https://us1.admin.mailchimp.com/"
                f"reports/advanced?id={report_id}"
            ),
            "sec-fetch-dest": "iframe",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "upgrade-insecure-requests": "1",
        }

        response = self.session.get(
            url,
            params={"id": report_id},
            headers=headers,
            timeout=30,
            allow_redirects=False,
        )

        return {
            "status_code": response.status_code,
            "content_type": response.headers.get(
                "content-type"
            ),
            "location": response.headers.get(
                "location"
            ),
            "text": response.text[:2000],
        }

    @staticmethod
    def parse_send_date(report):
        raw_send_time = report.get(
            "send_time"
        )

        if not raw_send_time:
            return None

        if isinstance(
            raw_send_time,
            dict,
        ):
            value = raw_send_time.get(
                "date_str"
            )
        else:
            try:
                parsed = json.loads(
                    str(raw_send_time)
                    .replace("'", '"')
                )

                value = parsed.get(
                    "date_str"
                )
            except (
                json.JSONDecodeError,
                AttributeError,
            ):
                value = str(
                    raw_send_time
                )

        if not value:
            return None

        try:
            return datetime.fromisoformat(
                value.replace(
                    "Z",
                    "+00:00",
                )
            )
        except ValueError:
            return None

    def get_campaign_overview(self, campaign_id):
        url = (
            "https://us1.admin.mailchimp.com/"
            "analytics/reports/overview/lazy"
        )

        response = self.session.get(
            url,
            params={"id": campaign_id},
            timeout=30,
        )

        self._check_response(response)

        try:
            data = response.json()
        except ValueError as exc:
            raise MailChimpAPIError(
                "De Mailchimp-campagne gaf geen geldige JSON terug."
            ) from exc

        report_recap = data.get("report_recap", {})

        return {
            "campaign_id": campaign_id,
            "report_id": str(
                data.get("campaignId")
                or data.get("campaign_id")
                or ""
            ),
            "campaign_name": report_recap.get(
                "campaign_name",
                "",
            ),
            "send_time": report_recap.get(
                "send_time",
            ),
            "status": report_recap.get(
                "status",
                "",
            ),
            "has_polls": report_recap.get(
                "has_polls",
                False,
            ),
            "report_url": report_recap.get(
                "report_url",
                "",
            ),
        }
    def get_recent_campaigns(self, seed_campaign_id):
        url = (
            "https://us1.admin.mailchimp.com/"
            "analytics/reports/overview/lazy"
        )

        response = self.session.get(
            url,
            params={"id": seed_campaign_id},
            timeout=30,
        )

        self._check_response(response)

        try:
            data = response.json()
        except ValueError as exc:
            raise MailChimpAPIError(
                "De lijst met recente Mailchimp-campagnes "
                "gaf geen geldige JSON terug."
            ) from exc

        recent_reports = (
            data
            .get("header_data", {})
            .get("recent_reports", [])
        )

        campaigns = []

        for report in recent_reports:
            campaign_id = report.get("campaignID")

            if not campaign_id:
                continue

            campaigns.append(
                {
                    "campaign_id": campaign_id,
                    "campaign_name": report.get(
                        "campaignName",
                        "",
                    ),
                    "publish_time": report.get(
                        "publishTime",
                        "",
                    ),
                    "url": report.get(
                        "url",
                        "",
                    ),
                }
            )

        return campaigns