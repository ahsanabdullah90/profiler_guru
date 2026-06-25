class LazyProxy:
    """A transparent lazy proxy that defers instantiation of the target class until the first attribute or method access."""
    def __init__(self, factory):
        object.__setattr__(self, "_factory", factory)
        object.__setattr__(self, "_wrapped", None)

    def _get_wrapped(self):
        if self._wrapped is None:
            object.__setattr__(self, "_wrapped", self._factory())
        return self._wrapped

    def __getattr__(self, name):
        return getattr(self._get_wrapped(), name)

    def __setattr__(self, name, value):
        if name in ("_factory", "_wrapped"):
            object.__setattr__(self, name, value)
        else:
            setattr(self._get_wrapped(), name, value)

    def __call__(self, *args, **kwargs):
        return self._get_wrapped()(*args, **kwargs)

    def __repr__(self):
        return repr(self._get_wrapped())

    def __str__(self):
        return str(self._get_wrapped())

    def __len__(self):
        return len(self._get_wrapped())

    def __getitem__(self, key):
        return self._get_wrapped()[key]

    def __setitem__(self, key, value):
        self._get_wrapped()[key] = value

    def __delitem__(self, key):
        del self._get_wrapped()[key]

    def __iter__(self):
        return iter(self._get_wrapped())

    def __contains__(self, item):
        return item in self._get_wrapped()

    def __enter__(self):
        return self._get_wrapped().__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._get_wrapped().__exit__(exc_type, exc_val, exc_tb)
