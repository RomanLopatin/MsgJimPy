from setuptools import setup, find_packages

setup(name="MsgJimPyServer",
      version="1.2.1",
      description="Server part of jim based messenger ",
      author="Roman Lopatin",
      author_email="romanlopatin@gmail.com",
      packages=find_packages(),
      include_package_data=True,
      package_data={"": ["*.ini"]},
      install_requires=['PyQt5', 'sqlalchemy'],
      scripts=['server/server_run'],
      )
