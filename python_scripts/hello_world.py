name = data.get('name', 'world')
logger.info("Hello {}".format(name))
hass.bus.fire("test_working", { "wow": "from a Python script!" })