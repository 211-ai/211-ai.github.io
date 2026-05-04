#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_PYTHON_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_BROWSER_MODEL = "Xenova/bge-small-en-v1.5"
DEFAULT_UI_DIR = Path("wallet_interface/ui")
DEFAULT_PACKAGE_DIR = Path("data/retrieval_package")
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def load_probe_texts(package_dir: Path, max_document_texts: int) -> list[str]:
    probes = [
        "food pantry",
        "emergency shelter",
        "utility assistance",
        "rental assistance for families",
        "mental health crisis support",
    ]
    documents_path = package_dir / "content" / "documents.parquet"
    if max_document_texts <= 0 or not documents_path.exists():
        return probes

    import pandas as pd

    frame = pd.read_parquet(documents_path, columns=["title", "text"]).fillna("")
    for row in frame.head(max_document_texts).to_dict(orient="records"):
        text = " ".join([str(row.get("title") or ""), str(row.get("text") or "")]).strip()
        if text:
            probes.append(text[:1200])
    return probes


def python_embeddings(texts: list[str], model_name: str) -> list[list[float]]:
    from scraper.build_retrieval_package import _ensure_torchvision_stub

    _ensure_torchvision_stub()
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return [[float(value) for value in vector.tolist()] for vector in vectors]


def browser_embeddings(texts: list[str], ui_dir: Path, model_name: str) -> list[list[float]]:
    ui_dir = ui_dir.resolve()
    with tempfile.TemporaryDirectory(dir=ui_dir, prefix=".bge-compat-") as tmp_dir:
        input_path = Path(tmp_dir) / "texts.json"
        script_path = Path(tmp_dir) / "embed.mjs"
        input_path.write_text(json.dumps({"texts": texts, "modelName": model_name}))
        script_path.write_text(
            """
import fs from "node:fs";
import { env, pipeline } from "@xenova/transformers";

env.allowLocalModels = false;
env.useBrowserCache = false;

const input = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const extractor = await pipeline("feature-extraction", input.modelName, { quantized: true });
const embeddings = [];
for (const text of input.texts) {
  const output = await extractor(text, { pooling: "mean", normalize: true });
  embeddings.push(Array.from(output.data).map((value) => Number(value)));
}
console.log(JSON.stringify({ embeddings }));
""".strip()
        )
        completed = subprocess.run(
            ["node", str(script_path), str(input_path)],
            cwd=ui_dir,
            check=True,
            text=True,
            capture_output=True,
        )
    payload = json.loads(completed.stdout)
    return [[float(value) for value in vector] for vector in payload["embeddings"]]


def cosine(left: list[float], right: list[float]) -> float:
    dot = 0.0
    left_norm = 0.0
    right_norm = 0.0
    for left_value, right_value in zip(left, right, strict=False):
        dot += left_value * right_value
        left_norm += left_value * left_value
        right_norm += right_value * right_value
    if left_norm <= 0 or right_norm <= 0:
        return 0.0
    return dot / (math.sqrt(left_norm) * math.sqrt(right_norm))


def validate_compatibility(
    *,
    package_dir: Path,
    ui_dir: Path,
    python_model: str,
    browser_model: str,
    max_document_texts: int,
) -> dict[str, Any]:
    texts = load_probe_texts(package_dir, max_document_texts)
    py_vectors = python_embeddings(texts, python_model)
    browser_vectors = browser_embeddings(texts, ui_dir, browser_model)
    if len(py_vectors) != len(browser_vectors):
        raise RuntimeError("Python and browser embedding counts differ")

    records: list[dict[str, Any]] = []
    for index, (text, py_vector, browser_vector) in enumerate(zip(texts, py_vectors, browser_vectors, strict=True)):
        records.append(
            {
                "index": index,
                "text_preview": text.replace("\n", " ")[:120],
                "python_dimension": len(py_vector),
                "browser_dimension": len(browser_vector),
                "cosine": cosine(py_vector, browser_vector),
            }
        )

    cosines = [record["cosine"] for record in records]
    return {
        "python_model": python_model,
        "browser_model": browser_model,
        "probe_count": len(records),
        "min_cosine": min(cosines) if cosines else None,
        "mean_cosine": sum(cosines) / len(cosines) if cosines else None,
        "max_cosine": max(cosines) if cosines else None,
        "dimension_mismatches": [record for record in records if record["python_dimension"] != record["browser_dimension"]],
        "records": records,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare Python and Transformers.js BGE-small embedding compatibility")
    parser.add_argument("--package-dir", type=Path, default=DEFAULT_PACKAGE_DIR)
    parser.add_argument("--ui-dir", type=Path, default=DEFAULT_UI_DIR)
    parser.add_argument("--python-model", default=DEFAULT_PYTHON_MODEL)
    parser.add_argument("--browser-model", default=DEFAULT_BROWSER_MODEL)
    parser.add_argument("--max-document-texts", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        result = validate_compatibility(
            package_dir=args.package_dir,
            ui_dir=args.ui_dir,
            python_model=args.python_model,
            browser_model=args.browser_model,
            max_document_texts=args.max_document_texts,
        )
    except subprocess.CalledProcessError as error:
        if error.stdout:
            sys.stderr.write(error.stdout)
        if error.stderr:
            sys.stderr.write(error.stderr)
        raise
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
