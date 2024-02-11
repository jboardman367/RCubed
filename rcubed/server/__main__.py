from rcubed.server.app import app
from rcubed.server.db import RCubedDB
from argparse import ArgumentParser

parser = ArgumentParser(
    prog='rcubed.server',
    description='R^3 model server'
)

parser.add_argument('db_path')
parser.add_argument('-p', '--port', type=int, default=5151, help='Runs on the provided port. Default 5151')

args = parser.parse_args()

app.config['db'] = args.db_path

app.run(port=args.port, debug=True)
