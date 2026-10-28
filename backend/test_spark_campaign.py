"""
test_spark_campaign.py
Runs a full campaign with Muse Spark as the planner.
Falls back to the mock planner if Spark fails.
"""

import time
from campaign import run_campaign, mock_planner
from spark_planner import spark_planner


def planner(current, tried, rejections):
    print("   ...asking Muse Spark")
    try:
        return spark_planner(current, tried, rejections)
    except Exception as e:
        print(f"   [Spark failed: {e}] -> using the mock planner instead")
        return mock_planner(current, tried, rejections)


start = time.time()
r = run_campaign(
    "CC(C)Cc1ccc(cc1)C(C)C(=O)O", planner=planner, max_steps=3, min_similarity=0.4
)
print(f"\nTook {time.time() - start:.0f} seconds")
print(f"START: {r['start']['smiles']}  QED {r['start']['qed']}  LogP {r['start']['logp']}")
for s in r["steps"]:
    print(f"\nSTEP {s['step']} [{s['planner']}]: {s['edit_name']}")
    print(f"  Spark says: {s['rationale']}")
    print(f"  result: {s['after']['smiles']}")
    print(f"  QED {s['before']['qed']} -> {s['after']['qed']}, "
          f"LogP {s['before']['logp']} -> {s['after']['logp']}")
print(f"\nREJECTED ({len(r['rejections'])}):")
for j in r["rejections"]:
    print(f"  step {j['step']} | {j['edit_id']} | {j['reason']}")
print(f"\nSTOPPED BECAUSE: {r['stop_reason']}")