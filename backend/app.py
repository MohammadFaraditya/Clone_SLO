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
from routes.salesman.crud_mapping_salesman import mapping_salesman_bp
from routes.customer.crud_customer_prc import customer_prc_bp
from routes.customer.crud_customer_dist import customer_dist_bp
from routes.customer.crd_mapping_customer import mapping_customer_bp
from routes.product.crud_product_dist import product_dist_bp
from routes.product.crud_product_prc import product_prc_bp
from routes.product.crud_product_group import product_group_bp
from routes.product.crd_mapping_product import mapping_product_bp
from routes.product.crud_pricegroup import pricegroup_bp
from routes.config.crud_config import config_bp
from routes.sellout.cr_sellout import sellout_bp
from routes.sellout.cr_mapping_error import mapping_error_bp

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
app.register_blueprint(mapping_salesman_bp)
app.register_blueprint(customer_prc_bp)
app.register_blueprint(customer_dist_bp)
app.register_blueprint(mapping_customer_bp)
app.register_blueprint(product_dist_bp)
app.register_blueprint(product_prc_bp)
app.register_blueprint(product_group_bp)
app.register_blueprint(mapping_product_bp)
app.register_blueprint(pricegroup_bp)
app.register_blueprint(config_bp)
app.register_blueprint(sellout_bp)
app.register_blueprint(mapping_error_bp)



if __name__ == '__main__':
    app.run(debug=True)
