from setuptools import setup

VERSION = '1.0a1'

# this plugin was originally by Jeff Hammel <jhammel@openplans.org>
# but I've substantially altered and maintained it for a while now.

setup(name='TicketMoverPlugin',
      version=VERSION,
      description="move tickets from one Trac to a sibling Trac",
      author='Nathan Bird',
      author_email='nathan@acceleration.net',
      url='https://github.com/UnwashedMeme/TicketMoverPlugin',
      keywords='trac plugin',
      license="BSD",
      py_modules=['ticketmoverplugin'],
      install_requires=[
          'Trac>=1.4',
          'TracSQLHelper==0.2.2'
      ],
      dependency_links=[
          "svn+https://trac-hacks.org/svn/tracsqlhelperscript/0.12/#egg=TracSQLHelper-0.2.2",
      ],
      entry_points={
          'trac.plugins': [
              'ticketmoverplugin=ticketmoverplugin'
          ]
      },
)
