import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def split_into_chunks(text, chunk_size=500, overlap=100):
    chunks = []
    step = chunk_size - overlap
    for i in range(0, len(text), step):
        chunk = text[i:i + chunk_size]
        chunks.append(chunk)
        if i + chunk_size >= len(text):
            break
    return chunks

STOP_WORDS = {"что", "как", "это", "где", "когда", "кто", "какой", "какие", "почему", "зачем", "для", "про", "или", "при", "дела"}


def find_best_chunks(question, chunks, top_n=2):
    words = question.lower().split()
    filtered = []
    for word in words:
        if word not in STOP_WORDS:
            filtered.append(word)
    words = filtered
    if not words:
        return []
    pairs = []
    best = []
    for chunk in chunks:
        score = 0
        chunk_lower = chunk.lower()
        for word in words:
            if word in chunk_lower:
                score += 1
        if score > 0:
            pairs.append((score, chunk))
        
    pairs.sort(reverse=True)
    top_pairs = pairs[:top_n]
    for score, chunk in top_pairs:
        best.append(chunk)
    return best

def load_chunks():
    with open(os.path.join(BASE_DIR, 'knowledge.txt'), encoding='utf-8') as f:
        text_read = f.read()
        chunks = split_into_chunks(text_read, chunk_size=500, overlap=100)
    return chunks
        
        

if __name__ == '__main__':
    chunks = load_chunks()


        
    question = input("Вопрос: ")
    for chunk in find_best_chunks(question, chunks):
        print(chunk)
        print("---")
            
