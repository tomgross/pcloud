""" Validators and decorators
"""

MODE_OR = 0
MODE_AND = 1


class RequiredParameterCheck(object):
    """A decorator that checks if at least on named parameter is present"""

    def __init__(self, required, mode=MODE_OR):
        self.required = sorted(required)
        self.mode = mode

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            found_paramater = sorted([req for req in self.required if req in kwargs])
            if self.mode == MODE_OR and found_paramater:
                return func(*args, **kwargs)
            elif self.mode == MODE_AND and found_paramater == self.required:
                return func(*args, **kwargs)
            else:
                raise ValueError(
                    f"Required parameter `{', '.join(self.required)}` is missing."
                )

        wrapper.__name__ = func.__name__
        wrapper.__dict__.update(func.__dict__)
        wrapper.__doc__ = func.__doc__
        return wrapper
