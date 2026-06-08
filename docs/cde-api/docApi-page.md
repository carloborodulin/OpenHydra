# FBI Crime Data API — docApi page (verbatim content)

> Faithful copy of the narrative and endpoint catalog shown at
> <https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/docApi>, captured 2026-06-08.
> The exact parameters/responses for each endpoint are in [`openapi.json`](./openapi.json)
> and summarized in [`endpoints.md`](./endpoints.md); a screenshot is in
> [`docApi.png`](./docApi.png).

**Base URL:** `api.usa.gov/crime/fbi/cde/`

The FBI Crime Data API is a read-only web service that returns JSON or CSV data.
It is broadly organized around the data reporting systems the FBI UCR program
uses and their related entities. Agencies submit data using one of two reporting
formats — the **Summary Reporting System (SRS)** or the **National Incident
Based Reporting System (NIBRS)**. SRS data is the legacy format that provides
aggregated counts of the reported crime offenses known to law enforcement by
location.

NIBRS is a newer format that provides an incident-based view of crime. It
includes information about each offense, such as the time of day an incident
occurred, the demographics of the offenders/victims, the known relationships
between the offenders and victims, and many other details around how and where
crime occurs. Neither format includes personally identifiable information (PII)
about the offenders or victims. While many agencies submit SRS data, the FBI
plans to transition all crime reporting to the NIBRS format by 2021.

Other UCR data collection systems made available by this API include:

- Summarized Agency Data
- NIBRS Counts
- Law Enforcement Employees Data
- State and Agency Participation Data

> **FBI guidance on interpretation:** The API was designed to provide as much
> information as possible in a usable format. However, the FBI still has some
> recommendations about how to interpret and display the data provided. The FBI
> strongly advises against using this data to do any sort of ranking or
> comparison among states or other entities. The exception being that it is
> appropriate to compare a city to its respective state, and that state to a
> national perspective.

**Servers:** `https://api.usa.gov/crime/fbi/cde` (server variable `basePath`,
default `/LATEST`).

---

## Endpoint catalog

Grouped exactly as the docApi page presents them. Path/method only here; see
`endpoints.md` for parameters and responses.

### Agency
Provides agencies that have provided data to the UCR Program and are displayed on the CDE.
- `GET /agency/{query}/{value}`

### Arrest
Provides details of the number of arrests, citations, or summons for an offense. View arrest information on the national and regional level along with federal, state, and local agencies.
- `GET /arrest/agency/{ori}/{offense}`
- `GET /arrest/national/{offense}`
- `GET /arrest/state/{state}/{offense}`

### Expanded Homicide
Expanded Homicide Data for the nation are derived from SRS and NIBRS reports voluntarily submitted to the FBI.
- `GET /shr/agency/{ori}`
- `GET /shr/national`
- `GET /shr/state/{state}`

### Expanded Property
Provides additional details for summarized UCR data beyond the count of reported crimes. Details include type of weapon used, value of items, etc.
- `GET /supplemental/agency/{ori}/{offense}`
- `GET /supplemental/national/{offense}`
- `GET /supplemental/state/{state}/{offense}`

### Hate Crime
Hate Crime data for the nation are derived from NIBRS and SRS reports voluntarily submitted to the FBI.
- `GET /hate-crime/agency/{ori}`
- `GET /hate-crime/agency/{ori}/{bias}`
- `GET /hate-crime/national`
- `GET /hate-crime/national/{bias}`
- `GET /hate-crime/state/{state}`
- `GET /hate-crime/state/{state}/{bias}`

### Law Enforcement Employees
Law Enforcement Employees data for the nation are derived from SRS and NIBRS reports voluntarily submitted to the FBI.
- `GET /pe`
- `GET /pe/{state}`
- `GET /pe/{state}/{ori}`

### LESDC
The Law Enforcement Suicide Data Collection's intent and benefit is to better understand the factors related to law enforcement officer suicides and provides information designed to assist in the development of programs, and potential resources, to help prevent suicides.
- `GET /lesdc`

### NIBRS
Provides details regarding the National Incident Based Reporting System. Provides offender data for an offense in instances when some aspect about the offender was known, e.g., age, sex, race, ethnicity. In cases involving multiple-offense incidents, each offender is counted more than once.
- `GET /nibrs/agency/{ori}/{offense}`
- `GET /nibrs/national/{offense}`
- `GET /nibrs/state/{state}/{offense}`

### NIBRS Estimations
Provides details regarding the National Incident Based Reporting System (estimation views).
- `GET /nibrs-estimation/lookup/{lookup}`
- `GET /nibrs-estimation/national/{offense}`
- `GET /nibrs-estimation/national/agency-type/{type}/{location}/{offense}`
- `GET /nibrs-estimation/national/size/{type}/{desc}/{offense}`
- `GET /nibrs-estimation/region/{region}/{offense}`
- `GET /nibrs-estimation/region/agency-type/{region}/{type}/{location}/{offense}`
- `GET /nibrs-estimation/region/size/{region}/{type}/{desc}/{offense}`
- `GET /nibrs-estimation/state/{state}/{offense}`

### Summarized
Provides details regarding reported and converted summary data. Estimated data is available for All Violent Crimes, Homicide, Rape, Robbery, Aggravated Assault, All Property Crimes, Arson, Burglary, Larceny-theft, and Motor Vehicle Theft. Data is available on the national and regional level along with federal, state, and local agencies.
- `GET /summarized/agency/{ori}/{offense}`
- `GET /summarized/national/{offense}`
- `GET /summarized/state/{state}/{offense}`

### Use Of Force
The National Use of Force collection includes any use of force that results in: the death of a person due to law enforcement use of force, the serious bodily injury of a person due to law enforcement use of force, or the discharge of a firearm by law enforcement at or in the direction of a person not otherwise resulting in death or serious bodily injury. Agencies with no qualifying incidents in a month submit a zero report.
- `GET /participation/national/{collection}/{query}`
- `GET /participation/national/uof/{query}`
- `GET /participation/state/{state}/{collection}/{query}`
- `GET /uof/questions/{grp}/{year}/{quarter}`
- `GET /uof/reports/{grp}/{spec}`
