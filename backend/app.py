from flask import Flask
from flask_cors import CORS
from routes.auth_routes import auth_bp
from routes.area.crud_area import area_bp
from routes.area.crud_region import region_bp
from routes.salesman.crud_salesman_team import salesman_team_bp
from routes.area.crud_entity import entity_bp
from routes.area.crud_branch import branch_bp
from routes.area.crud_branch_dist_route import branch_dist_bp
from routes.area.crd_mapping_branch import mapping_branch_bp
from routes.salesman.crud_salesman_master import salesman_master_bp
from routes.list_routes import list_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(auth_bp)
app.register_blueprint(area_bp)
app.register_blueprint(region_bp)
app.register_blueprint(salesman_team_bp)
app.register_blueprint(entity_bp)
app.register_blueprint(branch_bp)
app.register_blueprint(branch_dist_bp)
app.register_blueprint(mapping_branch_bp)
app.register_blueprint(salesman_master_bp)
app.register_blueprint(list_bp)

if __name__ == '__main__':
    app.run(debug=True)
