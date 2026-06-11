# OpenHydra

[![Build Status](https://github.com/carloborodulin/OpenHydra/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/carloborodulin/OpenHydra/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)](https://github.com/carloborodulin/OpenHydra)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-20232A?logo=react&logoColor=61DAFB)](https://react.dev/)
[![dbt](https://img.shields.io/badge/dbt-FF694B?logo=dbt&logoColor=white)](https://www.getdbt.com/)
[![DuckDB](https://img.shields.io/badge/DuckDB-FFF000?logo=duckdb&logoColor=black)](https://duckdb.org/)
[![Deployed on Railway](https://img.shields.io/badge/Railway-000000?logo=railway&logoColor=white)](https://openhydra-production.up.railway.app)

OpenHydra is an end-to-end analytical data platform designed to process, analyze, and visualize crime statistics in the United States. The system consumes data from the Federal Bureau of Investigation (FBI) Crime Data Explorer (CDE) API, representing Uniform Crime Reporting (UCR) public statistics.

* **Live Platform Demonstration:** https://openhydra-production.up.railway.app
* **Upstream CDE API Documentation:** https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/docApi
* **CDE API Access Registration:** https://api.data.gov/signup/

![OpenHydra Command-Center Dashboard](docs/dashboard.png)

### System Implementation Status

The platform has been fully developed, containerized, and deployed. The system architecture coordinates the following components:
* **Structured API Client ([cdeclient/](file:///Users/carlo/Documents/Development/personal/OpenHydra/cdeclient)):** A robust Python library featuring data validation and automated retry logic.
* **Data Warehousing & Transformation ([warehouse/](file:///Users/carlo/Documents/Development/personal/OpenHydra/warehouse)):** An analytics database powered by DuckDB, with schema models transformed via dbt.
* **Analytical Research ([analysis/](file:///Users/carlo/Documents/Development/personal/OpenHydra/analysis)):** Core notebooks summarizing key trends such as demographics, clearance ratios, and staffing metrics.
* **Backend Services ([api/](file:///Users/carlo/Documents/Development/personal/OpenHydra/api)):** A FastAPI microservice that exposes endpoints for queries and proxies real-time requests.
* **User Dashboard ([web/](file:///Users/carlo/Documents/Development/personal/OpenHydra/web)):** A responsive React web application utilizing MapLibre GL for geographic agency mapping and Recharts for trend analysis.

The UI supports filtering across national, state-level (all 50 states and Washington D.C.), and individual agency granularities. Selected agencies dynamically retrieve cached, real-time data from the upstream CDE API, avoiding the need to pre-materialize information for approximately 19,600 distinct law enforcement agencies.

## System Architecture

```
web/        React + Vite + TS Dashboard (MapLibre GL Map, Recharts)     (Frontend/Visualization)
   │ REST/JSON Requests
api/        FastAPI Backend Service over the Warehouse                   (Application Server)
   │ Analytical Queries
warehouse/  DuckDB Database with dbt Transformations                    (Data Engineering)
analysis/   Jupyter Notebooks (Polars + Plotly)                         (Data Analysis/Research)
   │ Ingestion (ETL) Data Pipelines
cdeclient/  Typed Python Client & Command-Line Tool                     (Client Layer)
   │ HTTP Operations
FBI Crime Data Explorer API
```

## Technology Stack

| Architecture Layer | Core Tools & Frameworks | Description |
| :--- | :--- | :--- |
| **Development Tooling** | `uv`, `ruff`, `mypy`, `pytest` | Python package and environment management, code quality tools, static typing, and test execution. |
| **Client Library (`cdeclient`)** | `httpx`, `pydantic` (v2), `tenacity`, `Typer` | Resilient asynchronous HTTP requests, data validation, execution retry strategy, and CLI functionality. |
| **Data Warehouse** | `DuckDB`, `dbt` (`dbt-duckdb`) | High-performance analytical query processing, source-to-mart transformations, and schema testing. |
| **Data Analysis** | `Jupyter`, `Polars`, `Plotly` | Performant dataframe parsing, narrative notebooks, and data plotting. |
| **Backend API** | `FastAPI`, `Uvicorn` | Asynchronous server gateway serving structured JSON endpoints and auto-generated OpenAPI documentation. |
| **Frontend Web** | `React`, `Vite`, `TypeScript`, `TanStack Query`, `Tailwind CSS`, `Recharts`, `MapLibre GL` | Interactive dashboards, state caching, mapping overlays, and dynamic charting components. |
| **Infrastructure & CI** | `Docker Compose`, `GitHub Actions`, `Railway` | Continuous integration workflows, orchestration configurations, and cloud deployment pipelines. |

The environment leverages Python 3.12 (managed via `uv`) to ensure library compatibility and dependency stability.

## Repository Structure

The code is divided into the following directories and files:

* [cdeclient/](file:///Users/carlo/Documents/Development/personal/OpenHydra/cdeclient) - Contains the typed Python client and command-line application.
* [warehouse/](file:///Users/carlo/Documents/Development/personal/OpenHydra/warehouse) - Implements the ETL pipeline (`oh-etl`) and the dbt transformation configuration.
* [analysis/](file:///Users/carlo/Documents/Development/personal/OpenHydra/analysis) - Stores exploratory Jupyter notebooks, analytics plots, and [FINDINGS.md](file:///Users/carlo/Documents/Development/personal/OpenHydra/analysis/FINDINGS.md).
* [api/](file:///Users/carlo/Documents/Development/personal/OpenHydra/api) - Contains the FastAPI backend application (`oh-api`).
* [web/](file:///Users/carlo/Documents/Development/personal/OpenHydra/web) - Contains the React dashboard build configurations, assets, and source code.
* [docs/](file:///Users/carlo/Documents/Development/personal/OpenHydra/docs) - Contains visual assets and auxiliary document reference materials.
* [data/samples/](file:///Users/carlo/Documents/Development/personal/OpenHydra/data/samples) - Holds cached response payloads for development tests and offline mocks.
* [Dockerfile](file:///Users/carlo/Documents/Development/personal/OpenHydra/Dockerfile) - Standard multi-stage container build specification.
* [.env.example](file:///Users/carlo/Documents/Development/personal/OpenHydra/.env.example) - Template for configuring environment variables.

## Roadmap & Implementation Milestones

The following development milestones have been successfully met:

* **Phase 0: Groundwork and Exploration**
  * Configured access keys, repository standards, and environment templates.
  * Authored helper scripts for initial API verification and cache generation.
* **Phase 1: Client and SDK Package (`cdeclient`)**
  * Shipped typed Python SDK covering the required endpoint families.
  * Implemented validation schemas, CLI commands, and test suites with robust linting.
* **Phase 2: Warehousing Pipeline (`warehouse`)**
  * Engineered a long-format Parquet data pipeline.
  * Structured analytical data modeling through staging and production marts using dbt and DuckDB.
* **Phase 3: Exploratory Analytics (`analysis`)**
  * Generated research notebooks analyzing clearance ratios, crime patterns, and staffing dynamics.
* **Phase 4: Backend Microservice (`api`)**
  * Built endpoints exposing structured queries over the DuckDB database.
  * Documented public API schemas using OpenAPI standards.
* **Phase 5: Frontend Dashboard Application (`web`)**
  * Engineered a dark-themed monitoring interface.
  * Integrated interactive mapping, live proxy drill-down queries, and chart visualizations.
* **Phase 6: DevOps, Testing, and Deployment**
  * Deployed a production-ready containerized service on Railway.
  * Implemented testing pipelines via GitHub Actions.

## FBI CDE API Reference & Integration Details

The system integrates directly with the FBI's Crime Data Explorer (CDE) API.

* **Base URL:** `https://api.usa.gov/crime/fbi/cde`
* **Authentication:** Requires appending the API key as a query parameter: `?API_KEY=<key>`.
* **Output Format:** JSON.
* **Date Parameters:** Most endpoints accept dates in `MM-YYYY` query formats (e.g., `from=01-2020&to=12-2022`). Police Employment (`/pe`) queries require four-digit years (e.g., `from=2018&to=2022`).

### Supported Endpoint Families

| Endpoint Family | Path Pattern | Data Characteristics & Integration Notes |
| :--- | :--- | :--- |
| **Agencies** | `/agency/byStateAbbr/{ST}` | Retrieves localized metadata for reporting agencies. Used to geolocate and render reporting agency pins on the map panel. |
| **Summarized** | `/summarized/{Scope}/{Offense}` | Retrieves monthly actual crime volumes and clearance counts. Scope can be set to `national`, `state/{ST}`, or `agency/{ori}`. Note: For state-level queries, the API returns a duplicate national comparison series that OpenHydra filters out to avoid collisions. |
| **Arrests** | `/arrest/{Scope}/{Offense}?type={totals\|counts}` | Resolves arrest statistics. Selecting `totals` yields breakdowns across demographic categories (race, sex, age groups). Note: Requires numeric offense identifier mappings. |
| **Police Employment** | `/pe?from=YYYY&to=YYYY` | Resolves officer and civilian staffing counts. Note: Standard variants such as `/pe/national` return null payloads. OpenHydra utilizes path-based lookups (`/pe/{ST}/{ori}`) to resolve actual data. |

### Real-Time Proxy Requests

While static aggregated data sets reside directly within the warehouse, per-agency detail queries are executed dynamically at request time by the backend proxy routes. These live requests are optimized using an in-memory TTL caching mechanism:

| Application Backend Route | Downstream Target FBI CDE Path |
| :--- | :--- |
| `/api/agency/{ori}/offenses` | `/summarized/agency/{ori}/{offense}` |
| `/api/agency/{ori}/arrests` | `/arrest/agency/{ori}/{code}?type=totals` |
| `/api/agency/{ori}/police-employment` | `/pe/{ST}/{ori}` |

In situations where upstream data records are missing or incomplete, endpoints handle empty payloads gracefully by returning standardized null structures to prevent client-side formatting errors.

### Validated Offense Slug Mappings

The following hyphenated offense descriptors are verified as active:
`violent-crime`, `homicide`, `rape`, `robbery`, `aggravated-assault`, `property-crime`, `burglary`, `larceny`, `motor-vehicle-theft`, `arson`.

### Identified API Limitations and Exclusions

* Endpoint routes matching `/estimate/*` and `/nibrs/*` return HTTP 404 responses from the current CDE endpoint. This incident-level data resides on legacy or deprecated servers (such as `sapi`). These are not currently supported by this project.

## Installation, Configuration, and Setup

This section outlines how to set up the OpenHydra platform, extract source data, compile the analytics database, and execute the backend and frontend components locally or in containerized environments.

### 1. Environment Configuration

Register for an API key at [api.data.gov](https://api.data.gov/signup/).

Configure your local environment by duplicating the template configuration:
```bash
cp .env.example .env
```
Open the newly created [.env](file:///Users/carlo/Documents/Development/personal/OpenHydra/.env) file and add your key:
```env
FBI_CDE_API_KEY=your_api_key_here
```

### 2. Verify Client Connectivity

You can query sample endpoints to confirm API key authorization and examine raw JSON structures:
```bash
./explore.sh
```
This utility script stores responses in [data/samples/](file:///Users/carlo/Documents/Development/personal/OpenHydra/data/samples) alongside a manifest index.

### 3. Build the Data Warehouse

The database relies on local Parquet files extracted from the FBI API, which are then compiled into analytical tables using dbt and DuckDB.

First, navigate to the warehouse directory and install dependencies:
```bash
cd warehouse
uv sync --group dbt
```

Execute the extraction command to pull target state data. You can run a selective pull for testing:
```bash
# Pulls data for New York state across selected crime categories
uv run oh-etl pull --states NY --offenses homicide,violent-crime --from 01-2020 --to 12-2022
```
Or initiate a full national dataset ingestion:
```bash
# Ingests datasets for all states and crime categories
uv run oh-etl pull --states all
```

Once raw Parquet data is populated, run dbt migrations to build the DuckDB marts:
```bash
cd dbt
uv run --group dbt dbt build --profiles-dir .
```
This command processes raw sources, runs integrity checks, and writes the compiled database file to [warehouse/openhydra.duckdb](file:///Users/carlo/Documents/Development/personal/OpenHydra/warehouse/openhydra.duckdb).

### 4. Running the Application Locally

To test the complete stack locally, start both the FastAPI backend server and the React frontend server.

#### Start the FastAPI Backend:
From the repository root directory, navigate to the API layer and start the server:
```bash
cd api
uv sync
uv run oh-api
```
The API documentation is accessible at `http://127.0.0.1:8000/docs`.

#### Start the React Frontend:
In a separate terminal session, navigate to the web directory and start the Vite development server:
```bash
cd web
npm install
npm run dev
```
The user dashboard will run at `http://localhost:5173`. The development server is pre-configured to proxy `/api` requests to the local backend port to prevent CORS issues.

### 5. Production Container Deployment

You can package and execute the entire project inside a single multi-stage Docker container. The image compiles frontend assets, populates the DuckDB warehouse, and runs the FastAPI backend.

To build and run the container locally:
```bash
docker compose up --build
```

#### Deploying to Railway:
The repository is pre-configured for automated deployment on Railway using [railway.json](file:///Users/carlo/Documents/Development/personal/OpenHydra/railway.json):
```bash
railway up
```
Ensure that the `FBI_CDE_API_KEY` environment variable is defined within the Railway dashboard settings.
