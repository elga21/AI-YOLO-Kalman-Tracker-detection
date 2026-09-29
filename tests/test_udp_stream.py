import unittest

from cuas_engine.stream_engine import is_network_stream, normalize_source_url


class UdpStreamTests(unittest.TestCase):
    def test_udp_source_is_recognized(self):
        self.assertTrue(is_network_stream("udp://192.168.100.12:37511"))
        self.assertTrue(is_network_stream("192.168.100.12:37511"))

    def test_udp_source_is_normalized(self):
        self.assertEqual(normalize_source_url("192.168.100.12:37511"), "udp://192.168.100.12:37511")
        self.assertEqual(normalize_source_url("udp://192.168.100.12:37511"), "udp://192.168.100.12:37511")
        self.assertEqual(normalize_source_url("192.168.100.12"), "udp://192.168.100.12:37511")


if __name__ == "__main__":
    unittest.main()
