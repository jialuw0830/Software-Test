python3 extract_structure.py \
  --system 2 \
  --requirements requirements.txt \
  --prompt prompt/structure.py \
  --output output/system2.json \
  --endpoint "https://azure-api-jialu.openai.azure.com/" \
  --deployment "gpt-4o" \
  --api-version "2024-12-01-preview"