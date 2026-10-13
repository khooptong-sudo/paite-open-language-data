"""Upload the training files and benchmark to Hugging Face.

Log in first (once):  hf auth login
Then:                 python scripts/publish_hf.py [repo_id]

The dataset card is huggingface/README.md. Re-run after every change to
training/ or eval/; unchanged files are skipped by the Hub.
"""

import sys
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[1]
REPO = sys.argv[1] if len(sys.argv) > 1 else "khooptong-sudo/paite-open-language-data"

api = HfApi()
api.create_repo(REPO, repo_type="dataset", exist_ok=True)
api.upload_file(path_or_fileobj=ROOT / "huggingface" / "README.md", path_in_repo="README.md",
                repo_id=REPO, repo_type="dataset")
for folder in ("training", "eval"):
    api.upload_folder(folder_path=ROOT / folder, path_in_repo=folder, repo_id=REPO, repo_type="dataset",
                      commit_message=f"Sync {folder}/ from GitHub")
print(f"https://huggingface.co/datasets/{REPO}")
