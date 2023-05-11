import werkzeug.wrappers
import ast
import functools
import json
import logging
import re
from datetime import datetime, timedelta
from odoo import http, _
from odoo.addons.restful.common import invalid_response, valid_response
from odoo.exceptions import AccessDenied, AccessError, UserError
from odoo.http import request
from dateutil import parser
from pytz import timezone

_logger = logging.getLogger(__name__)


def validate_token(func):

    @functools.wraps(func)
    def wrap(self, *args, **kwargs):
        """."""
        access_token = request.httprequest.headers.get("access_token")
        if not access_token:
            return invalid_response("access_token_not_found", "missing access token in request header", 401)
        access_token_data = (
            request.env["api.access_token"].sudo().search([("token", "=", access_token)], order="id DESC", limit=1)
        )

        if access_token_data.find_one_or_create_token(user_id=access_token_data.user_id.id) != access_token:
            return invalid_response("access_token", "token seems to have expired or invalid", 401)

        request.session.uid = access_token_data.user_id.id
        request.update_env(user=request.session.uid)
        return func(self, *args, **kwargs)

    return wrap

def get_free_slots(events):
        tz = timezone(http.request.env.context.get('tz') or 'UTC')
        start_time = parser.parse(events[0].start).astimezone(tz).replace(minute=0, second=0, microsecond=0)
        end_time = parser.parse(events[-1].stop).astimezone(tz).replace(minute=59, second=59, microsecond=999999)
        free_slots = []

        for event in events:
            event_start = parser.parse(event.start).astimezone(tz)
            event_end = parser.parse(event.stop).astimezone(tz)
            if start_time < event_start:
                free_slots.append((start_time, event_start))
            start_time = event_end

        if start_time < end_time:
            free_slots.append((start_time, end_time))

        return free_slots

class MainController(http.Controller):
    @http.route("/api/user", methods=["POST"], type="http", cors="*", auth="public", csrf=False)
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
        access_token = request.env["api.access_token"].find_one_or_create_token(user_id=user.id, create=True)
        return werkzeug.wrappers.Response(
            status=200,
            content_type="application/json; charset=utf-8",
            headers=[("Cache-Control", "no-store"), ("Pragma", "no-cache")],
            response=json.dumps(
                {
                    "uid": user.id,
                    "partner": partner.id,
                    "access_token": access_token
                }
            ),
        )

    @http.route("/api/nurses", type="http", auth="public", methods=["GET"], csrf=False, cors="*")
    def nurses(self, **kw):
        domain = []
        if kw.get('domain', ''):
            domain = kw.get('domain', '')
            domain = ast.literal_eval(domain)

        fields = []
        if kw.get('fields', ''):
            fields = kw.get('fields', '')
            fields = fields.split(',')

        data = request.env['hr.employee'].sudo().search_read(
            domain=domain, fields=fields
        )
        return valid_response(data)

    @http.route("/api/nurses/<id>", type="http", auth="public", methods=["GET"], csrf=False, cors="*")
    def getNurse(self, id=None, **kw):
        domain = [("id", "=", int(id))]
        fields = []
        if kw.get('fields', ''):
            fields = kw.get('fields', '')
            fields = fields.split(',')

        data = request.env['hr.employee'].sudo().search_read(
            domain=domain, fields=fields
        )
        return valid_response(data[0])

    @validate_token
    @http.route("/api/appointment", type="http", auth="public", methods=["POST"], csrf=False, cors="*")
    def book_appointment(self, **payload):
        payload = request.httprequest.data.decode()
        payload = json.loads(payload)

        nurse_list = request.env['hr.employee'].sudo().search(
            domain=[('id', '=', payload['nurse_id'])]
        )
        nurse = nurse_list[0]

        product_list = request.env['product.product'].sudo().search(
            domain=[('id', '=', payload['product_id'])]
        )
        user = request.env['res.users'].sudo().search(
            domain=[('id', '=', request.uid)]
        )

        product = product_list[0]
        start_datetime_str = payload['start_datetime']
        stop_datetime_str = payload['stop_datetime']

        start_datetime = datetime.strptime(start_datetime_str, '%Y-%m-%d %H:%M:%S')
        stop_datetime = datetime.strptime(stop_datetime_str, '%Y-%m-%d %H:%M:%S')

        appointment = request.env['afyaplug.appointment'].sudo().create({
            'contact_id': user.partner_id.id,
            'nurse_id': nurse.id,
            'product_id': product.id,
            'street': payload['street'],
            'street2': payload['street2'],
            'landmark': payload['landmark'],
            'town': payload['town'],
            'county': payload['county'],
            'appointment_date': start_datetime,
            'appointment_time': stop_datetime
        })

        # Create a new event for the employee in the calendar
        event = request.env['calendar.event'].sudo().create({
            'start': start_datetime,
            'stop': stop_datetime,
            'name': appointment.reference + " - " + user.partner_id.name,
            'partner_ids': [(4, nurse.user_id.partner_id.id), (4, user.partner_id.id)]
        })

        return valid_response(event.id)

    @validate_token
    @http.route("/api/schedule/<id>", type="http", auth="public", methods=["POST"], csrf=False, cors="*")
    def nurses_schedule(self, id=None, **payload):
        nurse = request.env['hr.employee'].sudo().search([('id', '=', id)])
        payload = request.httprequest.data.decode()
        payload = json.loads(payload)

        events = request.env['calendar.event'].sudo().search_read([])
        print(events)
        appointment_date = payload['date']
        return valid_response(events[0]['partner_ids'])

    @http.route('/employee/<int:employee_id>/free_slots', auth='public', type='http', methods=['GET'], csrf=False)
    def get_employee_free_slots(self, employee_id, start_date=None, end_date=None, **kwargs):
        try:
            employee = request.env['hr.employee'].sudo().search([('id', '=', employee_id)])
        except:
            raise UserError(_('Invalid employee ID'))


        partner_id = employee.read(['user_partner_id'])[0]['user_partner_id'][0]

        calendar = request.env['calendar.event'].sudo().search([
            ('start', '>=', datetime.now()),
            ('partner_ids', 'in', [partner_id]),
        ], order='start asc')
        print(calendar)
        if calendar:
            return valid_response(calendar.read())
        else:
            return valid_response({'message': 'No events found'})



