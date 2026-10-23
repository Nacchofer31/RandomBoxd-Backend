"""Letterboxd scraper for film enrichment."""

import httpx
from bs4 import BeautifulSoup


class LetterboxdScraper:
    """Scrapes film metadata from Letterboxd."""

    BASE_URL = "https://letterboxd.com/film"

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)

    async def get_film_genres(self, slug: str) -> list[str]:
        """
        Scrape genres for a film from Letterboxd.

        Args:
            slug: Letterboxd film slug (e.g., "inception")

        Returns:
            List of genre strings (e.g., ["drama", "science-fiction"])
        """
        url = f"{self.BASE_URL}/{slug}/"

        try:
            response = await self.client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Letterboxd has genres in a div with class "text-list text-link"
            # under the "Genres" section
            genres_section = soup.find("div", id="tab-genres")
            if not genres_section:
                return []

            genre_links = genres_section.find_all("a")
            genres = []

            for link in genre_links:
                # Extract genre from URL path like "/films/genre/drama/"
                href = link.get("href", "")
                if "/genre/" in href:
                    # Extract genre name from URL
                    genre = href.split("/genre/")[-1].strip("/")
                    if genre:
                        genres.append(genre)

            return genres

        except Exception:
            # If scraping fails, return empty list (film will use pool-level genres)
            return []
        finally:
            await self.client.aclose()

    async def enrich_films(self, slugs: list[str]) -> dict[str, list[str]]:
        """
        Enrich multiple films with genre data.

        Args:
            slugs: List of film slugs to enrich

        Returns:
            Dictionary mapping slug -> genres
        """
        results = {}

        for slug in slugs:
            genres = await self.get_film_genres(slug)
            results[slug] = genres

            # Small delay to be polite to Letterboxd
            import asyncio
            await asyncio.sleep(0.5)

        return results


# Singleton instance
scraper = LetterboxdScraper()
