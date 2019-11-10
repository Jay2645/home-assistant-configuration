#
#  Copyright (c) 2019, Andrey "Limych" Khrolenok <andrey@khrolenok.ru>
#  Creative Commons BY-NC-SA 4.0 International Public License
#  (see LICENSE.md or https://creativecommons.org/licenses/by-nc-sa/4.0/)
#
"""
The Car Wash binary sensor.

For more details about this platform, please refer to the documentation at
https://github.com/Limych/HomeAssistantComponents/
"""
import logging
from datetime import datetime

import voluptuous as vol
from homeassistant.components.binary_sensor import BinarySensorDevice
from homeassistant.components.weather import (
    ATTR_FORECAST_PRECIPITATION, ATTR_FORECAST_TIME, ATTR_FORECAST_TEMP,
    ATTR_FORECAST_TEMP_LOW, ATTR_FORECAST_CONDITION, ATTR_WEATHER_TEMPERATURE,
    ATTR_FORECAST)
from homeassistant.const import (
    CONF_NAME, EVENT_HOMEASSISTANT_START, TEMP_CELSIUS)
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_state_change
from homeassistant.util import dt as dt_util
from homeassistant.util.temperature import convert as convert_temperature

VERSION = '1.2.6'

_LOGGER = logging.getLogger(__name__)

CONF_WEATHER = 'weather'
CONF_DAYS = 'days'

DEFAULT_NAME = 'Car Wash'
DEFAULT_DAYS = 2

BAD_CONDITIONS = ["lightning-rainy", "rainy", "pouring", "snowy",
                  "snowy-rainy"]

PLATFORM_SCHEMA = cv.PLATFORM_SCHEMA.extend({
    vol.Required(CONF_WEATHER): cv.entity_id,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_DAYS, default=DEFAULT_DAYS): vol.Coerce(int),
})


async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    """Set up the Car Wash sensor."""
    _LOGGER.debug('Version %s', VERSION)
    _LOGGER.info('if you have ANY issues with this, please report them here:'
                 ' https://github.com/Limych/ha-car_wash')

    name = config.get(CONF_NAME)
    weather = config.get(CONF_WEATHER)
    days = config.get(CONF_DAYS)

    async_add_entities([CarWashBinarySensor(hass, name, weather, days)])


class CarWashBinarySensor(BinarySensorDevice):
    """Implementation of an Car Wash binary sensor."""

    def __init__(self, hass, friendly_name, weather_entity, days):
        """Initialize the sensor."""
        self._hass = hass
        self._name = friendly_name
        self._weather_entity = weather_entity
        self._days = days
        self._state = None

    async def async_added_to_hass(self):
        """Register callbacks."""

        @callback
        def sensor_state_listener(entity, old_state, new_state):
            """Handle device state changes."""
            self.async_schedule_update_ha_state(True)

        @callback
        def sensor_startup(event):
            """Update template on startup."""
            async_track_state_change(
                self._hass, [self._weather_entity], sensor_state_listener)

            self.async_schedule_update_ha_state(True)

        self._hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_START, sensor_startup)

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def is_on(self):
        """Return True if sensor is on."""
        return self._state

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return 'mdi:car-wash'

    @staticmethod
    def _temp2c(temperature: float, temperature_unit: str) -> float:
        """Convert weather temperature to Celsius degree."""
        if temperature is not None and temperature_unit != TEMP_CELSIUS:
            temperature = convert_temperature(
                temperature, temperature_unit, TEMP_CELSIUS)

        return temperature

    async def async_update(self):
        """Update the sensor state."""
        wd = self._hass.states.get(self._weather_entity)

        if wd is None:
            raise HomeAssistantError(
                'Unable to find an entity called {}'.format(
                    self._weather_entity))

        tu = self._hass.config.units.temperature_unit
        t = wd.attributes.get(ATTR_WEATHER_TEMPERATURE)
        cond = wd.state
        forecast = wd.attributes.get(ATTR_FORECAST)

        _LOGGER.debug('Current temperature %s, condition \'%s\'', t, cond)

        t = self._temp2c(t, tu)

        if forecast is None:
            raise HomeAssistantError(
                'Can\'t get forecast data!'
                ' Are you sure it\'s the weather provider?')

        cur_date = datetime.now().strftime('%F')
        stop_date = datetime.fromtimestamp(
            datetime.now().timestamp() + 86400 * (self._days + 1)
        ).strftime('%F')
        _LOGGER.debug('Inspect weather forecast from now till %s', stop_date)

        if cond in BAD_CONDITIONS:
            _LOGGER.debug('Detected bad weather condition')
            self._state = False
            return

        for fc in forecast:
            fc_date = fc.get(ATTR_FORECAST_TIME)
            if type(fc_date) == int:
                fc_date = dt_util.as_local(datetime.utcfromtimestamp(
                    fc_date / 1000)).isoformat()
            fc_date = fc_date[:10]
            if fc_date < cur_date:
                continue
            if fc_date == stop_date:
                break
            _LOGGER.debug('Inspect weather forecast for %s', fc_date)

            prec = fc.get(ATTR_FORECAST_PRECIPITATION)
            cond = fc.get(ATTR_FORECAST_CONDITION)
            tmin = fc.get(ATTR_FORECAST_TEMP_LOW)
            tmax = fc.get(ATTR_FORECAST_TEMP)
            _LOGGER.debug(
                'Precipitation %s, Condition \'%s\','
                ' Min temperature: %s, Max temperature %s',
                prec, cond, tmin, tmax)

            if prec:
                _LOGGER.debug('Precipitation detected')
                self._state = False
                return
            if cond in BAD_CONDITIONS:
                _LOGGER.debug('Detected bad weather condition')
                self._state = False
                return
            if tmin is not None and fc_date != cur_date:
                tmin = self._temp2c(tmin, tu)
                if t < 0 <= tmin:
                    _LOGGER.debug(
                        'Detected passage of temperature through melting'
                        ' point')
                    self._state = False
                    return
                t = tmin
            if tmax is not None:
                tmax = self._temp2c(tmax, tu)
                if t < 0 <= tmax:
                    _LOGGER.debug(
                        'Detected passage of temperature through melting'
                        ' point')
                    self._state = False
                    return
                t = tmax

        _LOGGER.debug('Inspection done. No bad forecast detected')
        self._state = True
