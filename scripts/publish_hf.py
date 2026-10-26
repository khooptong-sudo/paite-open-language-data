"""Upload the dataset to Hugging Face: the card, training/, eval/, the community
translations from Paite Daily, the word list, and the credits.

Weekly, the GitHub Action .github/workflows/huggingface.yml runs this with the
HF_TOKEN repository secret, so Hugging Face always matches this repository.
By hand: log in once (hf auth login), then python scripts/publish_hf.py [repo_id]

The dataset card is huggingface/README.md. Unchanged files are skipped by the Hub.
"""

import sys
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[1]
REPO = sys.argv[1] if len(sys.argv) > 1 else "LamkaLabs/paite-open-language-data"

api = HfApi()
api.create_repo(REPO, repo_type="dataset", exist_ok=True)
api.upload_file(path_or_fileobj=ROOT / "huggingface" / "README.md", path_in_repo="README.md",
                repo_id=REPO, repo_type="dataset")
for folder in ("training", "eval", "community"):
    api.upload_folder(folder_path=ROOT / folder, path_in_repo=folder, repo_id=REPO, repo_type="dataset",
                      commit_message=f"Sync {folder}/ from GitHub")
for name in ("glossary.json", "CONTRIBUTORS.md", "LICENSE"):
    api.upload_file(path_or_fileobj=ROOT / name, path_in_repo=name, repo_id=REPO, repo_type="dataset",
                    commit_message=f"Sync {name} from GitHub")
print(f"https://huggingface.co/datasets/{REPO}")
