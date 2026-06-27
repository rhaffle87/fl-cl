# FL-CL Experiment Run Summary: FL-CL-EWC-Baseline

- **MLflow Run ID**: `b94fd533206445bcbbff5427b8e5187f`
- **Total FL Rounds**: `100`
- **Continual Learning (EWC) Lambda**: `0.25`
- **Generated At**: 2026-06-28 00:21:36

## Final Metrics Summary
| Metric | Value |
|:---|:---|
| accuracy | 0.988095 |
| accuracy_class_0 | 0.957637 |
| accuracy_class_1 | 1.000000 |
| accuracy_class_2 | 0.998715 |
| accuracy_class_3 | 0.472506 |
| accuracy_class_4 | 0.971375 |
| best_loss | 0.090372 |
| best_round | 100.000000 |
| final_best_loss | nan |
| final_best_round | nan |
| loss | 0.090372 |

## Convergence Plots per Traffic Class
Click on each class below to view its convergence plot (incorporating Loss, Global Accuracy, and Class Accuracy):

### Botnet Convergence Plot
![Botnet Accuracy Plot](plots/class_1_botnet.png)

### DNS Exfil Convergence Plot
![DNS Exfil Accuracy Plot](plots/class_2_dns_exfil.png)

### DoS Convergence Plot
![DoS Accuracy Plot](plots/class_4_dos.png)

### Normal Convergence Plot
![Normal Accuracy Plot](plots/class_0_normal.png)

### SSH Brute Force Convergence Plot
![SSH Brute Force Accuracy Plot](plots/class_3_ssh_brute_force.png)

