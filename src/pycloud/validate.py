from decorator import decorator

def validate_folder_identifier():
    """A decorator that tests whether `path` or `folderid` has been specified.

    Usage:
    @validate_folder_identifier
    def foo(path=None, folderid=None, c=None):
        pass
    """
    def _validate_folder_identifier(func):
        """The actual decorator"""
        signature_params = _get_arg_spec(func, required_params)

        def wrapped(f, *args, **kwargs):
            """The wrapped function"""
	    if folderid is not None:
		params['folderid'] = folderid
	    elif path is not None:
		params['path'] = path
	    else:
		raise ValueError('Either `folderid` or `path` must be specified!')
            supplied_args = _get_supplied_args(signature_params, args, kwargs)

            missing = [p for p in required_params if p not in supplied_args]
            if len(missing):
                raise MissingParameterError(
                    'Missing required parameter(s): {0}'.format(
                        ', '.join(missing))
                )

            return f(*args, **kwargs)

        return decorator(wrapped, func)

    return _validate_folder_identifier

