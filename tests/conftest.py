import re
import textwrap

from amazonproduct import utils

def pytest_addoption(parser):
    group = parser.getgroup('amazonproduct',
        'custom options for testing python-amazon-product-api')
    group._addoption('--locale', action='append', dest='locales',
        metavar='LOCALE', help='Locale to use (e.g. "de" or "us"). This option '
            'can be used more than once. Note that tests with specific locales '
            'defined which do not match the ones specified by this option will '
            'NOT be run.')
    group._addoption('--api-version', action='append', dest='versions',
        metavar='VERSION', help='API version to use (e.g. "2010-09-01"). This '
            'option can be used more than once. Note that tests with specific '
            'versions defined which do not match the ones specified by this '
            'option will NOT be run.')
    group._addoption('--refetch', action='store', type='choice', dest='fetch',
        metavar='method', choices=['no', 'missing', 'outdated', 'all'],
        default='no', help='Fetch responses from live server and overwrite '
            'previously cached XML file: one of no (default)|missing|outdated|'
            'all.')


def pytest_funcarg__server(request):
    """
    Is the same as funcarg `httpserver` from plugin pytest-localserver with the
    difference that it has a module-wide scope.
    """
    def setup():
        try:
            localserver = request.config.pluginmanager.getplugin('localserver')
        except KeyError:
            raise pytest.skip('This test needs plugin pytest-localserver!')
        server = localserver.http.Server()
        server.start()
        return server
    def teardown(server):
        server.stop()
    return request.cached_setup(setup, teardown, 'module')


class DummyConfig (object):

    """
    Dummy config to which to which you can add config files which in turn will
    be created on the file system as temporary files.
    """

    _file_counter = 0

    def __init__(self, tmpdir):
        self.tmpdir = tmpdir
        self.files = []

    def add_file(self, content, path=None):
        """
        Writes one temporary file.
        """
        if not path:
            path = 'config-%i' % self._file_counter
            self._file_counter += 1
        p = self.tmpdir.ensure(path)
        p.write(textwrap.dedent(content))
        self.files += [p.strpath]

    _REG = re.compile(r'^#\s*file:\s+(.+?)\n', re.DOTALL | re.MULTILINE)
    def load_from_string(self, content):
        """
        Creates config files from string which is split up into file blocks and
        written to temporary files.
        """
        last = 0 # end of the last matching '# file: XXX'
        path = None # path of the last matching '# file: XXX'
        for m in self._REG.finditer(content):
            if path is not None:
                self.add_file(content[last:m.start()], path)
            path = m.group(1)
            last = m.end()
        if path is not None:
            self.add_file(content[last:], path)
        else:
            raise ValueError('Where are the file paths?')

    def __repr__(self):
        return '<DummyConfig %s files=%r>' % (id(self), self.files)


def pytest_funcarg__configfiles(request):
    """
    Returns a dummy config to which you can add config files which in turn will
    be created on the file system as temporary files. You can use the following
    methods:

    To add a single config file use ``configfiles.add_file(content, path)``. If
    you omit the ``path``, some arbitrary file name is used. ::

        configfiles.add_file('''
            [Credentials]
            aws_access_key_id = ABCDEFGH12345
            aws_secret_access_key = abcdegf43
            aws_product_locale = de''', path='/etc/amazon.config')

    In order to add multiple config files at once, you can use the following
    method::

        configfiles.load_from_string('''
        # file: /etc/boto.cfg
        [Credentials]
        aws_access_key_id = Hhdjksaiunkljfl
        aws_secret_access_key = difioemLjdks02
        
        # file: /home/user/.amazon-product-api
        [Credentials]
        aws_product_locale = de
        ''') 

    """
    tmpdir = request.getfuncargvalue('tmpdir')
    monkeypatch = request.getfuncargvalue('monkeypatch')
    cfg = DummyConfig(tmpdir)
    monkeypatch.setattr(utils, 'CONFIG_FILES', cfg.files)
    return cfg