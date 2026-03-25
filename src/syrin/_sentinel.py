"""Internal sentinel for 'not provided' in Agent.__init__.

Used to distinguish between 'parameter omitted' and 'parameter explicitly passed as None'
when resolving subclass-inherited defaults. NOT_PROVIDED means 'use class default';
None can mean 'explicitly set to None'. Not part of the public API.
"""

NOT_PROVIDED: object = object()
