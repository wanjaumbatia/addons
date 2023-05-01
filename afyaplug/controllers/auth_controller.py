from odoo import http
from odoo.http import request
from odoo.exceptions import UserError
from odoo.addons.restful.common import invalid_response, valid_response
from odoo.exceptions import AccessDenied, AccessError
import json
import logging
import werkzeug.wrappers

_logger = logging.getLogger(__name__)


class AuthenticationController(http.Controller):
    @http.route('/api/authenticate', type='json', auth='none', methods=['POST'])
    def authenticate(self, **post):
        _token = request.env["api.access_token"]
        payload = request.httprequest.data.decode()
        payload = json.loads(payload)
        username = payload['username']
        password = payload['password']
        db = payload['db']

        if not username or not password or not db:
            raise UserError('Please provide a username and password.')

        try:
            request.session.authenticate(db, username, password)
        except AccessError as aee:
            return invalid_response("Access error", "Error: %s" % aee.name)
        except AccessDenied as ade:
            return invalid_response("Access denied", "Login, password or db invalid")
        except Exception as e:
            # Invalid database:
            info = "The database name is not valid {}".format((e))
            error = "invalid_database"
            _logger.error(info)
            return invalid_response("wrong database name", error, 403)

        uid = request.session.uid
        if not uid:
            error = "authentication failed"
            return invalid_response(401, error, 'Invalid username or password.')

        access_token = _token.find_one_or_create_token(user_id=uid, create=True)
        # Successful response:
        return {
            "uid": uid,
            "access_token": access_token
        }

    @http.route('/api/register', type='json', auth='public', methods=['POST'])
    def register(self, **post):
        _token = request.env["api.access_token"]
        payload = request.httprequest.data.decode()
        payload = json.loads(payload)
        username = payload['username']
        password = payload['password']
        name = payload['name']
        email = payload['email']
        phone = payload['phone']
        db = payload['db']

        if not username or not password or not name or not email or not phone or not db:
            raise UserError('Please provide all required fields.')

        try:
            # Create a new user with the given username and password
            User = http.request.env['res.users']
            company = request.env['res.company'].sudo().search([('name', '=', 'Afya Plug')], limit=1)

            user = User.sudo().create({
                'login': username,
                'name': name,
                'company_id': company.id,
            })

            partner = user.partner_id
            partner.write(
            {
                'name': name,
                'company_type': 'person',
                'country_id': request.env['res.country'].search([('code', '=', 'KE')], limit=1).id,
                'email': email,
                'phone': phone,
                'mobile': phone,
                'function': 'Customer',
                'comment': 'Contact created during signup.',
                'category_id': [
                    (
                        6, 0,
                        [request.env['res.partner.category'].sudo().search([('name', '=', 'Customers')], limit=1).id])
                ],
                'user_id': user.id,
                'company_id': company.id
            })

            # contact = Contact.sudo().create()

            access_token = _token.find_one_or_create_token(user_id=user.id, create=True)

            return {
                "user_id": user.id,
                "contact_id": user.partner_id.id,
                "access_token": access_token
            }

        except Exception as e:
            return UserError(e)

    @http.route('/api/logout', type='json', auth='user')
    def logout(self):
        # Clear the session token to log out the user
        session = request.session
        session.token = None

        # Return a success message
        return {
            'message': 'User logged out successfully.'
        }

    @http.route('/api/user-info', type='json', auth='user')
    def user_info(self):
        # Get the current user's information, contact, and related records
        user = request.env.user
        partner = user.partner_id
        other_records = user.other_records  # replace 'other_records' with the actual name of the related records field

        # Serialize the user, contact, and related records into a dictionary
        data = {
            'user': user.read()[0],
            'partner': partner.read()[0],
            'other_records': other_records.read(),
        }

        # Return the serialized data in the response
        return data
