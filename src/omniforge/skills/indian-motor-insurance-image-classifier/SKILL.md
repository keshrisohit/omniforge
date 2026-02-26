---
name: indian-motor-insurance-image-classifier
description: Classify Indian motor insurance claim images into 33 document tags. Given a list of image paths (local, S3, GCS, or HTTP URLs), classifies each image and returns a JSON array with image name, tag, confidence, and photo_type. Use when asked to classify insurance images, documents, or photos for a motor claim.
---

# Indian Motor Insurance Image Classifier

Classify one or more motor insurance claim images into 33 document tags.

Supported image sources (any mix):

- **Local paths** — `/path/to/image.jpg`, `./relative/path.png`, or globs like `folder/*.jpg`
- **S3 URLs** — `s3://bucket-name/path/to/image.jpg`
- **GCS URLs** — `gs://bucket-name/path/to/image.jpg`
- **HTTP/HTTPS** — `https://example.com/image.jpg`

Supported file types: `.jpg` `.jpeg` `.png` `.pdf` `.mp4`

---

## Step 1 — Collect image paths

Gather all image paths/URLs from the user's request. Accept any mix of sources.
If the user provides a folder path, expand it to individual file paths using Glob
(matching `*.jpg`, `*.jpeg`, `*.png`, `*.pdf`, `*.mp4`).

---

## Step 2 — Locate the classifier script

Look for the script using Glob in this order:

1. `~/.claude/skills/indian-motor-insurance-image-classifier/scripts/classify_agent.py`
2. `**/.claude/skills/indian-motor-insurance-image-classifier/scripts/classify_agent.py`

If neither is found, write the **Embedded Script** (see bottom of this file) to
`/tmp/indian_motor_classify.py` using the Write tool, then use that path.

---

## Step 3 — Check prerequisites

Run a quick dependency check before classifying:

```bash
python3 -c "import PIL, openai; print('OK')" 2>&1
```

If the check fails, install required packages:

```bash
pip install Pillow openai python-dotenv
```

Optional dependencies (install only if needed):

- **PDF support**: `pip install pdf2image` + poppler (`brew install poppler` / `apt-get install poppler-utils`)
- **S3 support**: `pip install boto3` + AWS credentials (`aws configure`)
- **GCS support**: `pip install google-cloud-storage` + set `GOOGLE_APPLICATION_CREDENTIALS`

Check that `OPENROUTER_KEY` is available:

```bash
python3 -c "import os; k=os.environ.get('OPENROUTER_KEY',''); print('Key found' if k else 'MISSING — add OPENROUTER_KEY to .env')"
```

---

## Step 4 — Run the classifier

Use Bash to run the script. Always capture both stdout (JSON) and stderr (progress).

### Classify specific files

```bash
python3 /path/to/classify_agent.py --pretty \
  /path/to/image1.jpg \
  s3://bucket/image2.png \
  gs://bucket/document.pdf
```

### Classify via stdin (JSON array)

```bash
echo '["img1.jpg","s3://bucket/img2.png"]' | \
  python3 /path/to/classify_agent.py --stdin --pretty
```

### Change model (default: gemini-2.0-flash)

```bash
python3 /path/to/classify_agent.py --model gpt-4.1-nano --pretty image.jpg
```

### List available models

```bash
python3 /path/to/classify_agent.py --list-models
```

Available models: `gemini-2.0-flash` (default) · `gemini-2.5-flash` · `gpt-4.1-nano` · `gpt-4.1-mini` · `gpt-4o-mini` · `claude-haiku-4-5` · `claude-haiku-3.5`

---

## Step 5 — Parse and present results

The script writes a JSON array to stdout. Each element contains:

| Field | Type | Description |
| --- | --- | --- |
| `image` | string | Filename extracted from path |
| `path` | string | Original path/URL as provided |
| `source` | string | `local`, `s3`, `gcs`, or `http` |
| `tag` | string | One of 33 classification tags |
| `confidence` | float | Model confidence 0.0–1.0 |
| `photo_type` | string | Broad category group (or null) |
| `cost_usd` | float | API cost for this image |
| `input_tokens` | int | Prompt tokens used |
| `output_tokens` | int | Completion tokens used |
| `error` | string | Present only if classification failed |
| `note` | string | Present only for auto-tagged videos |

### The 33 classification tags

**Vehicle photos**: Accident Details · AI Photos · Break-in Photo · Re-Inspection Photos · Previous Claim Photos · RC Photo · Vehicle Details · Mparivahan · Vahan · Video

**KYC / Identity**: Customer Aadhar · Customer Bank · Customer PAN · Driving Licence

**Driver**: Driver Details · Driver Affidavit

**Insurance**: Insurance Details · Insurance Policy · Previous Year Policy · Claim Form · Intimation Form · Client Signature

**Financial**: Estimate · Invoice · Survey Bill · Difference Bill · Supporting Bill · Garage Cheque · Garage GST · Garage PAN · Garage Details · Payment Receipt · Satisfaction Voucher

**General**: Others

### Photo type groups

| `photo_type` | Tags covered |
| --- | --- |
| `vehicle_details` | Vehicle photos, RC, Mparivahan, Vahan, Video |
| `customer-kyc` | Aadhaar, PAN, Bank documents |
| `driver_details` | Driving licence, driver forms |
| `insurance_details` | Policy docs, claim forms |
| `loss_assessment` | Bills, invoices, estimates |
| `null` | "Others" tag |

Present results as a summary table for small batches, or counts-by-tag + total
cost for large batches. Always offer to show the full JSON on request.

Example output format:

```text
Classified 5 images (total cost: $0.000480):

  damage_front.jpg  → Accident Details    (conf=0.97)  vehicle_details
  policy_doc.pdf    → Insurance Policy    (conf=0.95)  insurance_details
  aadhar_card.jpg   → Customer Aadhar     (conf=0.99)  customer-kyc
  repair_bill.jpg   → Invoice             (conf=0.92)  loss_assessment
  video_clip.mp4    → Video               (conf=1.00)  vehicle_details  [auto-tagged]
```

---

## Step 6 — Handle errors

Each result may have an `error` field. Common errors and fixes:

| Error | Fix |
| --- | --- |
| `OPENROUTER_KEY not set` | Add `OPENROUTER_KEY=sk-...` to `.env` file |
| `File not found` | Check path; use absolute paths to be safe |
| `boto3 is not installed` | Run `pip install boto3` |
| `No AWS credentials found` | Run `aws configure` or set `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` |
| `google-cloud-storage is not installed` | Run `pip install google-cloud-storage` |
| `GCS error` | Check `GOOGLE_APPLICATION_CREDENTIALS` env var |
| `HTTP 403` | URL is private; download manually and use local path |
| `pdf2image not installed` | Run `pip install pdf2image` + install poppler |
| `Classification failed` | Transient API error; retry or check OPENROUTER_KEY quota |

For images with errors, report them clearly and continue with the rest. Never
abort the whole batch because one image failed.

---

## Embedded Script

If `classify_agent.py` cannot be found on disk, write the following code to
`/tmp/indian_motor_classify.py` using the Write tool, then run it.

```python
"""
Indian Motor Insurance Image Classifier
========================================
Classifies images into 33 document tags for Indian motor insurance claims.

Supported sources:
  - Local paths  : /path/to/image.jpg  or  relative/path.png
  - S3 URLs      : s3://bucket/path/to/image.jpg
  - GCS URLs     : gs://bucket/path/to/image.jpg
  - HTTP/HTTPS   : https://example.com/image.jpg

File types: .jpg .jpeg .png .pdf  (MP4 videos auto-tagged as "Video")

Usage:
    python classify_agent.py image1.jpg s3://bucket/img2.png
    python classify_agent.py --model gpt-4.1-nano --pretty *.jpg
    python classify_agent.py --stdin          # reads JSON array from stdin
    python classify_agent.py --list-models

Output (stdout): JSON array. Progress written to stderr.
"""

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv  # type: ignore[import-untyped]
    load_dotenv()
except ImportError:
    pass

try:
    from PIL import Image, ImageOps  # type: ignore[import-untyped]
except ImportError:
    print("ERROR: Pillow not installed. Run: pip install Pillow", file=sys.stderr)
    sys.exit(1)

try:
    from openai import OpenAI  # type: ignore[import-untyped]
except ImportError:
    print("ERROR: openai not installed. Run: pip install openai", file=sys.stderr)
    sys.exit(1)

try:
    from pdf2image import convert_from_bytes as _pdf_convert  # type: ignore[import-untyped]
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    import boto3  # type: ignore[import-untyped]
    from botocore.exceptions import ClientError, NoCredentialsError  # type: ignore[import-untyped]
    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False
    ClientError = Exception
    NoCredentialsError = Exception

try:
    from google.cloud import storage as gcs_storage  # type: ignore[import-untyped]
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False

OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY", "")

POSSIBLE_TAGS = [
    "Accident Details", "AI Photos", "Break-in Photo", "Claim Form",
    "Client Signature", "Customer Aadhar", "Customer Bank", "Customer PAN",
    "Difference Bill", "Driver Affidavit", "Driver Details", "Driving Licence",
    "Estimate", "Garage Cheque", "Garage GST", "Garage PAN", "Garage Details",
    "Insurance Details", "Insurance Policy", "Previous Year Policy",
    "Intimation Form", "Invoice", "Mparivahan", "Others", "Payment Receipt",
    "RC Photo", "Re-Inspection Photos", "Previous Claim Photos",
    "Satisfaction Voucher", "Supporting Bill", "Survey Bill", "Vahan",
    "Vehicle Details", "Video",
]

TAG_TO_PHOTOTYPE: dict = {
    "Accident Details": "vehicle_details", "AI Photos": "vehicle_details",
    "Break-in Photo": "vehicle_details", "Claim Form": "insurance_details",
    "Client Signature": "insurance_details", "Customer Aadhar": "customer-kyc",
    "Customer Bank": "customer-kyc", "Customer PAN": "customer-kyc",
    "Difference Bill": "loss_assessment", "Driver Affidavit": "driver_details",
    "Driver Details": "driver_details", "Driving Licence": "driver_details",
    "Estimate": "loss_assessment", "Garage Cheque": "loss_assessment",
    "Garage GST": "loss_assessment", "Garage PAN": "loss_assessment",
    "Garage Details": "loss_assessment", "Insurance Details": "insurance_details",
    "Insurance Policy": "insurance_details", "Previous Year Policy": "insurance_details",
    "Intimation Form": "insurance_details", "Invoice": "loss_assessment",
    "Mparivahan": "vehicle_details", "Others": None,
    "Payment Receipt": "loss_assessment", "RC Photo": "vehicle_details",
    "Re-Inspection Photos": "vehicle_details", "Previous Claim Photos": "vehicle_details",
    "Satisfaction Voucher": "loss_assessment", "Supporting Bill": "loss_assessment",
    "Survey Bill": "loss_assessment", "Vahan": "vehicle_details",
    "Vehicle Details": "vehicle_details", "Video": "vehicle_details",
}

MODELS: dict = {
    "gpt-4.1-nano":    {"openrouter_id": "openai/gpt-4.1-nano",             "label": "GPT-4.1-nano",    "input_per_mtok": 0.10, "output_per_mtok": 0.40, "detail": "high"},
    "gpt-4.1-mini":    {"openrouter_id": "openai/gpt-4.1-mini",             "label": "GPT-4.1-mini",    "input_per_mtok": 0.40, "output_per_mtok": 1.60, "detail": "high"},
    "gpt-4o-mini":     {"openrouter_id": "openai/gpt-4o-mini",              "label": "GPT-4o-mini",     "input_per_mtok": 0.15, "output_per_mtok": 0.60, "detail": "high"},
    "gemini-2.0-flash":{"openrouter_id": "google/gemini-2.0-flash-001",     "label": "Gemini 2.0 Flash","input_per_mtok": 0.10, "output_per_mtok": 0.40, "detail": None},
    "gemini-2.5-flash":{"openrouter_id": "google/gemini-2.5-flash-preview", "label": "Gemini 2.5 Flash","input_per_mtok": 0.15, "output_per_mtok": 0.60, "detail": None},
    "claude-haiku-4-5":{"openrouter_id": "anthropic/claude-haiku-4-5",      "label": "Claude Haiku 4.5","input_per_mtok": 0.80, "output_per_mtok": 4.00, "detail": None},
    "claude-haiku-3.5":{"openrouter_id": "anthropic/claude-3.5-haiku",      "label": "Claude 3.5 Haiku","input_per_mtok": 0.80, "output_per_mtok": 4.00, "detail": None},
}

DEFAULT_MODEL = "gemini-2.0-flash"
PDF_CONF_THRESHOLD = 0.85
PDF_MAX_PAGES = 3

SYSTEM_PROMPT = """You are an expert document classifier for Indian motor insurance claims.
Classify the image into exactly one of these 34 categories.

VEHICLE PHOTOS: Accident Details | AI Photos | Break-in Photo | Re-Inspection Photos | Previous Claim Photos | RC Photo | Vehicle Details | Mparivahan | Vahan | Video
IDENTITY / KYC: Customer Aadhar | Customer Bank | Customer PAN | Driving Licence
DRIVER: Driver Details | Driver Affidavit
INSURANCE: Insurance Details | Insurance Policy | Previous Year Policy | Claim Form | Intimation Form | Client Signature
FINANCIAL: Estimate | Invoice | Survey Bill | Difference Bill | Supporting Bill | Garage Cheque | Garage GST | Garage PAN | Garage Details | Payment Receipt | Satisfaction Voucher
GENERAL: Others

Key identifiers:
- Customer Aadhar: UIDAI emblem, 12-digit UID, QR code, bilingual text
- Customer PAN: blue background, Income Tax Dept header, 10-char alphanumeric
- Driving Licence: RTO-issued, DL number, vehicle class codes
- Customer Bank: cancelled cheque, passbook, or bank statement with IFSC
- RC Photo: Registration Certificate book/card with chassis/engine details
- Mparivahan/Vahan: app or portal screenshot showing vehicle registration info
- Accident Details: photos of vehicle damage
- Vehicle Details: general vehicle exterior photos (front/rear/side/odometer)
- Estimate: pre-repair quotation from garage
- Invoice: final post-repair bill from garage
- Survey Bill: surveyor damage assessment with cost breakdown

Respond with JSON only:
{"tag": "<one of the 34 tags>", "confidence": <0.0-1.0>}"""

USER_PROMPT = "Classify this insurance document image."


def get_client():
    if not OPENROUTER_KEY:
        raise RuntimeError("OPENROUTER_KEY not set. Add it to .env or environment variables.")
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_KEY)


def detect_source(path):
    if path.startswith("s3://"): return "s3"
    if path.startswith("gs://"): return "gcs"
    if path.startswith(("http://", "https://")): return "http"
    return "local"


def load_image_bytes(path):
    source = detect_source(path)
    if source == "local":
        p = Path(path)
        if not p.exists(): raise FileNotFoundError(f"File not found: {path}")
        return p.read_bytes(), "local"
    if source == "s3":
        if not S3_AVAILABLE: raise ImportError("boto3 not installed. Run: pip install boto3")
        parsed = urlparse(path)
        buf = BytesIO()
        try:
            boto3.client("s3").download_fileobj(parsed.netloc, parsed.path.lstrip("/"), buf)
        except NoCredentialsError:
            raise RuntimeError("No AWS credentials. Run 'aws configure' or set AWS_ACCESS_KEY_ID.")
        except ClientError as e:
            raise RuntimeError(f"S3 error: {e}")
        return buf.getvalue(), "s3"
    if source == "gcs":
        if not GCS_AVAILABLE: raise ImportError("google-cloud-storage not installed. Run: pip install google-cloud-storage")
        parsed = urlparse(path)
        try:
            client = gcs_storage.Client()
            return client.bucket(parsed.netloc).blob(parsed.path.lstrip("/")).download_as_bytes(), "gcs"
        except Exception as e:
            raise RuntimeError(f"GCS error: {e}")
    req = urllib.request.Request(path, headers={"User-Agent": "insurance-classifier/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read(), "http"
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"URL error: {e.reason}")


def preprocess_image(image_bytes, max_size=384):
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    try: img = ImageOps.exif_transpose(img)
    except Exception: pass
    img.thumbnail((max_size, max_size), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=70)
    return base64.b64encode(buf.getvalue()).decode()


def pdf_to_pages(pdf_bytes):
    if not PDF_SUPPORT:
        raise ImportError("pdf2image not installed. Run: pip install pdf2image (+ poppler)")
    pages = _pdf_convert(pdf_bytes, dpi=150)
    result = []
    for page in pages:
        buf = BytesIO()
        page.convert("RGB").save(buf, format="JPEG", quality=85)
        result.append(buf.getvalue())
    return result


def call_model(client, image_b64, model_key):
    m = MODELS[model_key]
    img_content = {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
    if m.get("detail"): img_content["image_url"]["detail"] = m["detail"]
    resp = client.chat.completions.create(
        model=m["openrouter_id"], max_tokens=200, temperature=0,
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user", "content": [img_content, {"type": "text", "text": USER_PROMPT}]}],
        extra_headers={"HTTP-Referer": "https://insurance-classifier", "X-Title": "Insurance Doc Classifier"},
    )
    raw = resp.choices[0].message.content.strip()
    usage = resp.usage
    return {"raw": raw, "input_tokens": usage.prompt_tokens if usage else 0,
            "output_tokens": usage.completion_tokens if usage else 0}


def compute_cost(model_key, in_tok, out_tok):
    m = MODELS[model_key]
    return (in_tok * m["input_per_mtok"] + out_tok * m["output_per_mtok"]) / 1_000_000


def parse_response(raw):
    try:
        clean = raw.strip()
        if "```" in clean:
            for part in clean.split("```"):
                part = part.strip()
                if part.startswith("json"): part = part[4:].strip()
                try: return json.loads(part)
                except Exception: pass
        return json.loads(clean)
    except Exception:
        return {"tag": "Others", "confidence": 0.0}


def normalize_tag(tag):
    if tag in POSSIBLE_TAGS: return tag
    return {t.lower(): t for t in POSSIBLE_TAGS}.get(tag.lower(), "Others")


def classify_bytes(client, image_bytes, model_key):
    api = call_model(client, preprocess_image(image_bytes), model_key)
    parsed = parse_response(api["raw"])
    tag = normalize_tag(parsed.get("tag", "Others"))
    return {"tag": tag, "confidence": parsed.get("confidence", 0.0),
            "input_tokens": api["input_tokens"], "output_tokens": api["output_tokens"],
            "cost_usd": compute_cost(model_key, api["input_tokens"], api["output_tokens"])}


def classify_pdf(client, pdf_bytes, model_key):
    try: pages = pdf_to_pages(pdf_bytes)
    except ImportError as e:
        return {"tag": "Others", "confidence": 0.0, "error": str(e),
                "cost_usd": 0.0, "input_tokens": 0, "output_tokens": 0}
    if not pages:
        return {"tag": "Others", "confidence": 0.0, "error": "PDF has no pages",
                "cost_usd": 0.0, "input_tokens": 0, "output_tokens": 0}
    best = {}
    total_cost = total_in = total_out = 0
    for page_bytes in pages[:PDF_MAX_PAGES]:
        r = classify_bytes(client, page_bytes, model_key)
        total_cost += r["cost_usd"]; total_in += r["input_tokens"]; total_out += r["output_tokens"]
        if not best or r["confidence"] > best["confidence"]: best = r.copy()
        if r["confidence"] >= PDF_CONF_THRESHOLD: break
    best.update({"cost_usd": total_cost, "input_tokens": total_in, "output_tokens": total_out})
    return best


def classify_one(client, path, model_key):
    name = Path(urlparse(path).path).name or path
    ext = Path(name).suffix.lower()
    source = detect_source(path)
    if ext == ".mp4":
        return {"image": name, "path": path, "source": source, "tag": "Video",
                "confidence": 1.0, "photo_type": "vehicle_details",
                "cost_usd": 0.0, "input_tokens": 0, "output_tokens": 0,
                "note": "auto-tagged as Video (no API call)"}
    try:
        image_bytes, resolved_source = load_image_bytes(path)
    except Exception as e:
        return {"image": name, "path": path, "source": source, "tag": "Others",
                "confidence": 0.0, "photo_type": None, "cost_usd": 0.0,
                "input_tokens": 0, "output_tokens": 0, "error": str(e)}
    try:
        result = classify_pdf(client, image_bytes, model_key) if ext == ".pdf" \
            else classify_bytes(client, image_bytes, model_key)
    except Exception as e:
        return {"image": name, "path": path, "source": resolved_source, "tag": "Others",
                "confidence": 0.0, "photo_type": None, "cost_usd": 0.0,
                "input_tokens": 0, "output_tokens": 0, "error": f"Classification failed: {e}"}
    out = {"image": name, "path": path, "source": resolved_source,
           "tag": result["tag"], "confidence": result["confidence"],
           "photo_type": TAG_TO_PHOTOTYPE.get(result["tag"]),
           "cost_usd": result["cost_usd"],
           "input_tokens": result["input_tokens"], "output_tokens": result["output_tokens"]}
    if "error" in result: out["error"] = result["error"]
    return out


def main():
    parser = argparse.ArgumentParser(description="Classify Indian motor insurance images.")
    parser.add_argument("images", nargs="*")
    parser.add_argument("--model", choices=list(MODELS.keys()), default=DEFAULT_MODEL)
    parser.add_argument("--stdin", action="store_true")
    parser.add_argument("--list-models", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    if args.list_models:
        for k, m in MODELS.items():
            print(f"  {k:<20}  {m['label']:<25}  {m['openrouter_id']}")
        return

    image_paths = list(args.images)
    if args.stdin:
        data = sys.stdin.read().strip()
        if data:
            try:
                extra = json.loads(data)
                image_paths.extend([str(p) for p in extra] if isinstance(extra, list) else [str(extra)])
            except json.JSONDecodeError:
                image_paths.extend(l.strip() for l in data.splitlines() if l.strip())

    if not image_paths:
        print("ERROR: No image paths provided.", file=sys.stderr); sys.exit(1)

    try: client = get_client()
    except RuntimeError as e: print(f"ERROR: {e}", file=sys.stderr); sys.exit(1)

    print(f"Classifying {len(image_paths)} image(s) with {MODELS[args.model]['label']}...", file=sys.stderr)
    results = []
    total_cost = 0.0
    for i, path in enumerate(image_paths, 1):
        print(f"  [{i:3}/{len(image_paths)}] {path}", file=sys.stderr, end="", flush=True)
        r = classify_one(client, path, args.model)
        results.append(r); total_cost += r.get("cost_usd", 0.0)
        if "error" in r:
            print(f"\n             ERROR: {r['error']}", file=sys.stderr)
        else:
            note = f"  [{r['note']}]" if r.get("note") else ""
            print(f"  → {r['tag']} (conf={r['confidence']:.2f}, ${r['cost_usd']:.6f}){note}", file=sys.stderr)

    print(f"\nDone: {len(results)} image(s) | total: ${total_cost:.6f}", file=sys.stderr)
    print(json.dumps(results, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
```
