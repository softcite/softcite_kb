from flask import make_response, abort
import connexion
from datetime import datetime

from swagger_ui_bundle import swagger_ui_3_path
options = {'swagger_path': swagger_ui_3_path, 'docExpansion': 'list'}

# Create the application instance
app = connexion.App(__name__, specification_dir='swagger/', options=options)

# Read the swagger.yml file to configure the endpoints and get the nice GUI for the same price
app.add_api("openapi.yaml", arguments={'docExpansion': 'list'})

# If we're running in stand alone mode, run the application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
