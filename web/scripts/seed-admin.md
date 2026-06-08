# Seeding the first admin

The security rules require an existing admin to create another, so the first
one is seeded manually (once):

**Production:** Firebase Console → Firestore → create collection `admins` →
add a document with **ID** = `donovan@lcmsyoungadults.org` (lowercase) and a
field `email: "donovan@lcmsyoungadults.org"`.

After that, sign in at `/admin` with that Google account and use the in-app
"Manage admins" UI (admin UI plan) to add/remove others.
