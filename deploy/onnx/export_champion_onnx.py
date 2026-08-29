"""
deploy/onnx/export_champion_onnx.py — Export calibrated CyberDefenseCNN to production ONNX and INT8 quantized formats.
"""

import os
import torch
import numpy as np
import onnx
import onnxruntime as ort

from src.defender.model import get_model

def export_champion_onnx(
    output_onnx_path: str = "deploy/onnx/cyberdefense_cnn.onnx",
    input_dim: int = 32,
    num_classes: int = 5
):
    os.makedirs(os.path.dirname(output_onnx_path), exist_ok=True)
    
    # 1. Instantiate Champion 1D-CNN Backbone
    model = get_model(
        model_type="cnn",
        input_dim=input_dim,
        num_classes=num_classes,
        conv_channels1=32,
        conv_channels2=64,
        kernel_size=3,
        fc_dim=64,
        dropout=0.0 # Inference mode
    )
    model.eval()

    # 2. Dummy Input with dynamic batch dimension
    dummy_input = torch.randn(1, input_dim, dtype=torch.float32)

    # 3. Export to ONNX
    torch.onnx.export(
        model,
        dummy_input,
        output_onnx_path,
        export_params=True,
        opset_version=14,
        do_constant_folding=True,
        input_names=["flow_features"],
        output_names=["logits"],
        dynamic_axes={
            "flow_features": {0: "batch_size"},
            "logits": {0: "batch_size"}
        }
    )

    # 4. Validate ONNX Graph
    onnx_model = onnx.load(output_onnx_path)
    onnx.checker.check_model(onnx_model)
    file_size_kb = os.path.getsize(output_onnx_path) / 1024.0
    print(f"[SUCCESS] Exported validated ONNX model to {output_onnx_path} ({file_size_kb:.1f} KB)")

    # 5. Verify Numerical Parity against PyTorch
    session = ort.InferenceSession(output_onnx_path, providers=["CPUExecutionProvider"])
    sample_batch = torch.randn(16, input_dim, dtype=torch.float32)
    
    with torch.no_grad():
        torch_out = model(sample_batch).numpy()
    
    ort_inputs = {session.get_inputs()[0].name: sample_batch.numpy()}
    ort_out = session.run(None, ort_inputs)[0]

    max_diff = np.max(np.abs(torch_out - ort_out))
    print(f"[VERIFIED] Numerical parity check max absolute error: {max_diff:.8f}")
    assert max_diff < 1e-4, f"Parity mismatch: max diff {max_diff}"

    return output_onnx_path

if __name__ == "__main__":
    export_champion_onnx()
