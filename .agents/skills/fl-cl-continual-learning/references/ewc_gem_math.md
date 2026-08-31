# Continual Learning Mathematical Reference: EWC & GEM

## 1. Elastic Weight Consolidation (EWC)

### Loss Function
$$L(\theta) = L_t(\theta) + \sum_{k=1}^{t-1} \sum_{i} \frac{\lambda}{2} F_{k, i} (\theta_i - \theta_{k, i}^*)^2$$

Where:
- $L_t(\theta)$: Current task loss (CrossEntropy).
- $\lambda$: Regularization hyperparameter balancing plasticity vs. stability (default: `400.0` - `1000.0`).
- $\theta_{k, i}^*$: Optimal parameters saved after completing task $k$.
- $F_{k, i}$: Diagonal element of the empirical Fisher Information Matrix:
  $$F_i = \frac{1}{|D_k|} \sum_{x \in D_k} \left( \frac{\partial \log p(x | \theta)}{\partial \theta_i} \right)^2$$

### Class-Weighted Adaptation
In network intrusion detection, traffic classes exhibit severe class imbalance. We scale Fisher importance values by inverse class frequency:
$$F_{i}^{weighted} = \sum_{c \in C} w_c \cdot F_{i, c}, \quad w_c = \frac{N}{|C| \cdot N_c}$$

---

## 2. Gradient Episodic Memory (GEM)

### Constrained Optimization
$$\min_{\theta} L(f(x; \theta), y) \quad \text{s.t.} \quad \langle g, g_k \rangle \ge 0 \quad \forall k < t$$

Where:
- $g = \nabla_\theta L(f(x; \theta), y)$ is the gradient on the current batch.
- $g_k = \nabla_\theta L(f(x_k; \theta), y_k)$ is the gradient computed on episodic replay memory for task $k$.

If the inner product is negative ($\langle g, g_k \rangle < 0$), the current gradient $g$ is projected onto the closest feasible gradient vector $\tilde{g}$ via Quadratic Programming (QP):
$$\min_{\tilde{g}} \frac{1}{2} \| g - \tilde{g} \|_2^2 \quad \text{s.t.} \quad G \tilde{g} \ge 0$$
