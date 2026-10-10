"""Package configuration for the Module 5 GradCafe application."""

from setuptools import setup


setup(
    name="jhu-software-concepts-module5",
    version="1.0.0",
    description="Secure GradCafe data analysis application",
    package_dir={"": "src"},
    py_modules=[
        "app",
        "clean",
        "db_config",
        "load_data",
        "models",
        "orm_queries",
        "query_data",
        "scrape",
        "scrape_records",
        "scrape_storage",
    ],
    install_requires=[
        "Flask",
        "SQLAlchemy",
        "psycopg[binary]",
        "beautifulsoup4",
        "urllib3",
    ],
)
