from setuptools import setup

version_namespace = {}
with open('sign_sync/version.py') as f:
    exec(f.read(), version_namespace)

setup(name='sign_sync_standalone',
      version=version_namespace['__version__'],
      description='Standalone version of Sign Sync for syncing users into Adobe Sign',
      classifiers=[
          'Development Status :: 4 - Beta',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'License :: OSI Approved :: MIT License',
          'Intended Audience :: Developers',
          'Intended Audience :: System Administrators',
      ],
      maintainer='Nathan Nguyen',
      maintainer_email='nnguyen@adobe.com',
      license='MIT',
      packages=['sign_sync', 'sign_sync.connections'],
      install_requires=[
          'apscheduler',
          'cryptography',
          'PyJWT',
          'PyYAML',
          'python-ldap',
          'requests',
          'six',
          'umapi-client'
      ]
)
