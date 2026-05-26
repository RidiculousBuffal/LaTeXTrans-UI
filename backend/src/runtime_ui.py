class _NullElement:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def progress(self, *args, **kwargs):
        return self

    def text(self, *args, **kwargs):
        return self

    def error(self, *args, **kwargs):
        return self

    def success(self, *args, **kwargs):
        return self

    def empty(self):
        return self


class _RuntimeUI:
    def empty(self):
        return _NullElement()

    def progress(self, *args, **kwargs):
        return _NullElement()

    def success(self, *args, **kwargs):
        return None

    def error(self, *args, **kwargs):
        return None


st = _RuntimeUI()
