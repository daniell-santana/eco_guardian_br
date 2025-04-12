from setuptools import setup, find_packages

setup(
    name="eco_guardian",
    version="0.1",
    packages=find_packages(),
    package_dir={"": "."},
    include_package_data=True,
    install_requires=[
        "streamlit",
        "pandas",
        "numpy",
        "scikit-learn",
        "plotly",
        "geopandas",
        "openai",
        "pdfplumber",
        "streamlit-folium",
        "python-dotenv"
    ],
    python_requires=">=3.10",
)
