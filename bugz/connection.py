import os
import sys
import urllib.error
import urllib.parse
import xmlrpc.client

from bugz.configfile import get_config_option
from bugz.exceptions import BugzError
from bugz.log import log_debug, log_error, log_info
from bugz.log import log_setDebugLevel, log_setQuiet
from bugz.tokens import Tokens
from bugz.utils import terminal_width


class Connection:
	def __init__(self, args, config):
		for key in vars(args):
			setattr(self, key, getattr(args, key))

		if not hasattr(self, 'connection'):
			if config.has_option('default', 'connection'):
				self.connection = get_config_option(config.get,
					'default', 'connection')
			else:
				log_error('No default connection specified')
				sys.exit(1)

		if self.connection not in config.sections():
			log_error('connection "{0}" not found'.format(self.connection))
			sys.exit(1)

		if not hasattr(self, 'base'):
			if config.has_option(self.connection, 'base'):
				self.base = get_config_option(config.get,
					self.connection, 'base')
			else:
				log_error('No base URL specified')
				sys.exit(1)

		if not hasattr(self, 'component'):
			if config.has_option(self.connection, 'component'):
				self.component = get_config_option(config.get,
					self.connection, 'component')

		if not hasattr(self, 'user'):
			if config.has_option(self.connection, 'user'):
				self.user = get_config_option(config.get,
					self.connection, 'user')

		if not hasattr(self, 'password'):
			if config.has_option(self.connection, 'password'):
				self.password = get_config_option(config.get,
					self.connection, 'password')

		if not hasattr(self, 'passwordcmd'):
			if config.has_option(self.connection, 'passwordcmd'):
				self.passwordcmd = get_config_option(config.get,
					self.connection, 'passwordcmd')

		if not hasattr(self, 'product'):
			if config.has_option(self.connection, 'product'):
				self.product = get_config_option(config.get,
					self.connection, 'product')

		if not hasattr(self, 'columns'):
			if config.has_option(self.connection, 'columns'):
				self.columns = get_config_option(config.getint,
					self.connection, 'columns')
			else:
				self.columns = terminal_width()

		if not hasattr(self, 'debug'):
			if config.has_option(self.connection, 'debug'):
				self.debug = get_config_option(config.getint,
					self.connection, 'debug')
			else:
				self.debug = 0
		log_setDebugLevel(self.debug)

		if not hasattr(self, 'quiet'):
			if config.has_option(self.connection, 'quiet'):
				self.quiet = get_config_option(config.getboolean,
					self.connection, 'quiet')
			else:
				self.quiet = False
		log_setQuiet(self.quiet)

		if config.has_option(self.connection, 'search_statuses'):
			self.search_statuses = get_config_option(config.get, self.connection,
					'search_statuses').split()

		if not hasattr(self, 'skip_auth'):
			if config.has_option(self.connection, 'skip_auth'):
				self.skip_auth = get_config_option(config.getboolean,
					self.connection, 'skip_auth')
			else:
				self.skip_auth = False

		if getattr(self, 'encoding', None) is not None:
			log_info('The encoding option is deprecated.')

		self.bz = xmlrpc.client.ServerProxy(self.base)
		self.connections = config.sections()

		parse_result = urllib.parse.urlparse(self.base)
		new_netloc = parse_result.netloc.split('@')[-1]
		self.safe_base = parse_result._replace(netloc=new_netloc).geturl()
		self.tokens = Tokens()
		self.bz_token = None

		old_token_file = os.path.join(os.environ['HOME'], '.bugz_token')
		try:
			old_token = open(old_token_file).read().strip()
			self.save_token(old_token)
			os.remove(old_token_file)
			print('Your ~/.bugz_token file was moved to ~/.bugz_tokens')
			print('The token was assigned to the {0} connection'
					.format(self.connection))
			print('If this is not correct, please edit ~/.bugz_tokens')
			print('and adjust the name of the connection.')
			print('This is the name enclosed in square brackets.')
			print('The connections command lists known connections.')
		except (IOError, OSError):
			pass

		log_info("Using [{0}] ({1})".format(self.connection, self.safe_base))

		log_debug('Command line debug dump:', 3)
		for key in vars(args):
			log_debug('{0}, {1}'.format(key, getattr(args, key)), 3)

		log_debug('Connection debug dump:', 3)
		for key in vars(self):
			log_debug('{0}, {1}'.format(key, getattr(self, key)), 3)

	def load_token(self):
		self.bz_token = self.tokens.get_token(self.connection)

	def save_token(self, bz_token):
		self.tokens.set_token(self.connection, bz_token)
		self.tokens.save_tokens()

	def destroy_token(self):
		self.bz_token = None
		self.tokens.remove_token(self.connection)
		self.tokens.save_tokens()

	def call_bz(self, method, params):
		"""Attempt to call method with args.
		"""
		if self.bz_token is not None:
			params['Bugzilla_token'] = self.bz_token
		try:
			return method(params)
		except xmlrpc.client.Fault as fault:
			raise BugzError('Bugzilla error: {0}'.format(fault.faultString))
		except xmlrpc.client.ProtocolError as e:
			raise BugzError(e)
		except urllib.error.URLError as e:
			raise BugzError(e)
