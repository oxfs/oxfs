from setuptools import setup, find_packages

with open('README.md', 'r') as inf:
    long_description = inf.read()

setup(
    name='oxfs',
    version='0.0.1',
    author='RainMark',
    author_email='rain.by.zhou@gmail.com',
    description='A simple and powerfull sftp filesystem.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/pypa/sampleproject',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],

    # packages= ['oxfs']
    packages=find_packages(),
    include_package_data=True,
    zip_safe=True,
    install_requires = [
        'paramiko >= 2.4.2',
        'xxhash >= 1.3.0',
    ],

    entry_points={
        'console_scripts':[
            'oxfs = oxfs.oxfs:main'
        ]
    },
)
