# OpenCausation.org

Coming-soon landing page for **OpenCausation.org** — an introductory gateway to structured medical causation review.

Sister site to [OpenCausation.com](https://github.com/llanesjoseph/OpenCausation.com); same page, hosted on its own Firebase project (`opencausationorg`).

## Structure

```
public/
  index.html            # the page (self-contained CSS, gentle fades, responsive)
  assets/library-bg.png # hero render (1672×941)
firebase.json           # Firebase Hosting config (site: opencausationorg)
.firebaserc             # Firebase project/target
porkbun.sh              # Porkbun DNS API helper (DOMAIN defaults to opencausation.org)
.github/workflows/firebase-deploy.yml  # auto-deploy to Firebase on push to main
```

## Deploy

Automatic on push to `main` (GitHub Action, keyless `FIREBASE_TOKEN`). Manual:

```bash
firebase deploy --only hosting --project opencausationorg
```

Live at `opencausationorg.web.app`, with custom domains `opencausation.org` and `www.opencausation.org`.

## DNS

`porkbun.sh` manages records via the Porkbun API (creds in `~/.porkbun.json`, never committed).

```bash
./porkbun.sh list
./porkbun.sh point-firebase <TXT> <A_IP>   # clean slate + point at Firebase
```

# Deploys via Workload Identity Federation — no stored credentials.
