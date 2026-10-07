from setuptools import find_packages, setup

package_name = 'interprete_ordenes'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='equipo',
    maintainer_email='equipo@esan.edu.pe',
    description='Interpretación de órdenes en lenguaje natural para el Gran Reto JetCobot',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'interprete = interprete_ordenes.interprete_ordenes:main',
        ],
    },
)
