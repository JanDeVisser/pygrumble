#!/usr/bin/env python
#
# Copyright (c) 2017 Jan de Visser (jan@sweattrails.com)
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#

from setuptools import setup


def readme():
    with open('README.md') as f:
        return f.read()


setup(name='grumble',
      version='0.1',
      description='Python storage and web framework',
      long_description=readme(),
      classifiers=[
          'Development Status :: 3 - Alpha',
          'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
          'Programming Language :: Python :: 2.7',
          'Topic :: Software Development :: Libraries :: Application Frameworks',
      ],
      keywords='framework',
      url='http://github.com/JanDeVisser/grumble',
      author='Jan de Visser',
      author_email='jan@de-visser.net',
      license='GPLv2+',
      packages=['gripe', 'grit', 'grizzle', 'grudge', 'grumble'],
      install_requires=[
          'webob', 'webapp2', 'psycopg2', 'jinja2'
      ],
      test_suite='nose.collector',
      tests_require=['nose', 'nose-cover3'],
      entry_points={
      },
      include_package_data=True,
      zip_safe=False)