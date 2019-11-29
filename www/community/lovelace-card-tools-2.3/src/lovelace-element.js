import { fireEvent } from "./event.js";

export const CUSTOM_TYPE_PREFIX = "custom:";

export const DOMAINS_HIDE_MORE_INFO = [
  "input_number",
  "input_select",
  "input_text",
  "scene",
  "weblink",
];

function errorElement(error, origConfig) {
  const el = document.createElement("hui-error-card");
  el.setConfig({
    type: "error",
    error,
    origConfig,
  });
  return el;
}

function _createElement(tag, config) {
  const el = document.createElement(tag);
  try {
    el.setConfig(config);
  } catch (err) {
    return errorElement(err, config);
  }
  return el;
}

function createLovelaceElement(thing, config) {
  if(!config || typeof config !== "object" || !config.type)
    return errorElement(`No ${thing} type configured`, config);

  let tag = config.type;
  if(tag.startsWith(CUSTOM_TYPE_PREFIX))
    tag = tag.substr(CUSTOM_TYPE_PREFIX.length);
  else
    tag = `hui-${tag}-${thing}`;

  if(customElements.get(tag))
    return _createElement(tag, config);

  const el = errorElement(`Custom element doesn't exist: ${tag}.`, config);
  el.style.display = "None";

  const timer = setTimeout(() => {
    el.style.display = "";
  }, 2000);

  customElements.whenDefined(tag).then(() => {
    clearTimeout(timer);
    fireEvent("ll-rebuild", {}, el);
  });

  return el;
}

export function createCard(config) {
  return createLovelaceElement('card', config);
}
export function createElement(config) {
  return createLovelaceElement('element', config);
}
export function createEntityRow(config) {
  const SPECIAL_TYPES = new Set([
    "call-service",
    "divider",
    "section",
    "weblink",
  ]);
  const DEFAULT_ROWS = {
    alert: "toggle",
    automation: "toggle",
    climate: "climate",
    cover: "cover",
    fan: "toggle",
    group: "group",
    input_boolean: "toggle",
    input_number: "input-number",
    input_select: "input-select",
    input_text: "input-text",
    light: "toggle",
    lock: "lock",
    media_player: "media-player",
    remote: "toggle",
    scene: "scene",
    script: "script",
    sensor: "sensor",
    timer: "timer",
    switch: "toggle",
    vacuum: "toggle",
    water_heater: "climate",
    input_datetime: "input-datetime",
  };

  if(!config)
    return errorElement("Invalid configuration given.", config);
  if(typeof config === "string")
    config = {entity: config};
  if(typeof config !== "object" || (!config.entity && !config.type))
    return errorElement("Invalid configuration given.", config);

  const type = config.type || "default";
  if(SPECIAL_TYPES.has(type) || type.startsWith(CUSTOM_TYPE_PREFIX))
    return createLovelaceElement('row', config);

  const domain = config.entity.split(".", 1)[0];
  Object.assign(config, {type: DEFAULT_ROWS[domain] || "text"});

  return createLovelaceElement('entity-row', config);
}
