from http.server import BaseHTTPRequestHandler
import os
import requests
import json
from datetime import datetime

OG_PASSWORD = os.getenv('OG_PASSWORD')


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods',
                         'GET, POST, PATCH, OPTIONS')
        self.send_header('Access-Control-Allow-Headers',
                         'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version')
        self.end_headers()
        return

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        request_body = self.rfile.read(content_length).decode('utf-8')

        data = json.loads(request_body)

        try:
            event_type = data['type']
            if event_type != "order.success":
                self.send_response(400)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                return

            og_order_id = data['data']['object']['public_id']
            customer = data['data']['object']['customer']

            next_order_date = get_first_date_of_next_month()

            print(event_type, og_order_id, customer, next_order_date)

            if og_order_id and customer:
                response = requests.get(
                    f"https://restapi.ordergroove.com/orders/?customer={customer}&status=1",
                    headers={
                        "accept": "application/json",
                        "x-api-key": OG_PASSWORD
                    })
                
                orders = response.json()

                for order in orders['results']:
                    current_place_datetime_str = order['place']
                    current_place_datetime = datetime.strptime(current_place_datetime_str, "%Y-%m-%d %H:%M:%S")
                    current_place_date = current_place_datetime.strftime("%Y-%m-%d")

                    if current_place_date != next_order_date:

                        # Call Ordergroove API
                        response = requests.patch(
                            url=f"https://restapi.ordergroove.com/orders/{order['public_id']}/change_place_date/",
                            headers={
                                "accept": "application/json",
                                "content-type": "application/json",
                                "x-api-key": OG_PASSWORD
                            },
                            json={
                                "place": f"{next_order_date} 00:00:00"
                            }
                        )

                        if response.status_code == 200:
                            print(f"Order {order['public_id']} place date updated to {next_order_date}")

                    else:
                        print(f"Order {order['public_id']} already has the correct place date")

            self.send_response(response.status_code)
            self.send_header('Content-type', response.headers['Content-Type'])
            self.end_headers()
            self.wfile.write(response.content)
            return

        except Exception as e:
            print(e)
            self.send_response(400)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            return


def get_first_date_of_next_month():
    today = datetime.today()

    if today.day < 7:
        next_month = (today.month % 12) + 1
        year = today.year if next_month != 1 else today.year + 1

    else:
        next_month = ((today.month + 1) % 12) + 1
        year = today.year if next_month > 1 else today.year + 1

    return f"{year:04d}-{next_month:02d}-01"
