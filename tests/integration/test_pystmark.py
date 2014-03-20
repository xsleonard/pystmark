import pystmark
from ..test_pystmark import (SenderTestBase, BatchSenderTestBase,
                             TestCase)


class SenderLiveTest(SenderTestBase):

    def test_send(self):
        r = self.send()
        self.assertValidJSONResponse(r, self.schema)


class BatchSenderLiveTest(BatchSenderTestBase):

    def test_send_batch(self):
        r = self.send()
        self.assertValidJSONResponse(r, self.schema)


# TODO -- postmark api has errors when using test api key on the bounce api
# but we want to try those


class BouncesLiveTest(TestCase):

    def test_get_bounces(self):
        r = pystmark.get_bounces(test=True)
        # TODO -- should be 200, once Postmark fixes theirs
        self.assert500(r)


class BounceLiveTest(TestCase):

    def test_get_bounce(self):
        r = pystmark.get_bounce(777, test=True)
        self.assert500(r)


class BounceDumpLiveTest(TestCase):

    def test_get_bounce_dump(self):
        r = pystmark.get_bounce_dump(777, test=True)
        self.assert500(r)


class BounceTagsLiveTest(TestCase):

    def test_get_bounce_tags(self):
        r = pystmark.get_bounce_tags(test=True)
        self.assert500(r)


class BounceActivateLiveTest(TestCase):

    def test_bounce_activate(self):
        r = pystmark.activate_bounce(777, test=True)
        self.assert500(r)


class DeliveryStatsLiveTest(TestCase):

    def test_get_delivery_stats(self):
        r = pystmark.get_delivery_stats(test=True)
        self.assert500(r)
