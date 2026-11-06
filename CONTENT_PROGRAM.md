# OpenRepair Content Research Program

## Mission
OpenRepair is a free alternative to ALLDATA and Mitchell, with open-source code.
Its repair content must be accurate enough that a working technician trusts it
over the paid tools. Generic content ("P0300: check plugs, coils, injectors") is a
failure. Become a genuine subject-matter expert in automotive diagnostics and
repair, study the industry-standard tools closely, and write original content
that meets or beats them.

## Research is the job. Go deep.
You are expected to research as widely and deeply as it takes:
- Industry-standard guides: study how ALLDATA, Mitchell1, Identifix, Haynes,
  Chilton and iFixit structure their content, how deep they go, how a tech moves
  through them, and where they fall short. We must understand the product we are
  beating from the customer's seat.
- OEM service information: factory procedures and specs are the gold standard and
  the final authority on numbers.
- Working techs: ScannerDanner, South Main Auto, Pine Hollow Auto Diagnostics and
  similar diagnostic channels and write-ups.
- Model-specific forums and owner communities: pattern failures, real fixes, what
  actually solved the problem.
- Public data: NHTSA vPIC (VIN decoding), NHTSA recalls, complaints and
  manufacturer communications/TSBs, EPA fueleconomy.gov.
Do not hold back on research out of caution. If a source is blocked, log it in
/research/blocked-sources.md and keep going.

## Access to paid and login-only sources
Some of the best sources sit behind subscriptions. The owner holds legitimate
accounts and opens those himself:
- Never ask for, store or type passwords, and never get around a login or paywall.
- When a topic needs a paid or OEM source, add it to /research/owner-lookups.md:
  vehicle, engine, what to look up, and why. The owner looks it up in his own
  account and drops notes or screenshots into /research/owner-notes/.
- Treat owner notes as a primary source and cite them as
  "OEM service info (owner lookup, date)" or "ALLDATA DIY (owner lookup, date)".
- Owner sources to plan around: ALLDATA DIY, Mitchell1 DIY, and OEM service
  sites such as Motorcraft Service (Ford) and ACDelco TDS (GM).

## Learn from everything, copy nothing
- Facts are free to use: specs, torque values, capacities, part numbers, firing
  orders, test values, procedures as sequences of facts, known failure patterns.
- Write every guide in your own words, with your own structure. Never copy text,
  photos or diagrams from any source. Make original SVG diagrams where a visual
  helps.
- Synthesize: the best page combines what 5 to 10 sources know and ends up better
  than any one of them.

## Accuracy is the top priority
A wrong spec or bad procedure can destroy an engine or hurt someone, and it would
end this project's credibility.
- Every numeric spec (torque, voltage, resistance, pressure, capacity, gap,
  clearance) cites its source in the page's source list.
- Cross-check critical specs against at least two independent sources, one of them
  OEM service info wherever possible.
- When sources conflict, note the conflict and treat OEM as the authority.
- If a value can't be confirmed, mark it UNVERIFIED and add it to
  owner-lookups.md. Never invent a plausible-looking number.
- Specs must match the exact application: year range, engine code, transmission.
- Include safety warnings where relevant: airbags/SRS, fuel systems, hybrid/EV
  high voltage, A/C refrigerant, lifting the vehicle, hot coolant.
- No page goes live until a working mechanic has signed off on it.

## Content ownership and license
- The app's code stays open source. The repair guides, research notes and
  diagrams are OpenRepair's own proprietary content: free for users to read in
  the app, but all rights reserved. Not covered by the code's open-source license.
- Keep all guide content under /content/ with its own LICENSE file stating this,
  and update the README so the split between code and content is clear.
- If the code repo is public, flag it so the owner can decide whether to move
  /content/ and /research/ into a private repo.

## Liability and safety on every page
- Every guide shows a clear "work at your own risk" disclaimer and its safety
  warnings at the top, before the first step.
- Draft site-wide Terms of Use and a disclaimer page for the lawyer to review.
  Mark them DRAFT, NOT LEGAL ADVICE until reviewed.

## Expert sign-off
- Each page tracks: written by, verified by (agent), mechanic sign-off (name,
  certification such as ASE, date). A page without mechanic sign-off is not
  published.
- Build a simple reviewer checklist a mechanic can work through quickly per page.

## Error reporting and revisions
- Add a "Report a mistake" button on every guide that records the page, the
  section and the user's note, and alerts the owner.
- Each page shows "last revised" and keeps a change history. A reported spec
  error is marked under review on the page until it is fixed.

## Process
1. Inspect the repo. Learn how content is stored and displayed, and fit new
   content to it (improve the format if it can't hold this depth, and explain why).
2. Research: one notes file per vehicle/engine/topic in /research/, with findings,
   pattern failures, specs and sources. This becomes our knowledge base.
3. Competitor study: write /research/competitor-teardown.md on how the paid tools
   lay out DTC pages and procedures, what techs like, and where we can beat them.
4. Writing: write pages from the research notes.
5. Verification: re-check every spec against its sources before marking a page
   done. Use a separate agent that did not write the page to review it for errors,
   missing steps and unsupported claims.
6. Log every page in /research/review-log.md with status: verified, has
   UNVERIFIED items, waiting on owner lookup, or needs mechanic sign-off.

## Scope and priority
Go deep before wide. Start with the best-selling, most-registered US vehicles of
the last 20 years (research which ones), their most common engines, and their most
common DTCs and repairs.
First milestone: the 20 most common DTCs on the top 10 vehicles, at full depth.

## A DTC page must include
- Code definition and what the computer is actually monitoring
- Enable criteria, where available
- Likely causes ranked by real-world frequency for that engine, with pattern
  failures called out (e.g. AFM lifters on the GM 5.3 for P0300)
- Step-by-step tests with spec values, connector/pin info where available, and
  what good vs. bad looks like
- Related TSBs and recalls
- Common misdiagnoses and parts people throw at it that don't fix it
- Typical repair time and rough parts cost
- Sources list

## A repair procedure must include
- Exact applications (years, engine, transmission)
- Tools and special tools
- Parts and fluids with specs and capacities
- Step-by-step procedure with torque specs and sequences inline
- Known gotchas from techs who've done the job
- Safety warnings
- Sources list

## Working style
- Work autonomously in batches and commit after each with a clear message.
- After the competitor teardown and the first 5 DTC pages, stop and summarize for
  review. After approval, continue through the milestone without stopping per page.
- If a source is blocked, log it and move on rather than stopping.
