import json
import os
import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
)
from ragas.metrics.collections import (
    context_precision,
    context_recall,
)
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)

import os
os.environ["OPENAI_API_KEY"] = "sk-proj-key"

llm = ChatOpenAI(model="gpt-4o-mini")
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# 3. Load dataset
with open("rag_test_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

dataset_dict = {
    "question": [item["question"] for item in data],
    "answer": [item["answer"] for item in data],
    "contexts": [item["contexts"] for item in data],
    "ground_truth": [item["ground_truth"] for item in data]
}
dataset = Dataset.from_dict(dataset_dict)

result = evaluate(
    dataset,
    metrics=[
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall
    ],
    llm=llm,
    embeddings=embeddings
)

df_results = result.to_pandas()
print("\nAVERAGE SCORES OF YOUR RAG:")
print(result)

df_results.to_csv("rag_performance_report.csv", index=False)
print("\nDetailed report saved!")