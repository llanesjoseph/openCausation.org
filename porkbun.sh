#!/usr/bin/env bash
# Porkbun DNS helper for opencausation.com
# Creds live in ~/.porkbun.json (chmod 600), never in this repo.
#
#   { "apikey": "pk1_...", "secretapikey": "sk1_..." }
#
# Usage:
#   ./porkbun.sh ping                         # verify keys work
#   ./porkbun.sh list                         # list all DNS records
#   ./porkbun.sh add  <TYPE> <NAME> <CONTENT> [TTL]   # NAME="" for root/apex
#   ./porkbun.sh del  <ID>                    # delete a record by id
#   ./porkbun.sh nuke                         # delete EVERY record (clean slate)
#   ./porkbun.sh point-firebase <TXT_TOKEN> <A_IP_1> [A_IP_2 ...]
#       # clean slate, then add Firebase: apex A record(s) + verification TXT

set -euo pipefail
DOMAIN="${PORKBUN_DOMAIN:-opencausation.org}"
CREDS="$HOME/.porkbun.json"
API="https://api.porkbun.com/api/json/v3"

[ -f "$CREDS" ] || { echo "Missing $CREDS — create it with your apikey/secretapikey."; exit 1; }
AUTH=$(cat "$CREDS")

post() { curl -s "$API/$1" -H 'Content-Type: application/json' -d "$2"; }

cmd="${1:-list}"
case "$cmd" in
  ping)
    post "ping" "$AUTH" | python3 -m json.tool
    ;;
  list)
    post "dns/retrieve/$DOMAIN" "$AUTH" | python3 -c '
import sys, json
d = json.load(sys.stdin)
if d.get("status") != "SUCCESS":
    print("ERROR:", d); sys.exit(1)
recs = d.get("records", [])
print("%d records\n" % len(recs))
print("%10s  %-6s %-34s %5s  %s" % ("ID","TYPE","NAME","TTL","CONTENT"))
print("-"*100)
for r in sorted(recs, key=lambda r:(r["type"], r["name"])):
    print("%10s  %-6s %-34s %5s  %s" % (r["id"], r["type"], r["name"], r.get("ttl",""), r["content"]))
'
    ;;
  add)
    TYPE="$2"; NAME="$3"; CONTENT="$4"; TTL="${5:-600}"
    BODY=$(python3 -c '
import json,sys
a=json.load(open(sys.argv[1]))
a.update({"name":sys.argv[2],"type":sys.argv[3],"content":sys.argv[4],"ttl":sys.argv[5]})
print(json.dumps(a))' "$CREDS" "$NAME" "$TYPE" "$CONTENT" "$TTL")
    post "dns/create/$DOMAIN" "$BODY" | python3 -m json.tool
    ;;
  del)
    ID="$2"
    post "dns/delete/$DOMAIN/$ID" "$AUTH" | python3 -m json.tool
    ;;
  nuke)
    # Delete everything EXCEPT NS/SOA (those are the nameserver delegation — removing them kills the domain)
    ids=$(post "dns/retrieve/$DOMAIN" "$AUTH" | python3 -c 'import sys,json;[print(r["id"]) for r in json.load(sys.stdin).get("records",[]) if r["type"] not in ("NS","SOA")]')
    [ -z "$ids" ] && { echo "Nothing to delete."; exit 0; }
    echo "Deleting $(echo "$ids" | wc -l | tr -d " ") records (keeping NS/SOA)..."
    for id in $ids; do
      printf "  del %-10s -> " "$id"
      post "dns/delete/$DOMAIN/$id" "$AUTH" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("status"))'
    done
    echo "Clean slate done (nameservers preserved)."
    ;;
  point-firebase)
    TXT="$2"; shift 2
    [ -z "$TXT" ] && { echo "Usage: point-firebase <TXT_TOKEN> <A_IP_1> [A_IP_2 ...]"; exit 1; }
    [ "$#" -lt 1 ] && { echo "Need at least one A-record IP."; exit 1; }
    "$0" nuke
    echo "Adding Firebase verification TXT..."
    "$0" add TXT "" "$TXT"
    for ip in "$@"; do
      echo "Adding apex A -> $ip"
      "$0" add A "" "$ip"
    done
    echo "---- final state ----"
    "$0" list
    ;;
  *)
    echo "Unknown command: $cmd"; exit 1;;
esac
