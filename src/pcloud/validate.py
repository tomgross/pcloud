""" Validators and decorators
"""


class RequiredParameterCheck(object):
    """ A decorator that checks function parameter
    """

    def __init__(self, required):
        self.required = required

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            found_paramater = False
            for req in self.required:
                if req in kwargs:
                    found_paramater = True
                    break
            if found_paramater:
                return func(*args, **kwargs)
            else:
                raise ValueError('One required parameter `%s` is missing',
                                 ', '.join(self.required))
        wrapper.__name__ = func.__name__
        wrapper.__dict__.update(func.__dict__)
        wrapper.__doc__ = func.__doc__
        return wrapper
