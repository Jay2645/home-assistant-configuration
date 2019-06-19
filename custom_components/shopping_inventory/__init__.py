"""Support to manage a shopping inventory."""
import asyncio
import logging
import uuid

import voluptuous as vol

from homeassistant.const import HTTP_NOT_FOUND, HTTP_BAD_REQUEST
from homeassistant.core import callback
from homeassistant.components import http
from homeassistant.components.http.data_validator import (
    RequestDataValidator)
from homeassistant.helpers import intent
import homeassistant.helpers.config_validation as cv
from homeassistant.util.json import load_json, save_json
from homeassistant.components import websocket_api

ATTR_NAME = 'name'

DOMAIN = 'shopping_inventory'
_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = vol.Schema({DOMAIN: {}}, extra=vol.ALLOW_EXTRA)
EVENT = 'shopping_inventory_updated'
INTENT_ADD_ITEM = 'HassShoppingInventoryAddItem'
INTENT_LAST_ITEMS = 'HassShoppingInventoryLastItems'
ITEM_UPDATE_SCHEMA = vol.Schema({
    'complete': bool,
    ATTR_NAME: str,
})
PERSISTENCE = '.shopping_inventory.json'

SERVICE_ADD_ITEM = 'add_item'
SERVICE_COMPLETE_ITEM = 'complete_item'

SERVICE_ITEM_SCHEMA = vol.Schema({
    vol.Required(ATTR_NAME): vol.Any(None, cv.string)
})

WS_TYPE_SHOPPING_INVENTORY_ITEMS = 'shopping_inventory/items'
WS_TYPE_SHOPPING_INVENTORY_ADD_ITEM = 'shopping_inventory/items/add'
WS_TYPE_SHOPPING_INVENTORY_UPDATE_ITEM = 'shopping_inventory/items/update'
WS_TYPE_SHOPPING_INVENTORY_CLEAR_ITEMS = 'shopping_inventory/items/clear'

SCHEMA_WEBSOCKET_ITEMS = \
    websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend({
        vol.Required('type'): WS_TYPE_SHOPPING_INVENTORY_ITEMS
    })

SCHEMA_WEBSOCKET_ADD_ITEM = \
    websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend({
        vol.Required('type'): WS_TYPE_SHOPPING_INVENTORY_ADD_ITEM,
        vol.Required('name'): str
    })

SCHEMA_WEBSOCKET_UPDATE_ITEM = \
    websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend({
        vol.Required('type'): WS_TYPE_SHOPPING_INVENTORY_UPDATE_ITEM,
        vol.Required('item_id'): str,
        vol.Optional('name'): str,
        vol.Optional('complete'): bool
    })

SCHEMA_WEBSOCKET_CLEAR_ITEMS = \
    websocket_api.BASE_COMMAND_MESSAGE_SCHEMA.extend({
        vol.Required('type'): WS_TYPE_SHOPPING_INVENTORY_CLEAR_ITEMS
    })


@asyncio.coroutine
def async_setup(hass, config):
    """Initialize the shopping inventory."""
    @asyncio.coroutine
    def add_item_service(call):
        """Add an item with `name`."""
        data = hass.data[DOMAIN]
        name = call.data.get(ATTR_NAME)
        if name is not None:
            data.async_add(name)

    @asyncio.coroutine
    def complete_item_service(call):
        """Mark the item provided via `name` as completed."""
        data = hass.data[DOMAIN]
        name = call.data.get(ATTR_NAME)
        if name is None:
            return
        try:
            item = [item for item in data.items if item['name'] == name][0]
        except IndexError:
            _LOGGER.error("Removing of item failed: %s cannot be found", name)
        else:
            data.async_update(item['id'], {'name': name, 'complete': True})

    data = hass.data[DOMAIN] = ShoppingInventoryData(hass)
    yield from data.async_load()

    intent.async_register(hass, AddInventoryItemIntent())
    intent.async_register(hass, InventoryTopItemsIntent())

    hass.services.async_register(
        DOMAIN, SERVICE_ADD_ITEM, add_item_service, schema=SERVICE_ITEM_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_COMPLETE_ITEM, complete_item_service,
        schema=SERVICE_ITEM_SCHEMA
    )

    hass.http.register_view(ShoppingInventoryView)
    hass.http.register_view(CreateShoppingInventoryItemView)
    hass.http.register_view(UpdateShoppingInventoryItemView)
    hass.http.register_view(ClearCompletedInventoryItemsView)

    hass.components.conversation.async_register(INTENT_ADD_ITEM, [
        'Add [the] [a] [an] {item} to my shopping inventory',
    ])
    hass.components.conversation.async_register(INTENT_LAST_ITEMS, [
        'What is on my shopping inventory'
    ])

    hass.components.frontend.async_register_built_in_panel(
        'shopping-inventory', 'shopping_inventory', 'mdi:cart')

    hass.components.websocket_api.async_register_command(
        WS_TYPE_SHOPPING_INVENTORY_ITEMS,
        websocket_handle_items,
        SCHEMA_WEBSOCKET_ITEMS)
    hass.components.websocket_api.async_register_command(
        WS_TYPE_SHOPPING_INVENTORY_ADD_ITEM,
        websocket_handle_add,
        SCHEMA_WEBSOCKET_ADD_ITEM)
    hass.components.websocket_api.async_register_command(
        WS_TYPE_SHOPPING_INVENTORY_UPDATE_ITEM,
        websocket_handle_update,
        SCHEMA_WEBSOCKET_UPDATE_ITEM)
    hass.components.websocket_api.async_register_command(
        WS_TYPE_SHOPPING_INVENTORY_CLEAR_ITEMS,
        websocket_handle_clear,
        SCHEMA_WEBSOCKET_CLEAR_ITEMS)

    return True


class ShoppingInventoryData:
    """Class to hold shopping inventory data."""

    def __init__(self, hass):
        """Initialize the shopping inventory."""
        self.hass = hass
        self.items = []

    @callback
    def async_add(self, name):
        """Add a shopping inventory item."""
        item = {
            'name': name,
            'id': uuid.uuid4().hex,
            'complete': False
        }
        self.items.append(item)
        self.hass.async_add_job(self.save)
        return item

    @callback
    def async_update(self, item_id, info):
        """Update a shopping inventory item."""
        item = next((itm for itm in self.items if itm['id'] == item_id), None)

        if item is None:
            raise KeyError

        info = ITEM_UPDATE_SCHEMA(info)
        item.update(info)
        self.hass.async_add_job(self.save)
        return item

    @callback
    def async_clear_completed(self):
        """Clear completed items."""
        self.items = [itm for itm in self.items if not itm['complete']]
        self.hass.async_add_job(self.save)

    @asyncio.coroutine
    def async_load(self):
        """Load items."""
        def load():
            """Load the items synchronously."""
            return load_json(self.hass.config.path(PERSISTENCE), default=[])

        self.items = yield from self.hass.async_add_job(load)

    def save(self):
        """Save the items."""
        save_json(self.hass.config.path(PERSISTENCE), self.items)


class AddInventoryItemIntent(intent.IntentHandler):
    """Handle AddItem intents."""

    intent_type = INTENT_ADD_ITEM
    slot_schema = {
        'item': cv.string
    }

    @asyncio.coroutine
    def async_handle(self, intent_obj):
        """Handle the intent."""
        slots = self.async_validate_slots(intent_obj.slots)
        item = slots['item']['value']
        intent_obj.hass.data[DOMAIN].async_add(item)

        response = intent_obj.create_response()
        response.async_set_speech(
            "I've added {} to your shopping inventory".format(item))
        intent_obj.hass.bus.async_fire(EVENT)
        return response


class InventoryTopItemsIntent(intent.IntentHandler):
    """Handle AddItem intents."""

    intent_type = INTENT_LAST_ITEMS
    slot_schema = {
        'item': cv.string
    }

    @asyncio.coroutine
    def async_handle(self, intent_obj):
        """Handle the intent."""
        items = intent_obj.hass.data[DOMAIN].items[-5:]
        response = intent_obj.create_response()

        if not items:
            response.async_set_speech(
                "There are no items on your shopping inventory")
        else:
            response.async_set_speech(
                "These are the top {} items on your shopping inventory: {}".format(
                    min(len(items), 5),
                    ', '.join(itm['name'] for itm in reversed(items))))
        return response


class ShoppingInventoryView(http.HomeAssistantView):
    """View to retrieve shopping inventory content."""

    url = '/api/shopping_inventory'
    name = "api:shopping_inventory"

    @callback
    def get(self, request):
        """Retrieve shopping inventory items."""
        return self.json(request.app['hass'].data[DOMAIN].items)


class UpdateShoppingInventoryItemView(http.HomeAssistantView):
    """View to retrieve shopping inventory content."""

    url = '/api/shopping_inventory/item/{item_id}'
    name = "api:shopping_inventory:item:id"

    async def post(self, request, item_id):
        """Update a shopping inventory item."""
        data = await request.json()

        try:
            item = request.app['hass'].data[DOMAIN].async_update(item_id, data)
            request.app['hass'].bus.async_fire(EVENT)
            return self.json(item)
        except KeyError:
            return self.json_message('Item not found', HTTP_NOT_FOUND)
        except vol.Invalid:
            return self.json_message('Item not found', HTTP_BAD_REQUEST)


class CreateShoppingInventoryItemView(http.HomeAssistantView):
    """View to retrieve shopping inventory content."""

    url = '/api/shopping_inventory/item'
    name = "api:shopping_inventory:item"

    @RequestDataValidator(vol.Schema({
        vol.Required('name'): str,
    }))
    @asyncio.coroutine
    def post(self, request, data):
        """Create a new shopping inventory item."""
        item = request.app['hass'].data[DOMAIN].async_add(data['name'])
        request.app['hass'].bus.async_fire(EVENT)
        return self.json(item)


class ClearCompletedInventoryItemsView(http.HomeAssistantView):
    """View to retrieve shopping inventory content."""

    url = '/api/shopping_inventory/clear_completed'
    name = "api:shopping_inventory:clear_completed"

    @callback
    def post(self, request):
        """Retrieve if API is running."""
        hass = request.app['hass']
        hass.data[DOMAIN].async_clear_completed()
        hass.bus.async_fire(EVENT)
        return self.json_message('Cleared completed items.')


@callback
def websocket_handle_items(hass, connection, msg):
    """Handle get shopping_inventory items."""
    connection.send_message(websocket_api.result_message(
        msg['id'], hass.data[DOMAIN].items))


@callback
def websocket_handle_add(hass, connection, msg):
    """Handle add item to shopping_inventory."""
    item = hass.data[DOMAIN].async_add(msg['name'])
    hass.bus.async_fire(EVENT)
    connection.send_message(websocket_api.result_message(
        msg['id'], item))


@websocket_api.async_response
async def websocket_handle_update(hass, connection, msg):
    """Handle update shopping_inventory item."""
    msg_id = msg.pop('id')
    item_id = msg.pop('item_id')
    msg.pop('type')
    data = msg

    try:
        item = hass.data[DOMAIN].async_update(item_id, data)
        hass.bus.async_fire(EVENT)
        connection.send_message(websocket_api.result_message(
            msg_id, item))
    except KeyError:
        connection.send_message(websocket_api.error_message(
            msg_id, 'item_not_found', 'Item not found'))


@callback
def websocket_handle_clear(hass, connection, msg):
    """Handle clearing shopping_inventory items."""
    hass.data[DOMAIN].async_clear_completed()
    hass.bus.async_fire(EVENT)
    connection.send_message(websocket_api.result_message(msg['id']))
