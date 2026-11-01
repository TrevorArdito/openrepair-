# Marketplace module (off by default)

Buy and sell new and used parts, matched to vehicles with the shared fitment matcher.
Turn on with `ENABLE_MARKETPLACE=true`. Design: `docs/COMMERCE_DESIGN.md` §4.

What's built (v1, no payments):
- Seller profiles (city/state shown; ZIP private; never a street address)
- Listings: new / used / remanufactured / for-parts, price, quantity, pickup/shipping,
  part number, brand, source VIN + mileage for used parts, up to 12 photos (same safe photo
  pipeline as guides: location data stripped), fitment rows (empty = universal part)
- Browse/search: words, part numbers, category, condition, state, price, "fits my vehicle"
- Buyer-seller messages per listing (no emails/phone numbers exchanged by the system)
- Reports (stolen, prohibited, scam, counterfeit, wrong fitment) → moderator queue
- Review queue: listings from accounts still on probation wait for a moderator
- Seller license verification (dismantler/business license number + state, checked by a
  moderator on the state's public lookup; no documents stored) → "Verified" badge
- Prohibited-item rules (`rules.py`): emissions delete/defeat parts, used airbags/SRS (new
  only from verified sellers), catalytic converters (new = EPA/CARB proof, used = verified
  licensed sellers only). Sellers accept the listing rules on every listing.
- Whole vehicles (category `vehicle`): VIN required for 1981+ and checked (check digit, NHTSA
  decode sets year/make/model, no duplicate open listings), title status, lien, runs/drives,
  odometer; private sellers max 5 open vehicle listings (more needs a verified dealer license)
- Watch list ("Saved"); email alert on new messages (link only, one per unread batch)
- Moderator actions logged in the moderation log; marketplace data in "download my data";
  deleting an account deletes its seller profile and listings.

Later: payments through a payment provider (we never store card data), buyer reviews after a
completed order, email notifications for new messages, distance search by ZIP, linking
listings to a parts catalog (`parts` module), affiliate links.
