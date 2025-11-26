from flask import Flask
from flask_cors import CORS
from routes.auth_routes import auth_bp
from routes.crud_area import area_bp
from routes.crud_region import region_bp
from routes.crud_salesman_team import salesman_team_bp
from routes.crud_entity import entity_bp
from routes.crud_branch import branch_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(auth_bp)
app.register_blueprint(area_bp)
app.register_blueprint(region_bp)
app.register_blueprint(salesman_team_bp)
app.register_blueprint(entity_bp)
app.register_blueprint(branch_bp)

if __name__ == '__main__':
    app.run(debug=True)
