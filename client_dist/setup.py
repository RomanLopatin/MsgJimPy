from setuptools import setup, find_packages

setup(name="MsgJimPyClient",
      version="1.1.3",
      description="Client part of jim based messenger ",
      author="Roman Lopatin",
      author_email="romanlopatin@gmail.com",
      packages=find_packages(),
      install_requires=['PyQt5', 'sqlalchemy'],
      # scripts=['server/server_run']
      )