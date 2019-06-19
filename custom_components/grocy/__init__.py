"""
The integration for grocy.
"""
import logging
import os
from datetime import timedelta

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.const import CONF_API_KEY, CONF_URL
from homeassistant.helpers import discovery
from homeassistant.util import Throttle

from .const import (CONF_ENABLED, CONF_NAME, CONF_SENSOR, DEFAULT_NAME, DOMAIN,
                    DOMAIN_DATA, ISSUE_URL, PLATFORMS, REQUIRED_FILES, STARTUP,
                    VERSION)

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=30)

_LOGGER = logging.getLogger(__name__)

SENSOR_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_ENABLED, default=True): cv.boolean,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_URL): cv.string,
                vol.Required(CONF_API_KEY): cv.string,
                vol.Optional(CONF_SENSOR): vol.All(cv.ensure_list, [SENSOR_SCHEMA]),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

from datetime import datetime
from typing import List
from enum import Enum

import requests

import iso8601

def urljoin(first, second):
    return first + second

def parse_date(input_value):
    if input_value is None:
        return None
    return iso8601.parse_date(input_value)


def parse_int(input_value, default_value=None):
    if input_value is None:
        return default_value
    try:
        return int(input_value)
    except ValueError:
        return default_value


def parse_float(input_value, default_value=None):
    if input_value is None:
        return default_value
    try:
        return float(input_value)
    except ValueError:
        return default_value

class QuantityUnitData(object):
    def __init__(self, parsed_json):
        self._id = parse_int(parsed_json.get('id'))
        self._name = parsed_json.get('name')
        self._name_plural = parsed_json.get('name_plural')
        self._description = parsed_json.get('description')
        self._row_created_timestamp = parse_date(parsed_json.get('row_created_timestamp'))


class LocationData(object):
    def __init__(self, parsed_json):
        self._id = parse_int(parsed_json.get('id'))
        self._name = parsed_json.get('name')
        self._description = parsed_json.get('description')
        self._row_created_timestamp = parse_date(parsed_json.get('row_created_timestamp'))


class ProductData(object):
    def __init__(self, parsed_json):
        self._id = parse_int(parsed_json.get('id'))
        self._name = parsed_json.get('name')
        self._description = parsed_json.get('description', None)
        self._location_id = parse_int(parsed_json.get('location_id', None))
        self._qu_id_stock = parse_int(parsed_json.get('qu_id_stock', None))
        self._qu_id_purchase = parse_int(parsed_json.get('qu_id_purchsase', None))
        self._qu_factor_purchase_to_stock = parse_float(parsed_json.get('qu_factor_purchase_to_stock', None))
        self._barcodes = parsed_json.get('barcode', "").split(",")
        self._picture_file_name = parsed_json.get('picture_file_name', None)
        self._allow_partial_units_in_stock = bool(parsed_json.get('allow_partial_units_in_stock', None) == "true")
        self._row_created_timestamp = parse_date(parsed_json.get('row_created_timestamp', None))
        self._min_stock_amount = parse_int(parsed_json.get('min_stock_amount', None), 0)
        self._default_best_before_days = parse_int(parsed_json.get('default_best_before_days', None))

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name


class ChoreData(object):
    def __init__(self, parsed_json):
        self._id = parse_int(parsed_json.get('id'))
        self._name = parsed_json.get('name')

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name


class UserDto(object):
    def __init__(self, parsed_json):
        self._id = parse_int(parsed_json.get('id'))

        self._username = parsed_json.get('username')


class CurrentChoreResponse(object):
    def __init__(self, parsed_json):
        self._chore_id = parse_int(parsed_json.get('chore_id'), None)
        self._last_tracked_time = parse_date(parsed_json.get('last_tracked_time'))
        self._next_estimated_execution_time = parse_date(parsed_json.get('next_estimated_execution_time'))

    @property
    def chore_id(self) -> int:
        return self._chore_id

    @property
    def last_tracked_time(self) -> datetime:
        return self._last_tracked_time

    @property
    def next_estimated_execution_time(self) -> datetime:
        return self._next_estimated_execution_time


class CurrentVolatilStockResponse(object):
    def __init__(self, parsed_json):
        self._expiring_products = [ProductData(product) for product in parsed_json.get('expiring_products')]
        self._expired_products = [ProductData(product) for product in parsed_json.get('expired_products')]
        self._missing_products = [ProductData(product) for product in parsed_json.get('missing_products')]

    @property
    def expiring_products(self) -> List[ProductData]:
        return self._expiring_products

    @property
    def expired_products(self) -> List[ProductData]:
        return self._expired_products

    @property
    def missing_products(self) -> List[ProductData]:
        return self._missing_products


class CurrentStockResponse(object):
    def __init__(self, parsed_json):
        self._product_id = parse_int(parsed_json.get('product_id'))
        self._amount = parse_float(parsed_json.get('amount'))
        self._best_before_date = parse_date(parsed_json.get('best_before_date'))

    @property
    def product_id(self) -> int:
        return self._product_id

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def best_before_date(self) -> datetime:
        return self._best_before_date


class ProductDetailsResponse(object):
    def __init__(self, parsed_json):
        self._last_purchased = parse_date(parsed_json.get('last_purchased'))
        self._last_used = parse_date(parsed_json.get('last_used'))
        self._stock_amount = parse_int(parsed_json.get('stock_amount'))
        self._stock_amount_opened = parse_int(parsed_json.get('stock_amount_opened'))
        self._next_best_before_date = parse_date(parsed_json.get('next_best_before_date'))
        self._last_price = parse_float(parsed_json.get('last_price'))

        self._product = ProductData(parsed_json.get('product'))

        self._quantity_unit_purchase = QuantityUnitData(parsed_json.get('quantity_unit_purchase'))
        self._quantity_unit_stock = QuantityUnitData(parsed_json.get('quantity_unit_stock'))

        self._location = LocationData(parsed_json.get('location'))

    @property
    def last_purchased(self) -> datetime:
        return self._last_purchased

    @property
    def last_used(self) -> datetime:
        return self._last_used

    @property
    def stock_amount(self) -> int:
        return self._stock_amount

    @property
    def stock_amount_opened(self) -> int:
        return self._stock_amount_opened

    @property
    def next_best_before_date(self) -> datetime:
        return self._next_best_before_date

    @property
    def last_price(self) -> float:
        return self._last_price

    @property
    def product(self) -> ProductData:
        return self._product


class ChoreDetailsResponse(object):
    def __init__(self, parsed_json):
        self._chore = ChoreData(parsed_json.get('chore'))
        self._last_done_by = UserDto(parsed_json.get('last_done_by'))

    @property
    def chore(self) -> ChoreData:
        return self._chore


class TransactionType(Enum):
    PURCHASE = "purchase"
    CONSUME = "consume"
    INVENTORY_CORRECTION = "inventory-correction"
    PRODUCT_OPENED = "product-opened"


class GrocyApiClient(object):
    def __init__(self, base_url, api_key):
        self._base_url = base_url
        self._api_key = api_key
        self._headers = {
            "accept": "application/json",
            "GROCY-API-KEY": api_key
        }

    def get_stock(self) -> List[CurrentStockResponse]:
        req_url = urljoin(self._base_url, "stock")
        resp = requests.get(req_url, headers=self._headers)
        if resp.status_code != 200 or len(resp.text) == 0:
            return
        parsed_json = resp.json()
        return [CurrentStockResponse(response) for response in parsed_json]

    def get_volatile_stock(self) -> CurrentVolatilStockResponse:
        req_url = urljoin(self._base_url, "stock/volatile")
        resp = requests.get(req_url, headers=self._headers)
        parsed_json = resp.json()
        return CurrentVolatilStockResponse(parsed_json)

    def get_product(self, product_id) -> ProductDetailsResponse:
        req_url = urljoin(urljoin(self._base_url, "stock/products/"), str(product_id))
        resp = requests.get(req_url, headers=self._headers)
        if resp.status_code != 200 or len(resp.text) == 0:
            return
        parsed_json = resp.json()
        return ProductDetailsResponse(parsed_json)

    def get_chores(self) -> List[CurrentChoreResponse]:
        req_url = urljoin(self._base_url, "chores")
        resp = requests.get(req_url, headers=self._headers)
        parsed_json = resp.json()
        return [CurrentChoreResponse(chore) for chore in parsed_json]

    def get_chore(self, chore_id: int) -> ChoreDetailsResponse:
        req_url = urljoin(urljoin(self._base_url, "chores/"), str(chore_id))
        resp = requests.get(req_url, headers=self._headers)
        parsed_json = resp.json()
        return ChoreDetailsResponse(parsed_json)

    def add_product(self, product_id, amount: float, price: float, best_before_date: datetime = None,
                    transaction_type: TransactionType = TransactionType.PURCHASE):
        data = {
            "amount": amount,
            "transaction_type": transaction_type.value,
            "price": price
        }

        if best_before_date is not None:
            data["best_before_date"] = best_before_date.isoformat()

        req_url = urljoin(urljoin(urljoin(self._base_url, "stock/products/"), str(product_id) + "/"), "add")
        requests.post(req_url, headers=self._headers, data=data)

    def consume_product(self, product_id: int, amount: float = 1, spoiled: bool = False,
                        transaction_type: TransactionType = TransactionType.CONSUME):
        data = {
            "amount": amount,
            "spoiled": spoiled,
            "transaction_type": transaction_type.value
        }

        req_url = urljoin(urljoin(urljoin(self._base_url, "stock/products/"), str(product_id) + "/"), "consume")
        requests.post(req_url, headers=self._headers, data=data)

class Product(object):
    def __init__(self, stock_response: CurrentStockResponse):
        self._product_id = stock_response.product_id
        self._available_amount = stock_response.amount
        self._best_before_date = stock_response.best_before_date

        self._name = None

    def get_details(self, api_client: GrocyApiClient):
        details = api_client.get_product(self.product_id)
        if details is None:
            return
        self._name = details.product.name

    @property
    def name(self) -> str:
        return self._name

    @property
    def product_id(self) -> int:
        return self._product_id

    @property
    def available_amount(self) -> float:
        return self._available_amount

    @property
    def best_before_date(self) -> datetime:
        return self._best_before_date


class Chore(object):
    def __init__(self, raw_chore: CurrentChoreResponse):
        self._chore_id = raw_chore.chore_id
        self._last_tracked_time = raw_chore.last_tracked_time
        self._next_estimated_execution_time = raw_chore.next_estimated_execution_time
        self._name = None

    def get_details(self, api_client: GrocyApiClient):
        details = api_client.get_chore(self.chore_id)
        self._name = details.chore.name

    @property
    def chore_id(self) -> int:
        return self._chore_id

    @property
    def last_tracked_time(self) -> datetime:
        return self._last_tracked_time

    @property
    def next_estimated_execution_time(self) -> datetime:
        return self._next_estimated_execution_time

    @property
    def name(self) -> str:
        return self._name


class Grocy(object):
    def __init__(self, base_url, api_key):
        self._api_client = GrocyApiClient(base_url, api_key)

    def stock(self, get_details: bool = False) -> List[Product]:
        raw_stock = self._api_client.get_stock()
        if raw_stock is None:
            return
        stock = [Product(resp) for resp in raw_stock]

        if get_details:
            for item in stock:
                item.get_details(self._api_client)
        return stock

    def volatile_stock(self) -> CurrentVolatilStockResponse:
        return self._api_client.get_volatile_stock()

    def expiring_products(self) -> List[ProductData]:
        return self.volatile_stock().expiring_products

    def expired_products(self) -> List[ProductData]:
        return self.volatile_stock().expired_products

    def missing_products(self) -> List[ProductData]:
        return self.volatile_stock().missing_products

    def product(self, product_id: int) -> ProductDetailsResponse:
        return self._api_client.get_product(product_id)

    def chores(self, get_details: bool = False) -> List[Chore]:
        raw_chores = self._api_client.get_chores()
        chores = [Chore(chore) for chore in raw_chores]

        if get_details:
            for chore in chores:
                chore.get_details(self._api_client)
        return chores

    def chore(self, chore_id: int) -> ChoreDetailsResponse:
        return self._api_client.get_chore(chore_id)

    def add_product(self, product_id, amount: float, price: float, best_before_date: datetime = None,
                    transaction_type: TransactionType = TransactionType.PURCHASE):
        return self._api_client.add_product(product_id, amount, price, best_before_date, transaction_type)

    def consume_product(self, product_id: int, amount: float = 1, spoiled: bool = False,
                        transaction_type: TransactionType = TransactionType.CONSUME):
        return self._api_client.consume_product(product_id, amount, spoiled, transaction_type)


async def async_setup(hass, config):
    """Set up this component."""

    # Print startup message
    startup = STARTUP.format(name=DOMAIN, version=VERSION, issueurl=ISSUE_URL)
    _LOGGER.info(startup)

    # Check that all required files are present
    file_check = await check_files(hass)
    if not file_check:
        return False

    # Create DATA dict
    hass.data[DOMAIN_DATA] = {}

    # Get "global" configuration.
    url = config[DOMAIN].get(CONF_URL)
    api_key = config[DOMAIN].get(CONF_API_KEY)

    # Configure the client.
    grocy = Grocy(url, api_key)
    hass.data[DOMAIN_DATA]["client"] = GrocyData(hass, grocy)

    # Load platforms
    for platform in PLATFORMS:
        # Get platform specific configuration
        platform_config = config[DOMAIN].get(platform, {})

        # If platform is not enabled, skip.
        if not platform_config:
            continue

        for entry in platform_config:
            entry_config = entry

            # If entry is not enabled, skip.
            if not entry_config[CONF_ENABLED]:
                continue

            hass.async_create_task(
                discovery.async_load_platform(
                    hass, platform, DOMAIN, entry_config, config
                )
            )

    def handle_add_product(call):
        product_id = call.data['product_id']
        amount = call.data.get('amount', 0)
        price = call.data.get('price', None)
        grocy.add_product(product_id, amount, price)

    hass.services.async_register(DOMAIN, "add_product", handle_add_product)

    def handle_consume_product(call):
        product_id = call.data['product_id']
        amount = call.data.get('amount', 0)
        spoiled = call.data.get('spoiled', False)

        transaction_type_raw = call.data.get('transaction_type', None)
        transaction_type = TransactionType.CONSUME
        
        if transaction_type_raw is not None:
            transaction_type = TransactionType[transaction_type_raw]
        grocy.consume_product(product_id, amount, spoiled=spoiled, transaction_type=transaction_type)

    hass.services.async_register(DOMAIN, "consume_product", handle_consume_product)
    
    return True


class GrocyData:
    """This class handle communication and stores the data."""

    def __init__(self, hass, client):
        """Initialize the class."""
        self.hass = hass
        self.client = client

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def update_data(self):
        """Update data."""
        # This is where the main logic to update platform data goes.
        try:
            stock = self.client.stock(get_details=True)
            self.hass.data[DOMAIN_DATA]["stock"] = stock
        except Exception as error:  # pylint: disable=broad-except
            _LOGGER.error("Could not update data - %s", error)


async def check_files(hass):
    """Return bool that indicates if all files are present."""
    # Verify that the user downloaded all files.
    base = "{}/custom_components/{}/".format(hass.config.path(), DOMAIN)
    missing = []
    for file in REQUIRED_FILES:
        fullpath = "{}{}".format(base, file)
        if not os.path.exists(fullpath):
            missing.append(file)

    if missing:
        _LOGGER.critical("The following files are missing: %s", str(missing))
        returnvalue = False
    else:
        returnvalue = True

    return returnvalue
