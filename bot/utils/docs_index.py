import os
from typing import List, Dict


def index_docs_folder(docs_path: str) -> int:
    count = 0
    for root, dirs, files in os.walk(docs_path):
        for f in files:
            if f.endswith((".txt", ".md", ".pdf")):
                count += 1
    return count


def search_docs(db, query: str) -> List[Dict]:
    return db.search_docs(query)