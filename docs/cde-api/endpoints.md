# FBI CDE API — endpoint reference

> Generated from `openapi.json` by `_tooling/gen_endpoints.mjs`. Do not edit by hand.

- **Spec:** OpenAPI 3.0.1 — CDE-PRD-API-Gateway (2022-10-13T17:58:35Z)
- **Server:** `https://api.usa.gov/crime/fbi/cde/{basePath}`
- **Auth:** append `?API_KEY=<key>` to every request
- **Totals:** 32 paths across 11 groups

## Use Of Force

### `GET /uof`

| param | in | required | type | values |
|---|---|---|---|---|
| `year` | query | yes | string |  |
| `location` | query | yes | string |  |

Responses: `200`


## LESDC

### `GET /lesdc`

| param | in | required | type | values |
|---|---|---|---|---|
| `chartType` | query | yes | lesdc_charts |  |
| `year` | query | yes | string |  |

Responses: `200`, `400`, `500`


## Arrest

### `GET /arrest/agency/{ori}/{offense}`

| param | in | required | type | values |
|---|---|---|---|---|
| `type` | query | yes | type |  |
| `ori` | path | yes | string |  |
| `from` | query | yes | string |  |
| `offense` | path | yes | arrest_offense |  |
| `to` | query | yes | string |  |

Responses: `200`

### `GET /arrest/national/{offense}`

| param | in | required | type | values |
|---|---|---|---|---|
| `type` | query | yes | type |  |
| `from` | query | yes | string |  |
| `to` | query | yes | string |  |
| `offense` | path | yes | arrest_offense |  |

Responses: `200`

### `GET /arrest/state/{state}/{offense}`

| param | in | required | type | values |
|---|---|---|---|---|
| `type` | query | yes | type |  |
| `state` | path | yes | states |  |
| `from` | query | yes | string |  |
| `to` | query | yes | string |  |
| `offense` | path | yes | arrest_offense |  |

Responses: `200`


## Agency

### `GET /agency/{query}/{value}`

| param | in | required | type | values |
|---|---|---|---|---|
| `query` | path | yes | agency_query_types |  |
| `value` | path | yes |  |  |

Responses: `200`


## NIBRS

### `GET /nibrs/agency/{ori}/{offense}`

| param | in | required | type | values |
|---|---|---|---|---|
| `type` | query | yes | type |  |
| `from` | query | yes | string |  |
| `to` | query | yes | string |  |
| `offense` | path | yes | nibrs_offenses |  |
| `ori` | path | yes | string |  |

Responses: `200`, `400`, `500`

### `GET /nibrs/national/{offense}`

| param | in | required | type | values |
|---|---|---|---|---|
| `type` | query | yes | type |  |
| `from` | query | yes | string |  |
| `to` | query | yes | string |  |
| `offense` | path | yes | nibrs_offenses |  |

Responses: `200`, `400`, `500`

### `GET /nibrs/state/{state}/{offense}`

| param | in | required | type | values |
|---|---|---|---|---|
| `type` | query | yes | type |  |
| `state` | path | yes | states |  |
| `from` | query | yes | string |  |
| `to` | query | yes | string |  |
| `offense` | path | yes | nibrs_offenses |  |

Responses: `200`, `400`, `500`


## NIBRS Estimations

### `GET /nibrs-estimation/lookup/{lookup}`

| param | in | required | type | values |
|---|---|---|---|---|
| `lookup` | path | yes | lookup |  |

Responses: `200`

### `GET /nibrs-estimation/national/agency-type/{type}/{location}/{offense}`

| param | in | required | type | values |
|---|---|---|---|---|
| `type` | path | yes | nibrs_estimations_types |  |
| `year` | query | yes | string |  |
| `location` | path | yes | nibrs_estimations_locations |  |
| `offense` | path | yes | nibrs_estimations_offenses |  |

Responses: `200`

### `GET /nibrs-estimation/national/size/{type}/{desc}/{offense}`

| param | in | required | type | values |
|---|---|---|---|---|
| `type` | path | yes | nibrs_estimations_types |  |
| `year` | query | yes | string |  |
| `desc` | path | yes | nibrs_estimations_descriptions |  |
| `offense` | path | yes | nibrs_estimations_offenses |  |

Responses: `200`

### `GET /nibrs-estimation/national/{offense}`

| param | in | required | type | values |
|---|---|---|---|---|
| `year` | query | yes | string |  |
| `offense` | path | yes | nibrs_estimations_offenses |  |

Responses: `200`

### `GET /nibrs-estimation/region/agency-type/{region}/{type}/{location}/{offense}`

| param | in | required | type | values |
|---|---|---|---|---|
| `type` | path | yes | nibrs_estimations_types |  |
| `year` | query | yes | string |  |
| `location` | path | yes | nibrs_estimations_locations |  |
| `region` | path | yes | regions |  |
| `offense` | path | yes | nibrs_estimations_offenses |  |

Responses: `200`

### `GET /nibrs-estimation/region/size/{region}/{type}/{desc}/{offense}`

| param | in | required | type | values |
|---|---|---|---|---|
| `type` | path | yes | nibrs_estimations_types |  |
| `year` | query | yes | string |  |
| `desc` | path | yes | nibrs_estimations_descriptions |  |
| `region` | path | yes | regions |  |
| `offense` | path | yes | nibrs_estimations_offenses |  |

Responses: `200`

### `GET /nibrs-estimation/region/{region}/{offense}`

| param | in | required | type | values |
|---|---|---|---|---|
| `year` | query | yes | string |  |
| `region` | path | yes | regions |  |
| `offense` | path | yes | nibrs_estimations_offenses |  |

Responses: `200`

### `GET /nibrs-estimation/state/{state}/{offense}`

| param | in | required | type | values |
|---|---|---|---|---|
| `year` | query | yes | string |  |
| `state` | path | yes | state_id |  |
| `offense` | path | yes | nibrs_estimations_offenses |  |

Responses: `200`


## Hate Crime

### `GET /hate-crime/agency/{ori}/{bias}`

| param | in | required | type | values |
|---|---|---|---|---|
| `ori` | path | yes | string |  |
| `bias` | path | yes | hate_crime_query_options |  |
| `type` | query | yes | type |  |
| `from` | query | yes | string |  |
| `to` | query | yes | string |  |

Responses: `200`, `400`, `500`

### `GET /hate-crime/national/{bias}`

| param | in | required | type | values |
|---|---|---|---|---|
| `bias` | path | yes | hate_crime_query_options |  |
| `type` | query | yes | type |  |
| `from` | query | yes | string |  |
| `to` | query | yes | string |  |

Responses: `200`, `400`, `500`

### `GET /hate-crime/state/{state}/{bias}`

| param | in | required | type | values |
|---|---|---|---|---|
| `state` | path | yes | states |  |
| `bias` | path | yes | hate_crime_query_options |  |
| `type` | query | yes | type |  |
| `from` | query | yes | string |  |
| `to` | query | yes | string |  |

Responses: `200`, `400`, `500`


## Expanded Property

### `GET /supplemental/agency/{ori}/{offense}`

| param | in | required | type | values |
|---|---|---|---|---|
| `type` | query | yes | type |  |
| `from` | query | yes | string |  |
| `to` | query | yes | string |  |
| `offense` | path | yes | expanded_property_offenses |  |
| `ori` | path | yes | string |  |

Responses: `200`, `400`, `500`

### `GET /supplemental/national/{offense}`

| param | in | required | type | values |
|---|---|---|---|---|
| `type` | query | yes | type |  |
| `from` | query | yes | string |  |
| `to` | query | yes | string |  |
| `offense` | path | yes | expanded_property_offenses |  |

Responses: `200`, `400`, `500`

### `GET /supplemental/state/{state}/{offense}`

| param | in | required | type | values |
|---|---|---|---|---|
| `type` | query | yes | type |  |
| `state` | path | yes | states |  |
| `from` | query | yes | string |  |
| `to` | query | yes | string |  |
| `offense` | path | yes | expanded_property_offenses |  |

Responses: `200`, `400`, `500`


## Summarized

### `GET /summarized/agency/{ori}/{offense}`

| param | in | required | type | values |
|---|---|---|---|---|
| `from` | query | yes | string |  |
| `offense` | path | yes | summarized_offenses |  |
| `ori` | path | yes |  |  |
| `to` | query | yes | string |  |

Responses: `200`, `400`, `500`

### `GET /summarized/national/{offense}`

| param | in | required | type | values |
|---|---|---|---|---|
| `from` | query | yes | string |  |
| `offense` | path | yes | summarized_offenses |  |
| `to` | query | yes | string |  |

Responses: `200`, `400`, `500`

### `GET /summarized/state/{state}/{offense}`

| param | in | required | type | values |
|---|---|---|---|---|
| `state` | path | yes | states |  |
| `from` | query | yes | string |  |
| `offense` | path | yes | summarized_offenses |  |
| `to` | query | yes | string |  |

Responses: `200`


## Expanded Homicide

### `GET /shr/agency/{ori}`

| param | in | required | type | values |
|---|---|---|---|---|
| `type` | query | yes | type |  |
| `from` | query | yes | string |  |
| `to` | query | yes | string |  |
| `ori` | path | yes | string |  |

Responses: `200`, `400`, `500`

### `GET /shr/national`

| param | in | required | type | values |
|---|---|---|---|---|
| `type` | query | yes | type |  |
| `from` | query | yes | string |  |
| `to` | query | yes | string |  |

Responses: `200`, `400`, `500`

### `GET /shr/state/{state}`

| param | in | required | type | values |
|---|---|---|---|---|
| `type` | query | yes | type |  |
| `state` | path | yes | states |  |
| `from` | query | yes | string |  |
| `to` | query | yes | string |  |

Responses: `200`, `400`, `500`


## Law Enforcement Employees

### `GET /pe`

| param | in | required | type | values |
|---|---|---|---|---|
| `from` | query | yes | string |  |
| `to` | query | yes | string |  |

Responses: `200`

### `GET /pe/{state}`

| param | in | required | type | values |
|---|---|---|---|---|
| `from` | query | yes | string |  |
| `to` | query | yes | string |  |
| `state` | path | yes | states |  |

Responses: `200`

### `GET /pe/{state}/{ori}`

| param | in | required | type | values |
|---|---|---|---|---|
| `from` | query | yes | string |  |
| `to` | query | yes | string |  |
| `state` | path | yes | states |  |
| `ori` | path | yes | string |  |

Responses: `200`

