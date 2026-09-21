import json
import unittest

from lertx.reconstruction import MAX_RESPONSE_BYTES, parse_scene


def scene_payload():
    return {"schema": "lertx.photo-scene.v1", "units": "m", "unobserved": ["Behind the workbench"],
            "objects": [{"id": "table", "label": "Work table", "translation": [0, 0, .4],
                         "rotation": [0, 0, 0], "color": [.3, .4, .5], "confidence": .7,
                         "geometry": {"type": "box", "size": [1, .6, .05]}}]}


class ReconstructionTests(unittest.TestCase):
    def test_valid_scene_round_trips(self):
        payload = scene_payload()
        self.assertEqual(parse_scene(json.dumps(payload)), payload)

    def test_rejects_unknown_fields_code_assets_and_verified_claims(self):
        for field in ("references", "python", "verified", "payload"):
            payload = scene_payload()
            payload[field] = "untrusted-provider-content"
            with self.assertRaisesRegex(ValueError, "Invalid photo scene response") as raised:
                parse_scene(json.dumps(payload))
            self.assertNotIn("untrusted-provider-content", str(raised.exception))

    def test_rejects_duplicate_keys_size_nesting_and_nonfinite(self):
        for text in ('{"schema":1,"schema":2}', '['*2000+']'*2000,
                     ' '* (MAX_RESPONSE_BYTES+1), 'NaN', 'Infinity', '{"x":1e9999}'):
            with self.subTest(length=len(text)):
                with self.assertRaises(ValueError):
                    parse_scene(text)

    def test_rejects_unsafe_ids_duplicate_ids_and_bad_vectors(self):
        for key, value in (("id", "../escape"), ("id", "/Root"), ("id", "é"),
                           ("id", "x"*65), ("translation", [0, 1]),
                           ("translation", [True, 0, 0]), ("rotation", [361, 0, 0]),
                           ("color", [2, 0, 0]), ("confidence", -1), ("label", "\ud800")):
            payload = scene_payload()
            payload["objects"][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                parse_scene(json.dumps(payload))
        payload = scene_payload()
        payload["objects"] *= 2
        with self.assertRaises(ValueError):
            parse_scene(json.dumps(payload))

    def test_mesh_requires_bounded_valid_nondegenerate_triangles(self):
        geometry = {"type": "mesh", "points": [[0, 0, 0], [1, 0, 0], [0, 1, 0]], "triangles": [0, 1, 2]}
        payload = scene_payload()
        payload["objects"][0]["geometry"] = geometry
        self.assertEqual(parse_scene(json.dumps(payload)), payload)
        for indices in ([0, 1], [0, 1, 3], [0, 1, -1], [0, True, 2], [0, 0, 1]):
            geometry["triangles"] = indices
            with self.assertRaises(ValueError):
                parse_scene(json.dumps(payload))
        geometry["triangles"] = [0, 1, 2]
        geometry["points"][2] = [2, 0, 0]
        with self.assertRaises(ValueError):
            parse_scene(json.dumps(payload))

    def test_dimensions_and_unknown_geometry_are_rejected(self):
        for geometry in ({"type": "box", "size": [0, 1, 1]}, {"type": "sphere", "radius": -1},
                         {"type": "mesh", "points": [], "triangles": []}, {"type": "script"},
                         {"type": "box", "size": [1]*3, "asset": "https://example.invalid"}):
            payload = scene_payload()
            payload["objects"][0]["geometry"] = geometry
            with self.assertRaises(ValueError):
                parse_scene(json.dumps(payload))

    def test_bounds_on_object_and_unknown_region_counts(self):
        payload = scene_payload()
        payload["objects"] = [dict(payload["objects"][0], id=f"p{i}") for i in range(257)]
        with self.assertRaises(ValueError):
            parse_scene(json.dumps(payload))
        payload = scene_payload()
        payload["unobserved"] = ["unknown"] * 65
        with self.assertRaises(ValueError):
            parse_scene(json.dumps(payload))
