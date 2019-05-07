from setuptools import setup, find_packages

with open('README.md', 'r') as inf:
    long_description = inf.read()

setup(
    name='oxfs',
    version='0.0.2',
    author='RainMark',
    author_email='rain.by.zhou@gmail.com',
    description='A simple and powerful sftp filesystem.',
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

    # packages= ['oxfs']
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
