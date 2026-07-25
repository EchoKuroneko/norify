from unittest.mock import patch, Mock
import unittest
from core.update import check_for_update


class TestUpdateChecker(unittest.TestCase):
    def setUp(self):
        self.version = "2.0.0"
        self.repo = "https://github.com/fake/repo"

    def test_update_available(self):
        # Mock GitHub response
        mock_response = Mock()
        mock_response.json.return_value = {
            "tag_name": "v" + self.version,
            "html_url": self.repo,
        }
        mock_response.raise_for_status = lambda: None

        with patch("requests.get", return_value=mock_response):
            result = check_for_update("3.0.0")
            self.assertIsNotNone(result)
            self.assertEqual(result[0], self.version)
            self.assertEqual(result[1], self.repo)


if __name__ == "__main__":
    unittest.main()
