"""Password login for Salesforce rest & bulk APIs

Modified from https://github.com/simple-salesforce/simple-salesforce/blob/master/simple_salesforce/login.py (Apache 2.0 License)
"""

import xml.dom.minidom as libminidom
import html
import requests
from textwrap import dedent

from tap_salesforce.salesforce.exceptions import TapSalesforceException


DEFAULT_CLIENT_ID_PREFIX = 'tap-salesforce'
DEFAULT_DOMAIN = 'login'
DEFAULT_API_VERSION = '52.0'


def get_first_element_value_from_xml(xml, element_name):
    """
    Extracts an element value from an XML string.

    For example, invoking
    getUniqueElementValueFromXmlString(
        '<?xml version="1.0" encoding="UTF-8"?><foo>bar</foo>', 'foo')
    should return the value 'bar'.
    """
    dom = libminidom.parseString(xml)
    elements = dom.getElementsByTagName(element_name)
    element_value = None
    if len(elements) > 0:
        element_value = (
            elements[0]
            .toxml()
            .replace('<' + element_name + '>', '')
            .replace('</' + element_name + '>', '')
        )
    return element_value


def login_with_password(username: str, password: str, security_token: str):
    username = html.escape(username)
    password = html.escape(password)
    security_token = html.escape(security_token)
    client_id = DEFAULT_CLIENT_ID_PREFIX
    domain = DEFAULT_DOMAIN
    api_version = DEFAULT_API_VERSION

    request_body = dedent(f"""
        <?xml version="1.0" encoding="utf-8" ?>
        <env:Envelope
                xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                xmlns:env="http://schemas.xmlsoap.org/soap/envelope/"
                xmlns:urn="urn:partner.soap.sforce.com">
            <env:Header>
                <urn:CallOptions>
                    <urn:client>{client_id}</urn:client>
                    <urn:defaultNamespace>sf</urn:defaultNamespace>
                </urn:CallOptions>
            </env:Header>
            <env:Body>
                <n1:login xmlns:n1="urn:partner.soap.sforce.com">
                    <n1:username>{username}</n1:username>
                    <n1:password>{password}{security_token}</n1:password>
                </n1:login>
            </env:Body>
        </env:Envelope>
    """).strip()
    url = f'https://{domain}.salesforce.com/services/Soap/u/{api_version}'
    request_headers = {
        'content-type': 'text/xml',
        'charset': 'UTF-8',
        'SOAPAction': 'login'
    }

    import singer
    LOGGER = singer.get_logger()
    LOGGER.info(f'Logging in to Salesforce using username and password through SOAP API: {url=} {request_headers=} {request_body=}')
    LOGGER.info(request_body)

    response = requests.post(url, request_body, headers=request_headers)

    if response.status_code != 200:
        exception_code = get_first_element_value_from_xml(
            response.content, 'sf:exceptionCode')
        exception_message = get_first_element_value_from_xml(
            response.content, 'sf:exceptionMessage')
        raise TapSalesforceException(
            f'Error login in to Salesforce using username and password through SOAP API: {exception_code=} {exception_message=}'
        )
    
    session_id = get_first_element_value_from_xml(response.content, 'sessionId')
    server_url = get_first_element_value_from_xml(response.content, 'serverUrl')

    instance_url = (
        server_url
        .replace('http://', '')
        .replace('https://', '')
        .split('/')[0]
        .replace('-api', '')
    )
    instance_url = f'https://{instance_url}'

    return session_id, instance_url
