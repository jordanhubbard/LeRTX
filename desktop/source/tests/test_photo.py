import base64
import copy
import hashlib
import json
import unittest

from lertx.config import DEFAULT_PROFILE
from lertx.photo import request_scene
from lertx.transport import CancelToken, TimeoutTransportError
from tests.test_reconstruction import scene_payload


class PhotoTests(unittest.TestCase):
    def setUp(self):
        self.profile = copy.deepcopy(DEFAULT_PROFILE)
        self.profile["llm"]["api_key"] = "injected-test-key"
        self.image = b"\x89PNG\r\n\x1a\nfixture"

    def response(self, text=None, status="completed"):
        return (200, {}, json.dumps({"status": status, "output": [{"type":"message", "content":
            [{"type":"output_text", "text": text if text is not None else json.dumps(scene_payload())}]}]}).encode())

    def test_request_uses_exact_settings_image_and_provenance(self):
        calls = []
        def transport(url, headers, body, timeout):
            calls.append((url, headers, json.loads(body), timeout))
            return self.response()
        result = request_scene(self.profile, self.image, transport)
        self.assertEqual(result["state"], "success")
        self.assertEqual(result["image_sha256"], hashlib.sha256(self.image).hexdigest())
        url, headers, body, timeout = calls[0]
        self.assertEqual(url, self.profile["llm"]["endpoint"])
        self.assertEqual(body["model"], self.profile["llm"]["model"])
        self.assertEqual(body["max_output_tokens"], 512)
        image_url = body["input"][0]["content"][1]["image_url"]
        self.assertEqual(base64.b64decode(image_url.split(",")[1]), self.image)
        self.assertNotIn("injected-test-key", json.dumps(result))
        self.assertNotIn('text', body)
        self.assertNotIn('provider', body)

    def test_openrouter_enforces_shape_but_still_checks_mesh_semantics(self):
        self.profile['llm']['endpoint']='https://openrouter.ai/api/v1/responses'
        self.profile['llm']['model']='openai/gpt-5-mini'
        self.profile['llm']['max_output_tokens']=8192
        def transport(url,headers,body,timeout):
            request=json.loads(body)
            self.assertTrue(request['text']['format']['strict'])
            self.assertTrue(request['provider']['require_parameters'])
            geometry=request['text']['format']['schema']['properties']['objects']['items']['properties']['geometry']
            mesh=next(v for v in geometry['anyOf'] if v['properties']['type']['enum']==['mesh'])
            self.assertEqual(mesh['properties']['triangles']['items']['type'],'integer')
            scene=scene_payload()
            # Valid JSON-schema shape, invalid physical geometry: collinear triangle.
            scene['objects'][0]['geometry']={'type':'mesh','points':[[0,0,0],[1,0,0],[2,0,0]],'triangles':[0,1,2]}
            return self.response(json.dumps(scene))
        self.assertEqual(request_scene(self.profile,self.image,transport),{'state':'invalid_scene'})

    def test_cancel_before_and_during_request(self):
        token = CancelToken()
        token.cancel()
        def never(*args):
            self.fail("cancelled request contacted transport")
        self.assertEqual(request_scene(self.profile, self.image, never, token), {"state":"cancelled"})
        token = CancelToken()
        def cancelled(*args):
            token.cancel()
            return self.response()
        self.assertEqual(request_scene(self.profile, self.image, cancelled, token), {"state":"cancelled"})

    def test_missing_key_or_invalid_settings_do_not_send(self):
        def never(*args):
            self.fail("invalid request contacted transport")
        self.profile["llm"]["api_key"] = ""
        self.assertEqual(request_scene(self.profile, self.image, never)["state"], "missing_key")
        self.profile["llm"]["endpoint"] = "http://invalid.example"
        self.assertEqual(request_scene(self.profile, self.image, never)["state"], "invalid_settings")

    def test_bad_incomplete_and_oversized_responses(self):
        for response, expected in ((self.response(status="incomplete"), "incomplete"),
                                   (self.response("not JSON"), "invalid_scene"),
                                   ((200, {}, b"x"*(4*1024*1024+1)), "service_failure"),
                                   ((401, {}, b"private provider data"), "auth_failure"),
                                   ((200, {}, b"not JSON"), "service_failure")):
            self.assertEqual(request_scene(self.profile, self.image, lambda *a: response), {"state":expected})

    def test_exception_details_never_escape(self):
        def raises(*args):
            raise RuntimeError("injected-test-key private image data")
        self.assertEqual(request_scene(self.profile, self.image, raises), {"state":"service_failure"})
        def timeout(*args):
            raise TimeoutTransportError("private")
        self.assertEqual(request_scene(self.profile, self.image, timeout), {"state":"timeout"})

    def test_detailed_preset_sets_reasoning_and_preserves_provider(self):
        from lertx.photo import photo_profile
        self.profile['llm']['endpoint']='https://openrouter.ai/api/v1/responses'
        profile=photo_profile(self.profile,'detail')
        def transport(url,headers,body,timeout):
            payload=json.loads(body)
            self.assertEqual(payload['reasoning'],{'effort':'high'})
            self.assertEqual(payload['model'],'openai/gpt-6-astra')
            self.assertEqual(timeout,300)
            self.assertEqual(payload['max_output_tokens'],24576)
            return self.response()
        self.assertEqual(request_scene(profile,self.image,transport)['state'],'success')
        self.assertEqual(self.profile['llm']['max_output_tokens'],512)
        self.profile['llm']['endpoint']='https://example.com/v1/responses'
        with self.assertRaises(ValueError):photo_profile(self.profile,'detail')
