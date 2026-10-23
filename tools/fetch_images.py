"""Download real firearm photos from Wikimedia Commons, cut out background, save img/<slug>.webp"""
import io, json, os, sys, requests
from PIL import Image
from rembg import remove, new_session
UA = {"User-Agent": "MetaDropBot/1.0 (github.com/Nephilim66/codmeta-data)"}
API = "https://commons.wikimedia.org/w/api.php"
os.makedirs("img", exist_ok=True)
cred = json.load(open("img/credits.json")) if os.path.exists("img/credits.json") else {}
sess = new_session("isnet-general-use")
force = os.environ.get("FORCE") == "1"

def candidates(spec):
    if spec.startswith("File:"):
        p = {"action": "query", "titles": spec, "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": 1000, "format": "json"}
    else:
        p = {"action": "query", "generator": "search", "gsrsearch": "filetype:bitmap " + spec, "gsrnamespace": 6, "gsrlimit": 12,
             "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": 1000, "format": "json"}
    r = requests.get(API, params=p, headers=UA, timeout=30).json()
    pages = sorted(r.get("query", {}).get("pages", {}).values(), key=lambda x: x.get("index", 0))
    out = []
    for pg in pages:
        ii = (pg.get("imageinfo") or [{}])[0]
        w, h = ii.get("width", 0), ii.get("height", 0)
        if spec.startswith("File:") or (h and w / h >= 1.7 and w >= 800):
            lic = ii.get("extmetadata", {}).get("LicenseShortName", {}).get("value", "")
            out.append((pg["title"], ii.get("thumburl") or ii.get("url"), ii.get("descriptionurl"), lic))
    return out

for line in open("images.txt", encoding="utf-8"):
    line = line.strip()
    if not line or line.startswith("#"): continue
    slug, spec = [x.strip() for x in line.split("|", 1)]
    dst = f"img/{slug}.webp"
    if os.path.exists(dst) and not force and cred.get(slug, {}).get("spec") == spec: continue
    ok = False
    for title, url, page, lic in candidates(spec)[:4]:
        try:
            raw = requests.get(url, headers=UA, timeout=60).content
            im = remove(Image.open(io.BytesIO(raw)).convert("RGBA"), session=sess)
            bb = im.getbbox()
            if not bb: continue
            im = im.crop(bb)
            if im.width / max(im.height, 1) < 1.4: continue   # not a side profile
            im.thumbnail((760, 320), Image.LANCZOS)
            im.save(dst, "WEBP", quality=82, method=6)
            cred[slug] = {"spec": spec, "title": title, "page": page, "license": lic}
            print("OK", slug, title); ok = True; break
        except Exception as e:
            print("ERR", slug, title, e)
    if not ok: print("MISS", slug, spec)
json.dump(cred, open("img/credits.json", "w"), ensure_ascii=False, indent=1)
