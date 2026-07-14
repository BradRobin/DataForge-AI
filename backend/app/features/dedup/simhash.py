import hashlib
import re
from typing import List

def get_hash_64(text: str) -> int:
    """Compute a deterministic 64-bit hash from a string using SHA-256."""
    sha = hashlib.sha256(text.encode("utf-8")).digest()
    # Use the first 8 bytes to construct a 64-bit unsigned integer
    return int.from_bytes(sha[:8], byteorder="big")

def get_shingles(text: str) -> List[str]:
    """Tokenize text and generate character 3-grams."""
    cleaned = text.lower()
    if len(cleaned) >= 3:
        return [cleaned[i:i+3] for i in range(len(cleaned) - 2)]
    return [cleaned] if cleaned else []

def compute_simhash(text: str) -> int:
    """
    Compute a 64-bit SimHash fingerprint for the given text.
    Returns 0 if the text is empty or has no features.
    """
    shingles = get_shingles(text)
    if not shingles:
        return 0

    # Initialize a 64-dimensional vector of weights
    vector = [0.0] * 64
    
    for shingle in shingles:
        shingle_hash = get_hash_64(shingle)
        # Accumulate weights across the 64-bit index
        for i in range(64):
            # Check if the i-th bit is set to 1
            if (shingle_hash >> i) & 1:
                vector[i] += 1.0
            else:
                vector[i] -= 1.0

    # Convert the accumulative vector into a final 64-bit fingerprint
    fingerprint = 0
    for i in range(64):
        if vector[i] > 0.0:
            fingerprint |= (1 << i)
            
    return fingerprint

def hamming_distance(f1: int, f2: int) -> int:
    """Calculate the Hamming distance (differing bits) between two 64-bit fingerprints."""
    # XOR the two values and count set bits
    return bin(f1 ^ f2).count("1")
