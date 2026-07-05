# pip install transformers sentence-transformers
from sentence_transformers import SentenceTransformer, util
import numpy as np

# 1. Load the Hugging Face model (Maps text to 384-dimensional vectors)
model = SentenceTransformer('all-MiniLM-L6-v2')

# 2. Our NLP Example Sentences
# Original second sentence: "I would like to apply for a personal loan as soon as possible"
sentences = [
    "Apply for Loan", 
    "I would like to apply for a personal loan as soon as possible"
    #"Can you lend money?"
]   

# 3. Generate Actual Embeddings (Vectorization)
embeddings = model.encode(sentences)
vec_a = embeddings[0]
vec_b = embeddings[1]

# 4. Calculate Metrics
# Euclidean Distance: Measures gap between arrow tips
e_dist = np.linalg.norm(vec_a - vec_b)

# Cosine Similarity: Measures alignment (angle)
# Using util.cos_sim returns a similarity matrix; .item() gets the scalar
c_sim = util.cos_sim(vec_a, vec_b).item()

# Cosine Distance: 1 - Similarity
c_dist = 1 - c_sim

# 5. Print Vectors Vertically (Side-by-Side Comparison)
print(f"{'Dimension':<12} | {'Vector A (Short)':<18} | {'Vector B (Long)':<18}")
print("-" * 55)
for i in range(10):  # Printing first 10 for readability
    print(f"Dim {i+1:<8} | {vec_a[i]:<18.4f} | {vec_b[i]:<18.4f}")

print(f"{'...':<12} | {'...':<18} | {'...':<18}")
print("-" * 55)
print(f"Total Dimensions: {len(vec_a)}")
print(f"\nRESULTS:")
print(f"Euclidean Distance: {e_dist:.4f}  (High distance due to text length/detail)")
print(f"Cosine Similarity:  {c_sim:.4f}  (High similarity - Semantic match!)")
print(f"Cosine Distance:    {c_dist:.4f}  (Low distance - Closest intent)")