import unittest

from lertx.scene import BodyMapping


class BodyMappingTests(unittest.TestCase):
    def test_preserves_insertion_independent_of_index_order(self):
        mapping = BodyMapping()
        mapping.add(2, "/World/C")
        mapping.add(0, "/World/A")
        mapping.add(1, "/World/B")
        self.assertEqual(mapping.paths_in_index_order(), ["/World/A", "/World/B", "/World/C"])

    def test_does_not_assume_contiguous_indices(self):
        mapping = BodyMapping()
        mapping.add(5, "/World/Far")
        mapping.add(1, "/World/Near")
        self.assertEqual(mapping.paths_in_index_order(), ["/World/Near", "/World/Far"])


if __name__ == "__main__":
    unittest.main()
