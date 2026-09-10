from .webhook import webhook
from .function_call import function_call
from . import api

# Register blueprints (webhook declares its own /webhook rule so the path has
# no trailing slash — deliveries must not bounce through a 308 redirect)
api.register_blueprint(webhook)
api.register_blueprint(function_call, url_prefix='/functions')
