from ..test_pystmark import PystSenderTestBase


class PystSenderLiveTest(PystSenderTestBase):

    def test_send(self):
        r = self.send()
        print r.content
        self.assertValidJSONResponse(r, self.schema)
