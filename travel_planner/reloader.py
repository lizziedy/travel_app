import os
from django.db.models.loading import AppCache
cache = AppCache()

curdir = os.getcwd()
for app in cache.get_apps():
    f = app.__file__
    if f.startswith(curdir) and f.endswith('.pyc'):
        os.remove(f)
    __import__(app.__name__)
    reload(app)

from django.utils.datastructures import SortedDict
cache.app_store = SortedDict()
cache.app_models = SortedDict()
cache.app_errors = {}
cache.handled = {}
cache.loaded = False
