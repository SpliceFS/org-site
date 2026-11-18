"""Rules every page of the site keeps."""

import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
# The pages in the site folder, and the template the change log page is built from.
PAGES = sorted(ROOT.glob("site/**/*.html")) + [ROOT / "scripts" / "changelog-page.html"]
LOGO = re.compile(r'<a class="mark" href="/">')


class TestPages(unittest.TestCase):
    def test_every_page_has_pages(self):
        self.assertGreater(len(PAGES), 1)

    def test_the_logo_leads_to_the_home_page(self):
        for page in PAGES:
            with self.subTest(page=str(page.relative_to(ROOT))):
                self.assertRegex(page.read_text(encoding="utf-8"), LOGO)


if __name__ == "__main__":
    unittest.main()
