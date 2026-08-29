# FL-CL MLflow Full Runs Inspection & Standardization Scorecard

- **Generated At**: 2026-08-29 01:22:42
- **Total Finished Runs Audited**: `88`
- **Database**: `/root/mlflow.db`

## 1. Experiment Registry Overview

| ID | Experiment Name | Total Finished Runs | Artifact Location |
|:---|:---|:---:|:---|
| `0` | **Default** | `0` | `mlflow-artifacts:/0` |
| `1` | **FL-CL-CyberDefense** | `58` | `mlflow-artifacts:/1` |
| `2` | **FCL-Sweep-Verification** | `4` | `mlflow-artifacts:/2` |
| `3` | **FCL-Parameter-Analysis-Sweep** | `1` | `mlflow-artifacts:/3` |
| `4` | **FCL-Representative-Matrix-Sweep** | `25` | `mlflow-artifacts:/4` |

---

## 2. Detailed Run Scorecard (Formatted by Experiment)

### Experiment 1: FL-CL-CyberDefense (58 Runs)

| Run ID | Model | CL Strategy | Aggregator | DP | Accuracy | Loss | Macro F1 | Duration | Benign Acc | SSH Acc | DoS Acc | Exfil Acc | Botnet Acc |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `94f38bf5` | `transformer` | `EWC` | `TrimmedMean` | `OFF` | **N/A** | N/A | N/A | 104s | ??? | ??? | ??? | ??? | ??? |
| `0fb2bed6` | `transformer` | `EWC` | `TrimmedMean` | `OFF` | **N/A** | N/A | N/A | 104s | ??? | ??? | ??? | ??? | ??? |
| `8d1ffea8` | `mlp` | `AGEM` | `Krum` | `OFF` | **N/A** | N/A | N/A | 104s | ??? | ??? | ??? | ??? | ??? |
| `039e5d3e` | `mlp` | `AGEM` | `Krum` | `OFF` | **N/A** | N/A | N/A | 104s | ??? | ??? | ??? | ??? | ??? |
| `0e9075a5` | `mlp` | `AGEM` | `FedAvg` | `OFF` | **N/A** | N/A | N/A | 104s | ??? | ??? | ??? | ??? | ??? |
| `67be5ff9` | `mlp` | `AGEM` | `FedAvg` | `OFF` | **N/A** | N/A | N/A | 104s | ??? | ??? | ??? | ??? | ??? |
| `b0abd320` | `mlp` | `AGEM` | `FedMedian` | `OFF` | **N/A** | N/A | N/A | 104s | ??? | ??? | ??? | ??? | ??? |
| `e58a1cf9` | `mlp` | `AGEM` | `FedMedian` | `OFF` | **N/A** | N/A | N/A | 534s | ??? | ??? | ??? | ??? | ??? |
| `d02e7589` | `mlp` | `AGEM` | `TrimmedMean` | `OFF` | **N/A** | N/A | N/A | 799s | ??? | ??? | ??? | ??? | ??? |
| `31a590e3` | `mlp` | `AGEM` | `TrimmedMean` | `OFF` | **N/A** | N/A | N/A | 800s | ??? | ??? | ??? | ??? | ??? |
| `ee2c8aec` | `cnn` | `AGEM` | `Krum` | `OFF` | **N/A** | N/A | N/A | 798s | ??? | ??? | ??? | ??? | ??? |
| `05be61a4` | `cnn` | `AGEM` | `Krum` | `OFF` | **N/A** | N/A | N/A | 799s | ??? | ??? | ??? | ??? | ??? |
| `6eb264d7` | `cnn` | `AGEM` | `FedAvg` | `OFF` | **N/A** | N/A | N/A | 800s | ??? | ??? | ??? | ??? | ??? |
| `52584d49` | `cnn` | `AGEM` | `FedAvg` | `OFF` | **N/A** | N/A | N/A | 799s | ??? | ??? | ??? | ??? | ??? |
| `0ab45513` | `cnn` | `AGEM` | `FedMedian` | `OFF` | **N/A** | N/A | N/A | 799s | ??? | ??? | ??? | ??? | ??? |
| `e6aa4dd6` | `cnn` | `AGEM` | `FedMedian` | `OFF` | **N/A** | N/A | N/A | 799s | ??? | ??? | ??? | ??? | ??? |
| `2cd986bd` | `cnn` | `AGEM` | `TrimmedMean` | `OFF` | **N/A** | N/A | N/A | 799s | ??? | ??? | ??? | ??? | ??? |
| `774250be` | `cnn` | `AGEM` | `TrimmedMean` | `OFF` | **N/A** | N/A | N/A | 797s | ??? | ??? | ??? | ??? | ??? |
| `f34060f0` | `cnn` | `EWC` | `FedAvg` | `OFF` | **99.65%** | 1.8324 | 95.45% | 247s | 99.5% | 100.0% | 100.0% | 100.0% | 100.0% |
| `1535db84` | `cnn` | `GEM` | `TrimmedMean` | `OFF` | **99.41%** | 0.0129 | 71.01% | 4418s | 99.4% | 100.0% | 100.0% | 100.0% | 100.0% |
| `0bbd5c17` | `cnn` | `EWC` | `TrimmedMean` | `OFF` | **98.64%** | 1.7948 | 73.50% | 429s | 99.5% | 100.0% | 99.2% | 100.0% | 55.7% |
| `ff325e00` | `cnn` | `GEM` | `FedAvg` | `OFF` | **99.62%** | 0.0128 | 90.40% | 464s | 99.5% | 100.0% | 100.0% | 100.0% | 100.0% |
| `f63490e2` | `cnn` | `EWC` | `FedAvg` | `OFF` | **99.88%** | 0.0528 | 60.63% | 2888s | 100.0% | 0.0% | 100.0% | 100.0% | 94.4% |
| `e5244991` | `cnn` | `GEM` | `FedAvg` | `OFF` | **99.31%** | 0.0225 | 83.67% | 468s | 99.2% | 100.0% | 99.8% | 100.0% | 100.0% |
| `4652ca42` | `cnn` | `EWC` | `FedAvg` | `OFF` | **99.52%** | 0.8657 | 78.98% | 247s | 99.9% | 0.0% | 99.6% | 100.0% | 100.0% |
| `a7470e19` | `cnn` | `EWC` | `TrimmedMean` | `OFF` | **99.30%** | 0.4497 | 62.59% | 246s | 99.6% | 0.0% | 99.6% | 100.0% | 100.0% |
| `c4c1c625` | `mlp` | `EWC` | `FedAvg` | `OFF` | **99.50%** | 1.7242 | 79.45% | 240s | 99.8% | 0.0% | 100.0% | 100.0% | 100.0% |
| `aaa09342` | `transformer` | `EWC` | `FedAvg` | `OFF` | **99.31%** | 0.0218 | 83.24% | 274s | 99.2% | 100.0% | 99.6% | 100.0% | 100.0% |
| `40b7de07` | `cnn` | `EWC` | `TrimmedMean` | `OFF` | **98.87%** | 1.1166 | 73.59% | 247s | 99.8% | 0.0% | 100.0% | 100.0% | 77.5% |
| `bae73416` | `cnn` | `EWC` | `TrimmedMean` | `OFF` | **75.23%** | 0.7557 | 77.10% | 598s | 72.4% | 100.0% | 100.0% | 100.0% | 66.6% |
| `1db4414e` | `cnn` | `EWC` | `FedAvg` | `OFF` | **99.13%** | 2.6383 | 76.01% | 623s | 99.7% | 100.0% | 100.0% | 100.0% | 53.7% |
| `847e5b87` | `cnn` | `EWC` | `FedAvg` | `OFF` | **99.42%** | 0.0656 | 79.24% | 392s | 99.8% | 0.0% | 100.0% | 100.0% | 96.3% |
| `c679a286` | `cnn` | `EWC` | `FedAvg` | `OFF` | **99.61%** | 14.6966 | 93.00% | 204s | 99.6% | 100.0% | 99.6% | 100.0% | 100.0% |
| `f3719a52` | `cnn` | `EWC` | `TrimmedMean` | `OFF` | **92.11%** | 1.5397 | 87.26% | 393s | 99.7% | 100.0% | 100.0% | 100.0% | 55.0% |
| `c89b5c07` | `cnn` | `EWC` | `FedAvg` | `OFF` | **92.12%** | 2.7586 | 83.63% | 396s | 99.7% | 100.0% | 100.0% | 100.0% | 55.3% |
| `c56d1f47` | `cnn` | `EWC` | `FedAvg` | `OFF` | **99.73%** | 6.4653 | 95.60% | 395s | 99.6% | 100.0% | 100.0% | 100.0% | 100.0% |
| `80be12d7` | `cnn` | `EWC` | `FedAvg` | `OFF` | **99.77%** | 2.3929 | 92.06% | 396s | 99.7% | 100.0% | 100.0% | 100.0% | 100.0% |
| `e2b6948a` | `cnn` | `EWC` | `FedAvg` | `OFF` | **99.37%** | 0.4312 | 91.03% | 210s | 99.2% | 100.0% | 100.0% | 100.0% | 100.0% |
| `fdf6937b` | `cnn` | `EWC` | `FedAvg` | `OFF` | **N/A** | N/A | N/A | 74s | ??? | ??? | ??? | ??? | ??? |
| `b0232ee3` | `cnn` | `EWC` | `FedAvg` | `OFF` | **99.53%** | 0.9216 | 79.55% | 209s | 99.9% | 0.0% | 100.0% | 100.0% | 100.0% |
| `db970d96` | `cnn` | `EWC` | `TrimmedMean` | `OFF` | **84.07%** | 1.3047 | 69.98% | 598s | 86.5% | 100.0% | 100.0% | 100.0% | 60.4% |
| `50930e6f` | `cnn` | `EWC` | `FedAvg` | `OFF` | **99.76%** | 1.9980 | 94.98% | 622s | 99.8% | 100.0% | 99.7% | 100.0% | 96.4% |
| `ac2717ba` | `cnn` | `EWC` | `FedAvg` | `OFF` | **99.69%** | 3.4956 | 91.63% | 389s | 99.6% | 100.0% | 100.0% | 100.0% | 98.2% |
| `5fd5677d` | `cnn` | `EWC` | `FedAvg` | `OFF` | **99.29%** | 3.9780 | 90.36% | 203s | 99.5% | 100.0% | 99.6% | 100.0% | 78.7% |
| `a97c8a6a` | `cnn` | `EWC` | `TrimmedMean` | `OFF` | **91.80%** | 5.1469 | 81.59% | 396s | 99.4% | 100.0% | 99.4% | 100.0% | 55.1% |
| `575be92a` | `cnn` | `EWC` | `FedAvg` | `OFF` | **83.31%** | 1.1575 | 72.18% | 394s | 84.7% | 100.0% | 99.6% | 100.0% | 63.9% |
| `1966a3e8` | `cnn` | `EWC` | `FedAvg` | `OFF` | **99.57%** | 7.3459 | 91.91% | 395s | 99.6% | 100.0% | 99.6% | 100.0% | 98.2% |
| `d4d1dac7` | `cnn` | `EWC` | `FedAvg` | `OFF` | **99.57%** | 3.4586 | 93.04% | 393s | 99.6% | 100.0% | 99.8% | 100.0% | 96.3% |
| `bbb12a1c` | `cnn` | `EWC` | `FedAvg` | `OFF` | **98.99%** | 0.4210 | 90.94% | 210s | 99.7% | 100.0% | 100.0% | 80.8% | 100.0% |
| `0501bc2a` | `cnn` | `EWC` | `TrimmedMean` | `OFF` | **92.11%** | 1.7073 | 84.58% | 597s | 99.7% | 100.0% | 99.7% | 100.0% | 54.1% |
| `2273a7f9` | `cnn` | `EWC` | `FedAvg` | `OFF` | **99.80%** | 5.5730 | 94.67% | 622s | 99.8% | 100.0% | 99.9% | 100.0% | 100.0% |
| `f5d3666d` | `cnn` | `EWC` | `FedAvg` | `OFF` | **99.69%** | 1.4962 | 94.66% | 390s | 99.6% | 100.0% | 100.0% | 100.0% | 98.2% |
| `d99bfc9c` | `cnn` | `EWC` | `FedAvg` | `OFF` | **99.76%** | 2.5147 | 96.31% | 204s | 99.7% | 100.0% | 100.0% | 100.0% | 100.0% |
| `68ad7430` | `cnn` | `EWC` | `TrimmedMean` | `OFF` | **90.84%** | 0.5305 | 73.73% | 597s | 99.7% | 100.0% | 100.0% | 100.0% | 1.9% |
| `e06191be` | `cnn` | `EWC` | `FedAvg` | `OFF` | **99.64%** | 0.4581 | 92.20% | 622s | 99.7% | 100.0% | 100.0% | 100.0% | 87.7% |
| `c1cffad6` | `cnn` | `EWC` | `FedAvg` | `OFF` | **98.14%** | 0.2405 | 73.13% | 331s | 99.6% | 100.0% | 100.0% | 100.0% | 0.0% |
| `0b878435` | `cnn` | `EWC` | `FedAvg` | `OFF` | **97.36%** | 0.7215 | 59.30% | 117s | 100.0% | 0.0% | 100.0% | 100.0% | 0.0% |
| `75a9f3a5` | `cnn` | `EWC` | `FedAvg` | `OFF` | **N/A** | N/A | N/A | 51s | ??? | ??? | ??? | ??? | ??? |

### Experiment 2: FCL-Sweep-Verification (4 Runs)

| Run ID | Model | CL Strategy | Aggregator | DP | Accuracy | Loss | Macro F1 | Duration | Benign Acc | SSH Acc | DoS Acc | Exfil Acc | Botnet Acc |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `1aa15dcf` | `N/A` | `N/A` | `N/A` | `OFF` | **N/A** | N/A | N/A | 791s | ??? | ??? | ??? | ??? | ??? |
| `b9abdaeb` | `N/A` | `N/A` | `N/A` | `OFF` | **N/A** | N/A | N/A | 0s | ??? | ??? | ??? | ??? | ??? |
| `871ac9b4` | `N/A` | `N/A` | `N/A` | `OFF` | **N/A** | N/A | N/A | 0s | ??? | ??? | ??? | ??? | ??? |
| `715cd025` | `N/A` | `N/A` | `N/A` | `OFF` | **N/A** | N/A | N/A | 0s | ??? | ??? | ??? | ??? | ??? |

### Experiment 3: FCL-Parameter-Analysis-Sweep (1 Runs)

| Run ID | Model | CL Strategy | Aggregator | DP | Accuracy | Loss | Macro F1 | Duration | Benign Acc | SSH Acc | DoS Acc | Exfil Acc | Botnet Acc |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `b3cefe77` | `N/A` | `N/A` | `N/A` | `OFF` | **N/A** | N/A | N/A | 9440s | ??? | ??? | ??? | ??? | ??? |

### Experiment 4: FCL-Representative-Matrix-Sweep (25 Runs)

| Run ID | Model | CL Strategy | Aggregator | DP | Accuracy | Loss | Macro F1 | Duration | Benign Acc | SSH Acc | DoS Acc | Exfil Acc | Botnet Acc |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `79aee122` | `transformer` | `AGEM` | `Krum` | `OFF` | **N/A** | N/A | N/A | 670s | ??? | ??? | ??? | ??? | ??? |
| `2e659b39` | `transformer` | `AGEM` | `Krum` | `OFF` | **N/A** | N/A | N/A | 669s | ??? | ??? | ??? | ??? | ??? |
| `db69ad73` | `transformer` | `AGEM` | `FedAvg` | `OFF` | **N/A** | N/A | N/A | 667s | ??? | ??? | ??? | ??? | ??? |
| `38948b11` | `transformer` | `AGEM` | `FedAvg` | `OFF` | **N/A** | N/A | N/A | 668s | ??? | ??? | ??? | ??? | ??? |
| `9d3c8e86` | `transformer` | `AGEM` | `FedMedian` | `OFF` | **N/A** | N/A | N/A | 668s | ??? | ??? | ??? | ??? | ??? |
| `095b2f7a` | `transformer` | `AGEM` | `FedMedian` | `OFF` | **N/A** | N/A | N/A | 667s | ??? | ??? | ??? | ??? | ??? |
| `1177949c` | `transformer` | `AGEM` | `TrimmedMean` | `OFF` | **N/A** | N/A | N/A | 668s | ??? | ??? | ??? | ??? | ??? |
| `20be0ec8` | `transformer` | `AGEM` | `TrimmedMean` | `OFF` | **N/A** | N/A | N/A | 668s | ??? | ??? | ??? | ??? | ??? |
| `d20b8159` | `transformer` | `GEM` | `Krum` | `OFF` | **99.08%** | 0.0575 | 89.87% | 89s | 98.7% | 100.0% | 100.0% | 100.0% | 100.0% |
| `2a05354a` | `transformer` | `GEM` | `Krum` | `OFF` | **97.73%** | 0.1508 | 85.49% | 90s | 96.8% | 100.0% | 100.0% | 100.0% | 100.0% |
| `5f59dc4d` | `transformer` | `GEM` | `FedAvg` | `OFF` | **98.68%** | 0.0933 | 88.48% | 89s | 98.2% | 100.0% | 100.0% | 100.0% | 100.0% |
| `43c479c6` | `transformer` | `GEM` | `FedAvg` | `OFF` | **98.87%** | 0.0811 | 89.23% | 90s | 98.4% | 100.0% | 100.0% | 100.0% | 100.0% |
| `ecc151f1` | `transformer` | `GEM` | `FedMedian` | `OFF` | **98.86%** | 0.0732 | 89.47% | 88s | 98.4% | 100.0% | 100.0% | 100.0% | 100.0% |
| `f8384d30` | `transformer` | `GEM` | `FedMedian` | `OFF` | **99.30%** | 0.0594 | 92.57% | 86s | 99.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| `fa24ac04` | `transformer` | `GEM` | `TrimmedMean` | `OFF` | **98.64%** | 0.0898 | 88.51% | 89s | 98.4% | 100.0% | 98.8% | 100.0% | 100.0% |
| `7eecb118` | `transformer` | `GEM` | `TrimmedMean` | `OFF` | **99.55%** | 0.0621 | 93.27% | 89s | 99.4% | 100.0% | 100.0% | 100.0% | 100.0% |
| `fb70add3` | `transformer` | `EWC` | `Krum` | `OFF` | **98.68%** | 0.1155 | 89.17% | 90s | 98.2% | 100.0% | 100.0% | 100.0% | 100.0% |
| `5960aed8` | `transformer` | `EWC` | `Krum` | `OFF` | **98.41%** | 0.1619 | 87.47% | 89s | 98.1% | 100.0% | 100.0% | 100.0% | 91.6% |
| `106c0b0f` | `transformer` | `EWC` | `FedAvg` | `OFF` | **98.18%** | 0.2793 | 87.39% | 89s | 97.4% | 100.0% | 100.0% | 100.0% | 100.0% |
| `ee3cf805` | `transformer` | `EWC` | `FedAvg` | `OFF` | **99.11%** | 0.5166 | 93.71% | 87s | 99.1% | 100.0% | 100.0% | 100.0% | 93.7% |
| `9c5c0cd0` | `transformer` | `EWC` | `FedMedian` | `OFF` | **55.10%** | 0.8780 | 32.27% | 87s | 47.6% | 0.0% | 100.0% | 0.0% | 100.0% |
| `ab3ba7a3` | `transformer` | `EWC` | `FedMedian` | `OFF` | **21.33%** | 1.2445 | 18.26% | 88s | 0.0% | 0.0% | 100.0% | 0.0% | 100.0% |
| `aece07fc` | `transformer` | `EWC` | `FedAvg` | `OFF` | **N/A** | N/A | N/A | 10384s | ??? | ??? | ??? | ??? | ??? |
| `8b336720` | `transformer` | `EWC` | `FedMedian` | `OFF` | **N/A** | N/A | N/A | 193s | ??? | ??? | ??? | ??? | ??? |
| `d313e96e` | `N/A` | `N/A` | `N/A` | `OFF` | **N/A** | N/A | N/A | 35654s | ??? | ??? | ??? | ??? | ??? |

