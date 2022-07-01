from setuptools import setup, find_packages

setup(name="MsgJimPyServer",
      version="1.2.3",
      description="Server part of jim based messenger ",
      author="Roman Lopatin",
      author_email="romanlopatin@gmail.com",
      packages=find_packages(),
      # package_dir={"": "server"},
      include_package_data=True,
      package_data={"": ["*.ini"]},
      install_requires=['PyQt5', 'sqlalchemy'],
      # package_data={"server": ["*.txt", "*.rst", "*.ini"]}
      # scripts=['server/server_run']
      )
