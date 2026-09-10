from src.collector.vtu_scraper import VTUScraper


def test_scraper_mock_listings():
    """
    Verify that explicit mock data can be generated.

    Mock data is used only for testing/development and should
    not be automatically injected into the production pipeline.
    """

    scraper = VTUScraper(
        base_url="https://vtu.internyet.in",
        use_mock_fallback=True,
    )

    listings = scraper.get_mock_listings()

    assert len(listings) >= 1

    for internship in listings:
        assert internship.portal_id
        assert internship.title
        assert internship.company


def test_scraper_fetch_listings_without_mock_fallback():
    """
    Verify that an unavailable portal does not silently return
    mock data when mock fallback is disabled.
    """

    scraper = VTUScraper(
        base_url="https://invalid-non-existent-vtu-portal-test.org",
        max_retries=1,
        timeout=1,
        use_mock_fallback=False,
    )

    listings = scraper.fetch_listings()

    assert listings == []