# ChrystalClear

**Free, open-source auto repair information — for shops, techs, and DIYers.**

ChrystalClear is a community-built alternative to paid repair databases. Decode a VIN,
see recalls, TSBs and complaints, look up trouble codes, and follow repair guides and
specs written and checked by real technicians. It runs in any browser and installs on
your phone like an app, with offline access to what you've recently viewed.

> **Repair information is free forever.** Vehicle lookups, recalls, TSBs, trouble codes, and
> every community-written guide and spec will always be free — never paywalled.

> **Status:** v0.1 in progress — VIN decoder, vehicle picker and My Garage work today. See [docs/PLAN.md](docs/PLAN.md),
> [TODO.md](TODO.md), and [CHANGELOG.md](CHANGELOG.md).

## Planned v0.1 features
- **VIN decoder** (NHTSA vPIC) and year/make/model/engine picker; vehicle profiles; **My Garage**
- **Recalls, TSB index, and complaints** from public NHTSA data
- **Trouble code (DTC) lookup** with plain-English meaning, symptoms, causes, and diagnostic steps
- **Community repair guides & specs** — procedures, torque specs, fluid capacities, part
  notes, labor estimates, photos — with revision history, pro verification, voting, and
  "report wrong info"
- **Fast search** across vehicles, codes, recalls, and guides
- **Shop-friendly design:** big buttons, high contrast, dark mode, metric/imperial toggle, works offline

## Quick start (developers)
With [Docker](https://docs.docker.com/get-docker/) installed, one command:

```bash
docker compose up
```

Then open **http://localhost:5173** (API docs at http://localhost:8000/api/v1/docs).
Sample vehicles are loaded automatically — try the year/make/model picker with
*2015 Ford F-150*, or decode any real VIN.

Without Docker (Python 3.12+ and Node 22+): `./scripts/dev.sh`

Run tests: `cd backend && pytest` and `cd frontend && npm test`.

## Safety disclaimer
Repair information here is provided by the community and public sources **as-is, without
warranty**. Always confirm torque values and safety-critical specs against the
manufacturer's service information before working on brakes, steering, suspension,
airbags, fuel, or high-voltage systems. You are responsible for your own work.

## Contributing
Contributions of code, guides, specs, and photos are welcome. Please read
[CONTRIBUTING.md](CONTRIBUTING.md) — especially the content rules — and our
[Code of Conduct](CODE_OF_CONDUCT.md).

## Data sources
- [NHTSA vPIC](https://vpic.nhtsa.dot.gov/api/) — VIN decoding and vehicle makes/models
- [NHTSA recalls, complaints and manufacturer communications (TSBs)](https://www.nhtsa.gov/nhtsa-datasets-and-apis)
- Community contributions written in contributors' own words

ChrystalClear is not affiliated with NHTSA, ALLDATA, Mitchell 1, Identifix, or any vehicle manufacturer.

## Contact
Project contact email: _to be set by the project owner._

## License
- **Code:** [GNU AGPL-3.0](LICENSE). If you run a modified version as a public service,
  you must share your source code with its users.
- **Community content** (guides, specs, notes, photos): [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
  Anyone may reuse it with credit, as long as they share it under the same license.
- Contributors sign our [Contributor License Agreement](CLA.md) — see CONTRIBUTING.md.
