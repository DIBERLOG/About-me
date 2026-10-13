import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
from update_portfolio import fetch_repositories, render_catalog, render_stats, replace_section


class PortfolioTest(unittest.TestCase):
    def test_public_filter_escaping_and_statistics(self):
        repos = [
            {"name": "A", "description": "<tag>|x\ny", "language": "Python", "stargazers_count": 3},
            {"name": "Fork", "fork": True, "language": "Rust", "stargazers_count": 99},
            {"name": "Farm-bot", "language": "Python", "stargazers_count": 99},
            {"name": "Secret", "private": True},
        ]
        table = render_catalog(repos)
        self.assertNotIn("Farm-bot", table)
        self.assertNotIn("Secret", table)
        self.assertIn("&lt;tag&gt;&#124;x y", table)
        self.assertIn("форк", table)
        svg = render_stats(repos, "2026-10-13")
        ET.fromstring(svg)
        self.assertIn("Проекты: 1", svg)
        self.assertIn("Звёзды: 3", svg)
        self.assertNotIn("Rust: 1", svg)

    def test_pagination(self):
        class Response:
            def __init__(self, payload):
                import io, json
                self.stream = io.StringIO(json.dumps(payload))
            def __enter__(self):
                return self.stream
            def __exit__(self, *args):
                self.stream.close()
        with patch("update_portfolio.urlopen", side_effect=[Response([{"name": "A"}] * 100), Response([{"name": "B"}])]) as request:
            self.assertEqual(len(fetch_repositories()), 101)
            self.assertIn("page=2", request.call_args.args[0].full_url)

    def test_markers_protect_manual_content(self):
        readme = "intro\n<!-- PROJECTS:START -->old<!-- PROJECTS:END -->\ncontacts"
        self.assertEqual(replace_section(readme, "PROJECTS", "new"), "intro\n<!-- PROJECTS:START -->\nnew\n<!-- PROJECTS:END -->\ncontacts")
        with self.assertRaises(ValueError):
            replace_section("no markers", "PROJECTS", "new")


if __name__ == "__main__":
    unittest.main()
