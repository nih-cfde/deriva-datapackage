from setuptools import setup, find_packages

setup(
  name='deriva-datapackage',
  version='1.0.5',
  url='https://github.com/nih-cfde/',
  author='Daniel J. B. Clarke',
  author_email='danieljbclarkemssm@gmail.com',
  long_description=open('README.md', 'r').read(),
  license='Apache-2.0',
  install_requires=list(map(str.strip, open('requirements.txt', 'r').readlines())),
  extras_require={
    'progress_bar': 'tqdm',
  },
  packages=find_packages(),
  include_package_data=True,
)
