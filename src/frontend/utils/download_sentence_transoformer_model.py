from transformers import AutoTokenizer, AutoModel

model_name = "sentence-transformers/all-MiniLM-L6-v2"

# Download and save the tokenizer and model
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name)

# Specify the directory to save the model
save_directory = "models/sentence_transformers"

# Save the tokenizer and model locally
tokenizer.save_pretrained(save_directory)
model.save_pretrained(save_directory)