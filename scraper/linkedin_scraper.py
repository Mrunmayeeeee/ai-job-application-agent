"""
LinkedIn Job Scraper – scrapes public job listings from LinkedIn.
Uses the public jobs search page (no login required for basic listings).
"""

import logging
import re
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import quote_plus
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class LinkedInScraper(BaseScraper):
    """Scrape job listings from LinkedIn's public job search."""

    BASE_URL = "https://www.linkedin.com/jobs/search"

    def scrape_jobs(self, query: str, location: str = "India") -> list[dict]:
        """
        Scrape LinkedIn job listings for a given query.

        Args:
            query: Job title or keywords (e.g., "Python Developer")
            location: Location filter (e.g., "India", "Remote")

        Returns:
            List of job dictionaries
        """
        jobs = []
        try:
            self.start_browser()
            url = (
                f"{self.BASE_URL}?"
                f"keywords={quote_plus(query)}"
                f"&location={quote_plus(location)}"
                f"&trk=public_jobs_jobs-search-bar_search-submit"
            )

            logger.info(f"Scraping LinkedIn: {query} in {location}")
            self.driver.get(url)
            self.safe_delay(3)

            # Scroll to load more listings
            for _ in range(3):
                self.driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);"
                )
                self.safe_delay(1.5)

            # Try clicking "See more jobs" button
            try:
                see_more = self.driver.find_element(
                    By.CSS_SELECTOR, "button.infinite-scroller__show-more-button"
                )
                see_more.click()
                self.safe_delay(2)
            except Exception:
                pass

            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            # LinkedIn public page uses specific card classes
            job_cards = soup.find_all("div", class_=re.compile(r"base-card|job-search-card"))

            if not job_cards:
                # Fallback: try list items
                job_cards = soup.find_all("li", class_=re.compile(r"jobs-search__result"))

            logger.info(f"Found {len(job_cards)} job cards on LinkedIn")

            for card in job_cards[:self.max_jobs]:
                try:
                    job = self._parse_card(card)
                    if job and job.get("title"):
                        jobs.append(job)
                except Exception as e:
                    logger.warning(f"Error parsing LinkedIn card: {e}")
                    continue

        except Exception as e:
            logger.error(f"LinkedIn scraping error: {e}")
        finally:
            self.close_browser()

        logger.info(f"Scraped {len(jobs)} jobs from LinkedIn")
        return jobs

    def _parse_card(self, card) -> dict:
        """Parse a single LinkedIn job card into a dictionary."""
        job = {"source": "LinkedIn"}

        # Title
        title_el = card.find("h3", class_=re.compile(r"base-search-card__title")) or \
                   card.find("span", class_=re.compile(r"sr-only"))
        if title_el:
            job["title"] = title_el.get_text(strip=True)

        # Company
        company_el = card.find("h4", class_=re.compile(r"base-search-card__subtitle")) or \
                     card.find("a", class_=re.compile(r"hidden-nested-link"))
        if company_el:
            job["company"] = company_el.get_text(strip=True)

        # Location
        location_el = card.find("span", class_=re.compile(r"job-search-card__location"))
        if location_el:
            job["location"] = location_el.get_text(strip=True)

        # URL
        link_el = card.find("a", class_=re.compile(r"base-card__full-link")) or \
                  card.find("a", href=re.compile(r"/jobs/view/"))
        if link_el and link_el.get("href"):
            job["job_url"] = link_el["href"].split("?")[0]

        # Posted date
        date_el = card.find("time")
        if date_el:
            job["posted_date"] = date_el.get("datetime", date_el.get_text(strip=True))

        return job

    def scrape_job_details(self, job_url: str) -> dict:
        """Scrape full details from a specific LinkedIn job page."""
        details = {}
        try:
            self.driver.get(job_url)
            self.safe_delay(3)

            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            # Job description
            desc_el = soup.find("div", class_=re.compile(r"show-more-less-html__markup"))
            if desc_el:
                details["description"] = desc_el.get_text(separator="\n", strip=True)

            # Criteria (experience level, job type, etc.)
            criteria_items = soup.find_all("li", class_=re.compile(r"description__job-criteria-item"))
            for item in criteria_items:
                header = item.find("h3")
                value = item.find("span")
                if header and value:
                    key = header.get_text(strip=True).lower().replace(" ", "_")
                    details[key] = value.get_text(strip=True)

        except Exception as e:
            logger.warning(f"Error scraping job details: {e}")

        return details
