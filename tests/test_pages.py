"""Rules every page of the site keeps."""

import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
# The pages in the site folder, and the template the change log page is built from.
PAGES = sorted(ROOT.glob("site/**/*.html")) + [ROOT / "scripts" / "changelog-page.html"]
LOGO = re.compile(r'<a class="mark" href="/">')
INSTALL_PAGE = ROOT / "site" / "install" / "index.html"
STEP = re.compile(r'<section class="one" id="(\w+)">(.*?)</section>', re.DOTALL)


class TestPages(unittest.TestCase):
    def test_every_page_has_pages(self):
        self.assertGreater(len(PAGES), 1)

    def test_the_logo_leads_to_the_home_page(self):
        for page in PAGES:
            with self.subTest(page=str(page.relative_to(ROOT))):
                self.assertRegex(page.read_text(encoding="utf-8"), LOGO)


class TestInstallPage(unittest.TestCase):
    def steps(self):
        return STEP.findall(INSTALL_PAGE.read_text(encoding="utf-8"))

    def test_it_has_the_three_steps_in_order(self):
        headings = [re.search(r"<h2>(Step \d):", body) for _, body in self.steps()]
        self.assertEqual([h.group(1) for h in headings if h], ["Step 1", "Step 2", "Step 3"])

    def test_each_step_has_a_code_block(self):
        self.assertEqual(len(self.steps()), 3)
        for step_id, body in self.steps():
            with self.subTest(step=step_id):
                self.assertIn("<pre><code>", body)


if __name__ == "__main__":
    unittest.main()
