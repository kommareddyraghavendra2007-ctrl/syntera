"""Allow: python -m evaluation.run"""
from evaluation.runner import run_evaluation
import argparse

parser = argparse.ArgumentParser(description="SYNTERA Retrieval Evaluation")
parser.add_argument("--repository-id", required=True)
parser.add_argument("--k", type=int, default=10)
parser.add_argument("--backend-url", default="http://localhost:8000")
args = parser.parse_args()
run_evaluation(args.repository_id, args.k, args.backend_url)
