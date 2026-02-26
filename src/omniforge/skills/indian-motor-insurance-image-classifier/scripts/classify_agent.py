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

Output (stdout): JSON array — one object per image.
Progress        : written to stderr (stdout stays clean JSON).
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
    pass  # .env support optional

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
    ClientError = Exception  # placeholder for type checker
    NoCredentialsError = Exception

try:
    from google.cloud import storage as gcs_storage  # type: ignore[import-untyped]
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False

# ── Constants ─────────────────────────────────────────────────────────────────

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
    "Accident Details":      "vehicle_details",
    "AI Photos":             "vehicle_details",
    "Break-in Photo":        "vehicle_details",
    "Claim Form":            "insurance_details",
    "Client Signature":      "insurance_details",
    "Customer Aadhar":       "customer-kyc",
    "Customer Bank":         "customer-kyc",
    "Customer PAN":          "customer-kyc",
    "Difference Bill":       "loss_assessment",
    "Driver Affidavit":      "driver_details",
    "Driver Details":        "driver_details",
    "Driving Licence":       "driver_details",
    "Estimate":              "loss_assessment",
    "Garage Cheque":         "loss_assessment",
    "Garage GST":            "loss_assessment",
    "Garage PAN":            "loss_assessment",
    "Garage Details":        "loss_assessment",
    "Insurance Details":     "insurance_details",
    "Insurance Policy":      "insurance_details",
    "Previous Year Policy":  "insurance_details",
    "Intimation Form":       "insurance_details",
    "Invoice":               "loss_assessment",
    "Mparivahan":            "vehicle_details",
    "Others":                None,
    "Payment Receipt":       "loss_assessment",
    "RC Photo":              "vehicle_details",
    "Re-Inspection Photos":  "vehicle_details",
    "Previous Claim Photos": "vehicle_details",
    "Satisfaction Voucher":  "loss_assessment",
    "Supporting Bill":       "loss_assessment",
    "Survey Bill":           "loss_assessment",
    "Vahan":                 "vehicle_details",
    "Vehicle Details":       "vehicle_details",
    "Video":                 "vehicle_details",
}

MODELS: dict = {
    "gpt-4.1-nano": {
        "openrouter_id": "openai/gpt-4.1-nano",
        "label": "GPT-4.1-nano",
        "input_per_mtok": 0.10, "output_per_mtok": 0.40, "detail": "high",
    },
    "gpt-4.1-mini": {
        "openrouter_id": "openai/gpt-4.1-mini",
        "label": "GPT-4.1-mini",
        "input_per_mtok": 0.40, "output_per_mtok": 1.60, "detail": "high",
    },
    "gpt-4o-mini": {
        "openrouter_id": "openai/gpt-4o-mini",
        "label": "GPT-4o-mini",
        "input_per_mtok": 0.15, "output_per_mtok": 0.60, "detail": "high",
    },
    "gemini-2.0-flash": {
        "openrouter_id": "google/gemini-2.0-flash-001",
        "label": "Gemini 2.0 Flash",
        "input_per_mtok": 0.10, "output_per_mtok": 0.40, "detail": None,
    },
    "gemini-2.5-flash": {
        "openrouter_id": "google/gemini-2.5-flash-preview",
        "label": "Gemini 2.5 Flash",
        "input_per_mtok": 0.15, "output_per_mtok": 0.60, "detail": None,
    },
    "claude-haiku-4-5": {
        "openrouter_id": "anthropic/claude-haiku-4-5",
        "label": "Claude Haiku 4.5",
        "input_per_mtok": 0.80, "output_per_mtok": 4.00, "detail": None,
    },
    "claude-haiku-3.5": {
        "openrouter_id": "anthropic/claude-3.5-haiku",
        "label": "Claude 3.5 Haiku",
        "input_per_mtok": 0.80, "output_per_mtok": 4.00, "detail": None,
    },
}

DEFAULT_MODEL = "gemini-2.0-flash"

SYSTEM_PROMPT = """You are an expert document classifier for Indian motor insurance claims.
Your job is to classify document images into exactly one of these 34 categories.

VEHICLE PHOTOS:
- Accident Details: Photos showing vehicle damage from an accident
- AI Photos: AI-generated or processed inspection images
- Break-in Photo: Photos showing break-in / theft damage to vehicle
- Re-Inspection Photos: Photos taken during re-inspection of the vehicle
- Previous Claim Photos: Photos from a previous insurance claim
- RC Photo: Registration Certificate (RC) book or card photo
- Vehicle Details: General vehicle photos — front, rear, side, odometer, chassis number
- Mparivahan: Screenshot from mParivahan app showing vehicle registration info
- Vahan: Screenshot from Vahan portal showing vehicle or registration data
- Video: Video file (classify if thumbnail or video frame is visible)

IDENTITY / KYC DOCUMENTS:
- Customer Aadhar: Aadhaar card — UIDAI issued, 12-digit UID, Ashoka emblem, QR code
- Customer Bank: Bank document — cancelled cheque, bank statement, passbook, IFSC visible
- Customer PAN: PAN card — Income Tax Dept, 10-char alphanumeric, blue background
- Driving Licence: Driving Licence issued by RTO — DL number, photo, vehicle class codes

DRIVER DOCUMENTS:
- Driver Details: Driver information form or printed summary (not the licence itself)
- Driver Affidavit: Sworn affidavit or declaration document signed by the driver

INSURANCE DOCUMENTS:
- Insurance Details: Cover note or summary page showing policy highlights and coverage
- Insurance Policy: Full motor insurance policy document with schedule and terms
- Previous Year Policy: Prior year insurance policy document
- Claim Form: Insurance claim application form filled by the claimant
- Intimation Form: Claim intimation / notification form submitted to insurer
- Client Signature: Signature page or consent/declaration form signed by the client

FINANCIAL / BILLING DOCUMENTS:
- Estimate: Pre-repair estimate or quotation from garage
- Invoice: Final repair invoice or bill from garage (post-repair)
- Survey Bill: Surveyor's damage assessment bill or report with cost breakdown
- Difference Bill: Supplementary bill for additional damage found after initial survey
- Supporting Bill: Additional supporting receipts or bills for spare parts, towing, etc.
- Garage Cheque: Cancelled cheque from the garage/workshop for payment purposes
- Garage GST: GST registration certificate or GST invoice from the garage
- Garage PAN: PAN card belonging to the garage or workshop
- Garage Details: Garage registration, address proof, or information form
- Payment Receipt: Receipt or acknowledgment of payment made to garage or vendor
- Satisfaction Voucher: Customer satisfaction voucher signed after claim settlement

GENERAL:
- Others: Anything not matching any category above

Respond with JSON only — no markdown fences, no explanation outside the JSON:
{"tag": "<one of the 34 tags above>", "confidence": <0.0-1.0>}"""

USER_PROMPT = "Classify this insurance document image."

PDF_CONF_THRESHOLD = 0.85
PDF_MAX_PAGES = 3

# ── API ────────────────────────────────────────────────────────────────────────

def get_client() -> OpenAI:
    if not OPENROUTER_KEY:
        raise RuntimeError(
            "OPENROUTER_KEY not set. "
            "Add OPENROUTER_KEY=sk-... to your .env file or environment variables."
        )
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_KEY)


# ── Image loading ──────────────────────────────────────────────────────────────

def detect_source(path: str) -> str:
    if path.startswith("s3://"):
        return "s3"
    if path.startswith("gs://"):
        return "gcs"
    if path.startswith(("http://", "https://")):
        return "http"
    return "local"


def load_bytes_local(path: str) -> bytes:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return p.read_bytes()


def load_bytes_s3(path: str) -> bytes:
    if not S3_AVAILABLE:
        raise ImportError(
            "boto3 is not installed. Run: pip install boto3\n"
            "AWS credentials must also be configured (aws configure or env vars)."
        )
    parsed = urlparse(path)
    bucket, key = parsed.netloc, parsed.path.lstrip("/")
    try:
        buf = BytesIO()
        boto3.client("s3").download_fileobj(bucket, key, buf)
        return buf.getvalue()
    except NoCredentialsError:
        raise RuntimeError(
            "No AWS credentials found. Run 'aws configure' or set "
            "AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY."
        )
    except ClientError as e:
        code = e.response["Error"]["Code"]  # type: ignore[attr-defined]
        raise RuntimeError(f"S3 {code}: {e.response['Error']['Message']}")  # type: ignore[index]


def load_bytes_gcs(path: str) -> bytes:
    if not GCS_AVAILABLE:
        raise ImportError(
            "google-cloud-storage is not installed. "
            "Run: pip install google-cloud-storage\n"
            "GCP credentials must also be configured (GOOGLE_APPLICATION_CREDENTIALS)."
        )
    parsed = urlparse(path)
    bucket_name, blob_name = parsed.netloc, parsed.path.lstrip("/")
    try:
        client = gcs_storage.Client()
        return client.bucket(bucket_name).blob(blob_name).download_as_bytes()
    except Exception as e:
        raise RuntimeError(f"GCS error: {e}")


def load_bytes_http(path: str) -> bytes:
    req = urllib.request.Request(path, headers={"User-Agent": "insurance-classifier/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"URL error: {e.reason}")


def load_image_bytes(path: str) -> tuple:
    """Return (bytes, source_type). Raises on error."""
    source = detect_source(path)
    return {
        "local": load_bytes_local,
        "s3":    load_bytes_s3,
        "gcs":   load_bytes_gcs,
        "http":  load_bytes_http,
    }[source](path), source


# ── Preprocessing ──────────────────────────────────────────────────────────────

def preprocess_image(image_bytes: bytes, max_size: int = 384) -> str:
    """Resize, orient, and return as base64 JPEG string."""
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    img.thumbnail((max_size, max_size), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=70)
    return base64.b64encode(buf.getvalue()).decode()


def pdf_to_pages(pdf_bytes: bytes, dpi: int = 150) -> list:
    """Convert PDF pages to list of JPEG byte strings."""
    if not PDF_SUPPORT:
        raise ImportError(
            "pdf2image not installed. Run: pip install pdf2image\n"
            "Poppler also required:\n"
            "  macOS:  brew install poppler\n"
            "  Ubuntu: apt-get install poppler-utils\n"
            "  Windows: https://github.com/oschwartz10612/poppler-windows"
        )
    pages = _pdf_convert(pdf_bytes, dpi=dpi)
    result = []
    for page in pages:
        buf = BytesIO()
        page.convert("RGB").save(buf, format="JPEG", quality=85)
        result.append(buf.getvalue())
    return result


# ── API call ───────────────────────────────────────────────────────────────────

def call_model(client: OpenAI, image_b64: str, model_key: str) -> dict:
    m = MODELS[model_key]
    image_content: dict = {
        "type": "image_url",
        "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
    }
    if m.get("detail"):
        image_content["image_url"]["detail"] = m["detail"]
    resp = client.chat.completions.create(
        model=m["openrouter_id"],
        max_tokens=200,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [image_content, {"type": "text", "text": USER_PROMPT}]},
        ],
        extra_headers={"HTTP-Referer": "https://insurance-classifier", "X-Title": "Insurance Doc Classifier"},
    )
    raw = resp.choices[0].message.content.strip()
    usage = resp.usage
    return {
        "raw": raw,
        "input_tokens": usage.prompt_tokens if usage else 0,
        "output_tokens": usage.completion_tokens if usage else 0,
    }


def compute_cost(model_key: str, input_tok: int, output_tok: int) -> float:
    m = MODELS[model_key]
    return (input_tok * m["input_per_mtok"] + output_tok * m["output_per_mtok"]) / 1_000_000


def parse_response(raw: str) -> dict:
    try:
        clean = raw.strip()
        if "```" in clean:
            for part in clean.split("```"):
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                try:
                    return json.loads(part)
                except Exception:
                    pass
        return json.loads(clean)
    except Exception:
        return {"tag": "Others", "confidence": 0.0}


def normalize_tag(tag: str) -> str:
    if tag in POSSIBLE_TAGS:
        return tag
    return {t.lower(): t for t in POSSIBLE_TAGS}.get(tag.lower(), "Others")


# ── Classification ─────────────────────────────────────────────────────────────

def classify_bytes(client: OpenAI, image_bytes: bytes, model_key: str) -> dict:
    b64 = preprocess_image(image_bytes)
    api = call_model(client, b64, model_key)
    parsed = parse_response(api["raw"])
    tag = normalize_tag(parsed.get("tag", "Others"))
    cost = compute_cost(model_key, api["input_tokens"], api["output_tokens"])
    return {"tag": tag, "confidence": parsed.get("confidence", 0.0),
            "input_tokens": api["input_tokens"], "output_tokens": api["output_tokens"],
            "cost_usd": cost}


def classify_pdf(client: OpenAI, pdf_bytes: bytes, model_key: str) -> dict:
    try:
        pages = pdf_to_pages(pdf_bytes)
    except ImportError as e:
        return {"tag": "Others", "confidence": 0.0, "error": str(e),
                "cost_usd": 0.0, "input_tokens": 0, "output_tokens": 0}
    if not pages:
        return {"tag": "Others", "confidence": 0.0, "error": "PDF has no pages",
                "cost_usd": 0.0, "input_tokens": 0, "output_tokens": 0}
    best: dict = {}
    total_cost = total_in = total_out = 0
    for page_bytes in pages[:PDF_MAX_PAGES]:
        r = classify_bytes(client, page_bytes, model_key)
        total_cost += r["cost_usd"]
        total_in += r["input_tokens"]
        total_out += r["output_tokens"]
        if not best or r["confidence"] > best["confidence"]:
            best = r.copy()
        if r["confidence"] >= PDF_CONF_THRESHOLD:
            break
    best.update({"cost_usd": total_cost, "input_tokens": total_in, "output_tokens": total_out})
    return best


def classify_one(client: OpenAI, path: str, model_key: str) -> dict:
    """Classify one image from any source. Never raises — errors go into result."""
    name = Path(urlparse(path).path).name or path
    ext = Path(name).suffix.lower()
    source = detect_source(path)

    # MP4 videos: auto-tag, no API call
    if ext == ".mp4":
        return {"image": name, "path": path, "source": source,
                "tag": "Video", "confidence": 1.0, "photo_type": "vehicle_details",
                "cost_usd": 0.0, "input_tokens": 0, "output_tokens": 0,
                "note": "auto-tagged as Video (no API call)"}

    # Load bytes
    try:
        image_bytes, resolved_source = load_image_bytes(path)
    except Exception as e:
        return {"image": name, "path": path, "source": source,
                "tag": "Others", "confidence": 0.0, "photo_type": None,
                "cost_usd": 0.0, "input_tokens": 0, "output_tokens": 0, "error": str(e)}

    # Classify
    try:
        result = classify_pdf(client, image_bytes, model_key) if ext == ".pdf" \
            else classify_bytes(client, image_bytes, model_key)
    except Exception as e:
        return {"image": name, "path": path, "source": resolved_source,
                "tag": "Others", "confidence": 0.0, "photo_type": None,
                "cost_usd": 0.0, "input_tokens": 0, "output_tokens": 0,
                "error": f"Classification failed: {e}"}

    out = {"image": name, "path": path, "source": resolved_source,
           "tag": result["tag"], "confidence": result["confidence"],
           "photo_type": TAG_TO_PHOTOTYPE.get(result["tag"]),
           "cost_usd": result["cost_usd"],
           "input_tokens": result["input_tokens"], "output_tokens": result["output_tokens"]}
    if "error" in result:
        out["error"] = result["error"]
    return out


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Classify Indian motor insurance images from local/S3/GCS/HTTP.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Sources: local path | s3://bucket/key | gs://bucket/key | https://url
Output : JSON array to stdout; progress to stderr

Examples:
  python classify_agent.py photo.jpg policy.pdf
  python classify_agent.py s3://bucket/damage.jpg
  python classify_agent.py --model gpt-4.1-nano --pretty *.jpg
  echo '["a.jpg","s3://b/c.png"]' | python classify_agent.py --stdin
""")
    parser.add_argument("images", nargs="*", help="Image paths or URLs")
    parser.add_argument("--model", choices=list(MODELS.keys()), default=DEFAULT_MODEL)
    parser.add_argument("--stdin", action="store_true",
                        help="Also read JSON array of paths from stdin")
    parser.add_argument("--list-models", action="store_true")
    parser.add_argument("--pretty", action="store_true", help="Indent JSON output")
    args = parser.parse_args()

    if args.list_models:
        for key, m in MODELS.items():
            print(f"  {key:<20}  {m['label']:<25}  {m['openrouter_id']}")
            print(f"  {'':20}  in ${m['input_per_mtok']}/MTok  out ${m['output_per_mtok']}/MTok")
        return

    image_paths = list(args.images)
    if args.stdin:
        data = sys.stdin.read().strip()
        if data:
            try:
                extra = json.loads(data)
                image_paths.extend([str(p) for p in extra] if isinstance(extra, list) else [str(extra)])
            except json.JSONDecodeError:
                image_paths.extend(line.strip() for line in data.splitlines() if line.strip())

    if not image_paths:
        print("ERROR: No image paths. Pass as args or use --stdin.", file=sys.stderr)
        sys.exit(1)

    try:
        client = get_client()
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Classifying {len(image_paths)} image(s) with {MODELS[args.model]['label']}...",
          file=sys.stderr)

    results = []
    total_cost = 0.0
    for i, path in enumerate(image_paths, 1):
        print(f"  [{i:3}/{len(image_paths)}] {path}", file=sys.stderr, end="", flush=True)
        r = classify_one(client, path, args.model)
        results.append(r)
        total_cost += r.get("cost_usd", 0.0)
        if "error" in r:
            print(f"\n             ERROR: {r['error']}", file=sys.stderr)
        else:
            note = f"  [{r['note']}]" if r.get("note") else ""
            print(f"  → {r['tag']} (conf={r['confidence']:.2f}, ${r['cost_usd']:.6f}){note}",
                  file=sys.stderr)

    print(f"\nDone: {len(results)} image(s) | total: ${total_cost:.6f}", file=sys.stderr)
    print(json.dumps(results, indent=2 if args.pretty else None))


if __name__ == "__main__":
    main()
