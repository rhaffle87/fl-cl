import mlflow

client = mlflow.tracking.MlflowClient("http://localhost:5000")

# Get all experiments
experiments = client.search_experiments()
print(f"Experiments found: {len(experiments)}")
for exp in experiments:
    print(f"  Experiment ID: {exp.experiment_id} | Name: {exp.name}")

# Get ALL runs across all experiments
all_runs = []
for exp in experiments:
    runs = client.search_runs(
        [exp.experiment_id],
        order_by=["attributes.start_time DESC"],
        max_results=20
    )
    all_runs.extend(runs)

print(f"\nTotal runs found: {len(all_runs)}")
for r in all_runs:
    metrics = dict(r.data.metrics)
    tags = r.data.tags
    name = tags.get("mlflow.runName", r.info.run_id[:8])
    # Filter for FL rounds metrics only (not system)
    fl_metrics = {k: v for k, v in metrics.items() if not k.startswith("system/")}
    print(f"---")
    print(f"Run: {r.info.run_id[:12]}  Name: {name}")
    print(f"Status: {r.info.status}")
    print(f"FL Metrics: {fl_metrics}")
    if fl_metrics:
        print(f"  => Has FL data!")
