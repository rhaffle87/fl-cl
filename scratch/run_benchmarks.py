import os
import yaml
import subprocess
import glob

BENCHMARK_DIR = "configs/experiments"

def create_yaml(filename, updates):
    base_config = {
        "experiment": {"name": "FL-CL-Benchmark", "description": ""},
        "fl": {"rounds": 5, "min_clients": 2, "fraction_fit": 1.0, "fraction_evaluate": 1.0},
        "cl": {
            "strategy": "EWC", "ewc_lambda": 0.5, "gem_patterns_per_exp": 256,
            "gem_memory_strength": 0.5, "task_sequence": "benign,ssh,slowloris,dns_exfil,botnet",
            "complexity_score": 1.4, "comm_overhead_budget": 200000000
        },
        "security": {
            "poison_enabled": False, "poison_client_ids": ["A"], "poison_rate": 0.2,
            "poison_from_class": 0, "poison_to_class": 4, "dp_enabled": False,
            "dp_noise_multiplier": 0.0, "dp_max_grad_norm": 0.0, "aggregation_strategy": "FedAvg",
            "trimmed_mean_beta": 0.1
        },
        "model": {
            "type": "cnn", "prune_fraction": 0.2, "input_dim": 32, "num_classes": 5,
            "hidden_layers": [64, 32], "dropout": 0.2
        },
        "training": {
            "optimizer": "SGD", "lr": 0.003, "momentum": 0.9, "batch_size": 32,
            "epochs_per_round": 1, "class_weights": [1.0, 250.0, 2.0, 5.0, 50.0]
        },
        "features": {
            "columns": ["bidirectional_packets", "bidirectional_bytes", "duration_ms",
                        "src2dst_packets", "src2dst_bytes", "dst2src_packets", "dst2src_bytes",
                        "src2dst_mean_piat_ms", "dst2src_mean_piat_ms", "dst_port"]
        },
        "simulation": {
            "attack_duration_seconds": 15,
            "stages": [{"mode": "benign"}, {"mode": "ssh"}, {"mode": "slowloris"},
                       {"mode": "dns_exfil"}, {"mode": "botnet"}]
        },
        "topology": {
            "aggregator": "10.10.130.10", "defender_a": "10.10.130.11",
            "defender_b": "10.10.130.12", "target_a": "10.10.110.15",
            "target_b": "10.10.120.15", "traffic_gen": "10.10.140.10",
            "flower_port": 8080, "mlflow_port": 5000
        },
        "notifications": {"telegram": {"enabled": False}},
        "checkpointing": {
            "save_dir": "/opt/mlflow-artifacts/checkpoints",
            "save_best": True, "export_torchscript": True
        },
        "mlops": {
            "mode": "experimental", "production_strategy": "scratch",
            "registered_model_name": "CyberDefenseNet"
        },
        "labeling": {"dos_duration_threshold_ms": 2000},
        "data_quality": {
            "jsd_threshold": 0.6, "gate_action": "alert",
            "baseline_stats_path": "configs/baseline_feature_stats.json",
            "baseline_class_distribution": "2000,10,200,50,100"
        }
    }

    # Apply updates
    for k, v in updates.items():
        if isinstance(v, dict) and k in base_config:
            base_config[k].update(v)
        else:
            base_config[k] = v

    filepath = os.path.join(BENCHMARK_DIR, filename)
    with open(filepath, "w") as f:
        yaml.dump(base_config, f, sort_keys=False)
    print(f"[+] Created {filepath}")

def generate_configs():
    # 1. Quick Test
    create_yaml("benchmark_quick.yaml", {
        "experiment": {"name": "FL-CL-Benchmark-Quick", "description": "Category 1: Fast / Quick Test"},
        "simulation": {"attack_duration_seconds": 15},
        "fl": {"rounds": 2, "fraction_fit": 1.0, "fraction_evaluate": 1.0, "min_clients": 2},
        "training": {"epochs_per_round": 1, "batch_size": 32, "lr": 0.01, "optimizer": "SGD", "momentum": 0.9, "class_weights": [1.0, 1.0, 1.0, 1.0, 1.0]},
        "cl": {"ewc_lambda": 0.5, "strategy": "EWC", "gem_patterns_per_exp": 256, "gem_memory_strength": 0.5, "task_sequence": "benign,ssh,slowloris,dns_exfil,botnet", "complexity_score": 1.4, "comm_overhead_budget": 200000000},
        "security": {"aggregation_strategy": "FedAvg", "dp_enabled": False, "dp_noise_multiplier": 0.0, "dp_max_grad_norm": 0.0, "poison_enabled": False, "poison_client_ids": ["A"], "poison_rate": 0.2, "poison_from_class": 0, "poison_to_class": 4, "trimmed_mean_beta": 0.1}
    })

    # 2. Balanced Test
    create_yaml("benchmark_balanced.yaml", {
        "experiment": {"name": "FL-CL-Benchmark-Balanced", "description": "Category 2: Medium / Balanced Test"},
        "simulation": {"attack_duration_seconds": 50},
        "fl": {"rounds": 5, "fraction_fit": 1.0, "fraction_evaluate": 1.0, "min_clients": 2},
        "training": {"epochs_per_round": 3, "batch_size": 64, "lr": 0.005, "optimizer": "SGD", "momentum": 0.9, "class_weights": [1.0, 1.0, 1.0, 1.0, 1.0]},
        "cl": {"ewc_lambda": 0.8, "strategy": "EWC", "gem_patterns_per_exp": 256, "gem_memory_strength": 0.5, "task_sequence": "benign,ssh,slowloris,dns_exfil,botnet", "complexity_score": 1.4, "comm_overhead_budget": 200000000},
        "security": {"aggregation_strategy": "FedAvg", "dp_enabled": True, "dp_noise_multiplier": 0.1, "dp_max_grad_norm": 10.0, "poison_enabled": False, "poison_client_ids": ["A"], "poison_rate": 0.2, "poison_from_class": 0, "poison_to_class": 4, "trimmed_mean_beta": 0.1}
    })

    # 3. Stressed Test
    create_yaml("benchmark_stressed.yaml", {
        "experiment": {"name": "FL-CL-Benchmark-Stressed", "description": "Category 3: Highly Stressed Test"},
        "simulation": {"attack_duration_seconds": 90},
        "fl": {"rounds": 15, "fraction_fit": 1.0, "fraction_evaluate": 1.0, "min_clients": 2},
        "training": {"epochs_per_round": 10, "batch_size": 128, "lr": 0.05, "optimizer": "SGD", "momentum": 0.9, "class_weights": [1.0, 1.0, 1.0, 1.0, 1.0]},
        "cl": {"ewc_lambda": 2.0, "strategy": "EWC", "gem_patterns_per_exp": 256, "gem_memory_strength": 0.5, "task_sequence": "benign,ssh,slowloris,dns_exfil,botnet", "complexity_score": 1.4, "comm_overhead_budget": 200000000},
        "security": {"aggregation_strategy": "FedAvg", "dp_enabled": True, "dp_noise_multiplier": 1.5, "dp_max_grad_norm": 1.0, "poison_enabled": False, "poison_client_ids": ["A"], "poison_rate": 0.2, "poison_from_class": 0, "poison_to_class": 4, "trimmed_mean_beta": 0.1}
    })

    # 4. Real-World Test
    create_yaml("benchmark_realworld.yaml", {
        "experiment": {"name": "FL-CL-Benchmark-RealWorld", "description": "Category 4: Real-World Scenarios"},
        "simulation": {"attack_duration_seconds": 90},
        "fl": {"rounds": 10, "fraction_fit": 0.5, "fraction_evaluate": 1.0, "min_clients": 2},
        "training": {"epochs_per_round": 3, "batch_size": 64, "lr": 0.001, "optimizer": "SGD", "momentum": 0.9, "class_weights": [1.0, 1.0, 1.0, 1.0, 1.0]},
        "cl": {"ewc_lambda": 0.8, "strategy": "EWC", "gem_patterns_per_exp": 256, "gem_memory_strength": 0.5, "task_sequence": "benign,ssh,slowloris,dns_exfil,botnet", "complexity_score": 1.4, "comm_overhead_budget": 200000000},
        "security": {"aggregation_strategy": "TrimmedMean", "dp_enabled": True, "dp_noise_multiplier": 0.5, "dp_max_grad_norm": 5.0, "poison_enabled": True, "poison_client_ids": ["A"], "poison_rate": 0.2, "poison_from_class": 0, "poison_to_class": 4, "trimmed_mean_beta": 0.1}
    })

def run_experiment(config_file):
    import sys
    cfg_path = os.path.join(BENCHMARK_DIR, config_file)
    cmd = ["/opt/flower-env/bin/python3", "src/orchestrate.py", "--config", str(cfg_path)]
    print(f"[*] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[!] Error running {config_file}:\n{result.stderr}")
    else:
        print(f"[+] Successfully completed {config_file}")
        
    # Optional: read exports or print metrics

if __name__ == "__main__":
    if not os.path.exists(BENCHMARK_DIR):
        os.makedirs(BENCHMARK_DIR)
        
    print("Generating YAML Configurations...")
    generate_configs()
    
    configs = [
        "benchmark_quick.yaml",
        "benchmark_balanced.yaml",
        "benchmark_stressed.yaml",
        "benchmark_realworld.yaml"
    ]
    for cfg in configs:
        print(f"\n{'='*50}\nStarting {cfg}\n{'='*50}")
        run_experiment(cfg)
