import os
import logging

from dotenv import load_dotenv
from flask import Flask

# Load environment variables from .env file
load_dotenv()

from .api import api as api_blueprint  # noqa: E402  (needs env loaded first)

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Register Blueprints
app.register_blueprint(api_blueprint)


# Define routes
@app.get('/')
def index():
    return {"hi": "Hello, World!"}


# List all registered endpoints
def list_endpoints():
    output = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            methods = ','.join(rule.methods)
            output.append((rule.rule, methods))
    return output


# Print the list of registered endpoints to the terminal
for endpoint in list_endpoints():
    print(f"Endpoint: {endpoint[0]}, Methods: {endpoint[1]}")


def main():
    port = int(os.getenv('PORT', 8000))
    print(f"Port: {port}")

    app.run(port=port, debug=True)


if __name__ == '__main__':
    main()
