"""
Internshala Job / Internship Scraper.
Scrapes internship and job listings from Internshala.com.
"""

import logging
import re
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from urllib.parse import quote_plus
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class InternShalaScraper(BaseScraper):
    """Scrape job and internship listings from Internshala."""

    INTERNSHIP_URL = "https://internshala.com/internships/matching-preferences"
    JOBS_URL = "https://internshala.com/jobs"

    def scrape_jobs(self, query: str, location: str = "") -> list[dict]:
        """
        Scrape Internshala for internship/job listings.

        Args:
            query: Keywords like "python developer", "data science"
            location: Optional location filter

        Returns:
            List of job dictionaries
        """
        jobs = []
        try:
            self.start_browser()

            # Build search URL
            query_slug = query.lower().replace(" ", "-")
            if location:
                location_slug = location.lower().replace(" ", "-")
                url = f"https://internshala.com/internships/{query_slug}-internship-in-{location_slug}"
            else:
                url = f"https://internshala.com/internships/{query_slug}-internship"

            logger.info(f"Scraping Internshala: {url}")
            self.driver.get(url)
            self.safe_delay(3)

            # Scroll to load more
            for _ in range(3):
                self.driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);"
                )
                self.safe_delay(1.5)

            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            # Internshala internship cards
            cards = soup.find_all("div", class_=re.compile(r"individual_internship|internship_meta"))
            if not cards:
                cards = soup.find_all("div", {"class": "container-fluid individual_internship"})

            # Fallback: try the internship listing containers
            if not cards:
                cards = soup.find_all("div", id=re.compile(r"internship_detail_"))

            logger.info(f"Found {len(cards)} cards on Internshala")

            for card in cards[:self.max_jobs]:
                try:
                    job = self._parse_card(card)
                    if job and job.get("title"):
                        jobs.append(job)
                except Exception as e:
                    logger.warning(f"Error parsing Internshala card: {e}")
                    continue

            # Also try scraping jobs section
            job_listings = self._scrape_jobs_section(query, location)
            jobs.extend(job_listings)

        except Exception as e:
            logger.error(f"Internshala scraping error: {e}")
        finally:
            self.close_browser()

        logger.info(f"Scraped {len(jobs)} total listings from Internshala")
        return jobs

    def _parse_card(self, card) -> dict:
        """Parse a single Internshala listing card."""
        job = {"source": "Internshala"}

        # Title
        title_el = card.find("h3", class_="heading_4_5") or \
                   card.find("a", class_="view_detail_button")
        if title_el:
            job["title"] = title_el.get_text(strip=True)

        # Company
        company_el = card.find("h4", class_="heading_6") or \
                     card.find("p", class_="company_name")
        if company_el:
            job["company"] = company_el.get_text(strip=True)

        # Location
        location_el = card.find("a", class_="location_link") or \
                      card.find("p", id="location_names")
        if location_el:
            job["location"] = location_el.get_text(strip=True)
        else:
            loc_span = card.find("span", class_="location")
            if loc_span:
                job["location"] = loc_span.get_text(strip=True)

        # Stipend
        stipend_el = card.find("span", class_="stipend") or \
                     card.find("span", class_=re.compile(r"desktop-text"))
        if stipend_el:
            job["salary"] = stipend_el.get_text(strip=True)

        # Duration
        duration_el = card.find("span", class_="item_body")
        if duration_el:
            job["job_type"] = f"Duration: {duration_el.get_text(strip=True)}"

        # URL
        link_el = card.find("a", class_="view_detail_button") or \
                  card.find("a", href=re.compile(r"/internship/detail/"))
        if link_el and link_el.get("href"):
            href = link_el["href"]
            if not href.startswith("http"):
                href = f"https://internshala.com{href}"
            job["job_url"] = href

        return job

    def _scrape_jobs_section(self, query: str, location: str) -> list[dict]:
        """Also check the jobs section (full-time positions)."""
        jobs = []
        try:
            query_slug = query.lower().replace(" ", "-")
            url = f"https://internshala.com/jobs/{query_slug}-jobs"
            if location:
                url += f"-in-{location.lower().replace(' ', '-')}"

            self.driver.get(url)
            self.safe_delay(3)

            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            cards = soup.find_all("div", class_=re.compile(r"individual_internship"))

            for card in cards[:self.max_jobs // 2]:
                try:
                    job = self._parse_card(card)
                    if job and job.get("title"):
                        job["job_type"] = "Full-time"
                        jobs.append(job)
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"Internshala jobs section error: {e}")

        return jobs

    def scrape_job_details(self, job_url: str) -> dict:
        """Scrape full details from a specific Internshala listing page."""
        details = {}
        try:
            self.driver.get(job_url)
            self.safe_delay(3)

            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            # Description
            desc_el = soup.find("div", class_="text-container") or \
                      soup.find("div", class_=re.compile(r"internship_details"))
            if desc_el:
                details["description"] = desc_el.get_text(separator="\n", strip=True)

            # Skills required
            skill_els = soup.find_all("span", class_="round_tabs") or \
                        soup.find_all("span", class_=re.compile(r"skill_tag"))
            if skill_els:
                details["skills_required"] = [s.get_text(strip=True) for s in skill_els]

            # Who can apply / requirements
            req_el = soup.find("div", class_=re.compile(r"who_can_apply"))
            if req_el:
                details["requirements"] = req_el.get_text(separator="\n", strip=True)

        except Exception as e:
            logger.warning(f"Error scraping Internshala details: {e}")

        return details
