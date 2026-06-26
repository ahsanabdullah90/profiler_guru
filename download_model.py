import os
from huggingface_hub import snapshot_download

def main():
    model_id = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
    local_dir = os.path.join("src", "models", "sentiment_model")
    
    print(f"Downloading {model_id} to {local_dir}...")
    os.makedirs(local_dir, exist_ok=True)
    
    try:
        snapshot_download(
            repo_id=model_id,
            local_dir=local_dir,
            local_dir_use_symlinks=False,
            ignore_patterns=["*.msgpack", "*.h5", "*.ot"] # ignore non-pytorch/non-safetensors weights to save space
        )
        print("Model downloaded successfully!")
    except Exception as e:
        print(f"Error downloading model: {e}")

if __name__ == "__main__":
    main()
