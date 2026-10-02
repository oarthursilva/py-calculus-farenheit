import os


class Config:
    # # security options

    # API documentation
    APIFAIRY_TITLE = 'Calculo Fahrenheit'
    APIFAIRY_VERSION = '1.0'
    APIFAIRY_UI = os.environ.get('DOCS_UI', 'elements')
    APIFAIRY_TAGS = ['fahrenheit']
