from setuptools import setup

VERSION = '1.0'     # hmmm... how to tag forks...

# this plugin was originally by Jeff Hammel <jhammel@openplans.org>
# but I've substantially altered and maintained it for a while now.
# updated for Trac 1.4

setup(name='TicketMoverPlugin',
      version=VERSION,
      description="move tickets from one Trac to a sibling Trac",
      author='Nathan Bird',
      author_email='nathan@acceleration.net',
      url='https://github.com/OnroerendErfgoed/TicketMoverPlugin',
      keywords='trac plugin',
      license="BSD",
      py_modules=['ticketmoverplugin'],
      install_requires=[
          'Trac>=1.4',
          'TracSQLHelper==0.3.1'
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
