from setuptools import setup, find_packages

long_description = '''
### Oxfs

- Oxfs is a network file system like sshfs.
- It is very fast to edit remote files with desktop software.

### Get Start

- https://github.com/RainMark/oxfs
'''

setup(
    name='oxfs',
    version='0.1.3',
    author='RainMark',
    author_email='rain.by.zhou@gmail.com',
    description='A Fast SFTP File System',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/RainMark/oxfs',
    classifiers=[
        'Environment :: MacOS X',
        'Environment :: X11 Applications',
        'Programming Language :: Python :: 3 :: Only',
        'Operating System :: MacOS',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Unix',
        'License :: OSI Approved :: MIT License',
    ],

    packages=find_packages(),
    include_package_data=True,
    zip_safe=True,
    install_requires = [
        'fusepy == 3.0.1',
        'paramiko >= 2.0.0',
        'xxhash >= 1.3.0',
    ],

    entry_points={
        'console_scripts':[
            'oxfs = oxfs.oxfs:main'
        ]
    },
)
