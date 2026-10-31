# Running ChrystalClear on $0 (and how to raise money later)

Current budget: **$0**. Everything below works without spending anything.

## You don't need a domain yet
Free hosts give you a working web address:
- **Render** (free web service): `chrystalclear.onrender.com`. Our production `Dockerfile` runs
  there as-is. Free services sleep when idle (~1 minute to wake up).
- **Neon** or **Supabase** free Postgres for the database.
- **Cloudflare Pages** / **GitHub Pages** are free too, if we later split the frontend out.

Buy a domain (~$12–15/year for `.app`) once donations cover it. Moving to a domain later is
easy — nothing in the app depends on the address.

## Ways to bring in money (all compatible with "repair info free forever")
1. **GitHub Sponsors** — free to set up, GitHub takes no fee on personal sponsorships.
   Owner: github.com/sponsors → join, connect a bank account. A "Sponsor" button then
   appears on the repo.
2. **Open Collective** (via the Open Source Collective fiscal host) — transparent public
   budget; donors see where money goes. The host takes a percentage (check current rate).
3. **Ko-fi / Buy Me a Coffee** — simplest "tip jar" link for the About page.
4. **Shop sponsorships** — local parts stores or shops sponsor a "Supported by" line.
5. **Parts affiliate links** (later, with the parts-lookup module) — small commission, free to users.
6. **Grants** — right-to-repair, open-data, and digital-public-goods grant programs open up
   periodically. Worth checking once there's a public demo to point to.
7. **Later (Option B):** optional paid business tools (shop management, team accounts,
   bulk API) — never paywalling repair information.

## Free legal help (instead of hiring a lawyer)
- **USPTO Law School Clinic Certification Program** — supervised law students give free
  trademark help (search + filing advice). Search "USPTO law school clinic" and pick a
  participating school's trademark clinic.
- **Software Freedom Law Center** — free legal help for free/open-source software projects.
- **Fiscal sponsors** (e.g. Software Freedom Conservancy, Open Source Collective) can hold
  funds and sometimes provide legal/trademark support for member projects.
- **Contributor agreement:** our `CLA.md` is a draft. A zero-cost alternative to legal
  review is to adopt a widely used, lawyer-written template (e.g. the Apache Individual
  CLA or a Project Harmony agreement) with our name filled in. Ask before outside
  contributors join.

## What the owner can do now (all free)
- [ ] Turn on GitHub Sponsors for your account (takes ~15 minutes; needs bank + tax info).
- [ ] When ready to launch publicly: create free Render + Neon accounts (I'll walk you through it).
