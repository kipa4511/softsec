# test/test_mocks.py
class MockWatermarkUtils:
    @staticmethod
    def apply_watermark(*args, **kwargs):
        return b"%PDF-1.4\n% WATERMARKED\n%%EOF\n"

    @staticmethod
    def read_watermark(*args, **kwargs):
        return "SECRET123"

