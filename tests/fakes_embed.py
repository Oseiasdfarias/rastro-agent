import hashlib
import math


class HashEmbedder:
    dim = 384

    def encode(self, texts, kind):
        out = []
        for t in texts:
            v = [0.0] * self.dim
            for w in t.lower().split():
                v[int(hashlib.md5(w.encode()).hexdigest(), 16) % self.dim] += 1.0
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out
