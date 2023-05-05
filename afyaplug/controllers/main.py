import json
import logging
import ast
import werkzeug.wrappers

from odoo import http
from odoo.addons.restful.common import invalid_response, valid_response
from odoo.exceptions import AccessDenied, AccessError
from odoo.http import request

_logger = logging.getLogger(__name__)


class MainController(http.Controller):
    @http.route("/api/user", methods=["POST"], type="http", auth="public", csrf=False)
    def token(self, **post):
        payload = request.httprequest.data.decode()
        payload = json.loads(payload)
        user_check = request.env['res.users'].search_count([("login", "=", payload['email'])], limit=1)

        if user_check > 0:
            return invalid_response("UserExists", "User already exists")

        user = request.env['res.users'].sudo().create({
            'name': payload['name'],
            'login': payload['email'],
            'password': payload['password'],
        })

        partner = request.env['res.partner'].sudo().browse(user.partner_id.id)
        partner.write(
            {
                'name': payload['name'],
                'company_type': 'person',
                'country_id': request.env['res.country'].search([('code', '=', 'KE')], limit=1).id,
                'email': payload['email'],
                'phone': '555-555-1212',
                'mobile': '555-555-1212',
                'function': 'Customer',
                'comment': 'Customer Contact',
                'category_id': [
                    (6, 0, [request.env['res.partner.category'].sudo().search([('name', '=', 'Customers')],
                                                                       limit=1).id])]
            }
        )
        # create access token
        return werkzeug.wrappers.Response(
            status=200,
            content_type="application/json; charset=utf-8",
            headers=[("Cache-Control", "no-store"), ("Pragma", "no-cache")],
            response=json.dumps(
                {
                    "uid": user.id,
                    "partner": partner.id
                }
            ),
        )

    @http.route("/api/nurses", type="http", auth="public", methods=["GET"], csrf=False)
    def nurses(self, **kw):
        domain = []
        if kw.get('domain', ''):
            domain = kw.get('domain', '')
            domain = ast.literal_eval(domain)

        data = request.env['hr.employee'].sudo().search_read(
            domain=domain
        )
        return valid_response(data)
