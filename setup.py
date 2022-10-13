from setuptools import setup, find_packages

long_description = '''
### Oxfs

Oxfs is a user-space network file system similar to SSHFS, and the underlying data transfer is based on the SFTP protocol. Oxfs introduces an asynchronous refresh policy to solve the jamming problem caused by the mismatch between network speed and user operation file speed. When Oxfs writes a file, it first writes to the local cache file and submits an asynchronous update task to update the content to the remote host. Similarly, when reading a file, it is preferred to read from a local cache file. Oxfs's data cache eventually falls to disk, and even if it is remounted, the history cache can still be used.

### Get Start

- https://oxfs.io
'''

setup(
    name='oxfs',
    version='0.5.3',
    author='RainMark',
    author_email='rain.by.zhou@gmail.com',
    description='A Fast SFTP File System',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/oxfs/oxfs',
    classifiers=[
        'Operating System :: Unix',
        'Operating System :: MacOS',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3 :: Only',
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
